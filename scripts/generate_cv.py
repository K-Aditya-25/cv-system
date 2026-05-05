from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from schemas.career_schema import CareerDatabase, JobConfig, Selection  # noqa: E402


DEFAULT_SECTION_ORDERS: dict[str, list[str]] = {
    "technical_ml": [
        "education",
        "technical_skills",
        "experience",
        "projects",
        "achievements",
        "certifications",
    ],
    "software_engineering": [
        "education",
        "technical_skills",
        "experience",
        "projects",
        "achievements",
        "certifications",
    ],
    "data_science": [
        "profile",
        "education",
        "technical_skills",
        "experience",
        "projects",
        "achievements",
        "certifications",
    ],
    "startup_events": [
        "profile",
        "education",
        "experience",
        "projects",
        "leadership_volunteering_outreach",
        "skills",
    ],
    "leadership_community": [
        "profile",
        "education",
        "experience",
        "leadership",
        "volunteering",
        "leadership_volunteering_outreach",
        "skills",
        "achievements",
    ],
    "general": [
        "profile",
        "education",
        "skills",
        "experience",
        "projects",
        "leadership",
        "volunteering",
        "achievements",
        "certifications",
    ],
}

SECTION_TITLES: dict[str, str] = {
    "profile": "Profile",
    "education": "Education",
    "technical_skills": "Technical Skills",
    "skills": "Skills",
    "experience": "Experience",
    "projects": "Projects",
    "volunteering": "Volunteering",
    "leadership": "Leadership",
    "achievements": "Achievements",
    "certifications": "Certifications",
}

LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


class CvGenerationError(Exception):
    pass


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise CvGenerationError(f"File not found: {path}") from None
    except yaml.YAMLError as exc:
        raise CvGenerationError(f"Invalid YAML in {path}: {exc}") from exc


def escape_tex(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return "".join(LATEX_REPLACEMENTS.get(char, char) for char in text)


def escape_url(value: Any) -> str:
    if value is None:
        return ""
    # Hyperref receives URLs inside \detokenize so normal URL punctuation is preserved.
    return str(value).replace("}", "%7D")


def href_url(value: Any) -> str:
    return r"\detokenize{" + escape_url(value) + "}"


def category_label(value: str) -> str:
    special = {
        "programming_languages": "Programming",
        "machine_learning": "ML",
        "cloud_devops": "Cloud & DevOps",
    }
    return special.get(value, value.replace("_", " ").title())


def safe_latex_name(output_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", output_name):
        raise CvGenerationError(
            "output_name must contain only letters, numbers, dashes, underscores, or dots"
        )
    if output_name.endswith(".tex"):
        return output_name
    return f"{output_name}.tex"


def index_by_id(items: list[Any], section_name: str) -> dict[str, Any]:
    indexed = {item.id: item for item in items}
    if len(indexed) != len(items):
        raise CvGenerationError(f"Duplicate IDs detected in {section_name}")
    return indexed


def select_simple_items(
    selected_ids: list[str],
    available_items: list[Any],
    section_name: str,
) -> list[dict[str, Any]]:
    indexed = index_by_id(available_items, section_name)
    selected: list[dict[str, Any]] = []
    for selected_id in selected_ids:
        item = indexed.get(selected_id)
        if item is None:
            raise CvGenerationError(f"Selected {section_name} ID does not exist: {selected_id}")
        selected.append(item.model_dump())
    return selected


def select_items_with_bullets(
    selected_entries: list[Any],
    available_items: list[Any],
    section_name: str,
) -> list[dict[str, Any]]:
    indexed = index_by_id(available_items, section_name)
    selected: list[dict[str, Any]] = []
    for entry in selected_entries:
        item = indexed.get(entry.id)
        if item is None:
            raise CvGenerationError(f"Selected {section_name} ID does not exist: {entry.id}")

        item_data = item.model_dump()
        bullets_by_id = {bullet["id"]: bullet for bullet in item_data.get("bullets", [])}
        chosen_bullets = []
        for bullet_id in entry.bullets:
            bullet = bullets_by_id.get(bullet_id)
            if bullet is None:
                raise CvGenerationError(
                    f"Selected bullet '{bullet_id}' does not belong to {section_name} '{entry.id}'"
                )
            chosen_bullets.append(bullet)
        item_data["bullets"] = chosen_bullets
        selected.append(item_data)
    return selected


def select_skills(
    selected_skills: dict[str, list[str]],
    available_skills: dict[str, list[str]],
) -> dict[str, list[str]]:
    selected: dict[str, list[str]] = {}
    for category, skills in selected_skills.items():
        if category not in available_skills:
            raise CvGenerationError(f"Selected skills category does not exist: {category}")
        available = set(available_skills[category])
        missing = [skill for skill in skills if skill not in available]
        if missing:
            raise CvGenerationError(
                f"Selected skill(s) do not exist in '{category}': {', '.join(missing)}"
            )
        selected[category] = skills
    return selected


def select_custom_sections(
    selected_sections: dict[str, list[str]],
    available_sections: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for section_key, selected_ids in selected_sections.items():
        section = available_sections.get(section_key)
        if section is None:
            raise CvGenerationError(f"Selected custom section does not exist: {section_key}")

        item_index = {item.id: item for item in section.items}
        selected_items = []
        for selected_id in selected_ids:
            item = item_index.get(selected_id)
            if item is None:
                raise CvGenerationError(
                    f"Selected custom section item '{selected_id}' does not exist in '{section_key}'"
                )
            selected_items.append(item.model_dump())

        selected[section_key] = {
            "title": section.title,
            "items": selected_items,
        }
    return selected


def has_section_content(section_key: str, context: dict[str, Any]) -> bool:
    if section_key == "profile":
        return bool(context["profile"].get("summary"))
    if section_key in {"skills", "technical_skills"}:
        return bool(context.get("skills"))
    if section_key in context.get("custom_sections", {}):
        return bool(context["custom_sections"][section_key].get("items"))
    value = context.get(section_key)
    return bool(value)


def build_render_context(
    database: CareerDatabase,
    job_config: JobConfig,
    selection: Selection,
) -> dict[str, Any]:
    database_copy = copy.deepcopy(database)
    selected_context: dict[str, Any] = {
        "profile": database_copy.profile.model_dump(),
        "job": job_config.model_dump(),
        "education": select_simple_items(selection.education, database_copy.education, "education"),
        "experience": select_items_with_bullets(
            selection.experience, database_copy.experience, "experience"
        ),
        "projects": select_items_with_bullets(selection.projects, database_copy.projects, "projects"),
        "skills": select_skills(selection.skills, database_copy.skills),
        "volunteering": select_simple_items(
            selection.volunteering, database_copy.volunteering, "volunteering"
        ),
        "leadership": select_simple_items(selection.leadership, database_copy.leadership, "leadership"),
        "achievements": select_simple_items(
            selection.achievements, database_copy.achievements, "achievements"
        ),
        "certifications": select_simple_items(
            selection.certifications, database_copy.certifications, "certifications"
        ),
        "custom_sections": select_custom_sections(
            selection.custom_sections, database_copy.custom_sections
        ),
    }

    section_order = job_config.sections_order or DEFAULT_SECTION_ORDERS[job_config.cv_variant]
    selected_context["sections_order"] = [
        section for section in section_order if has_section_content(section, selected_context)
    ]

    section_titles = dict(SECTION_TITLES)
    for key, section in selected_context["custom_sections"].items():
        section_titles[key] = section["title"]
    selected_context["section_titles"] = section_titles
    return selected_context


def render_cv(context: dict[str, Any], template_name: str) -> str:
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    env.filters["tex"] = escape_tex
    env.filters["tex_url"] = escape_url
    env.filters["href_url"] = href_url
    env.filters["category_label"] = category_label

    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        raise CvGenerationError(f"Template not found: templates/{template_name}") from None
    return template.render(**context)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a tailored LaTeX CV from a job folder.")
    parser.add_argument("job_folder", type=Path, help="Path to a job folder")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    job_folder = args.job_folder
    if not job_folder.is_absolute():
        job_folder = ROOT / job_folder

    try:
        database = CareerDatabase.model_validate(load_yaml(ROOT / "data" / "master.yaml"))
        job_config = JobConfig.model_validate(load_yaml(job_folder / "job_config.yaml"))
        selection = Selection.model_validate(load_yaml(job_folder / "selection.yaml"))

        context = build_render_context(database, job_config, selection)
        rendered = render_cv(context, job_config.template)

        output_filename = safe_latex_name(job_config.output_name)
        job_output_path = job_folder / output_filename
        outputs_path = ROOT / "outputs" / output_filename
        outputs_path.parent.mkdir(parents=True, exist_ok=True)

        job_output_path.write_text(rendered, encoding="utf-8")
        outputs_path.write_text(rendered, encoding="utf-8")
    except ValidationError as exc:
        print(f"Validation failed:\n{exc}", file=sys.stderr)
        return 1
    except CvGenerationError as exc:
        print(f"CV generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {job_output_path}")
    print(f"Wrote {outputs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
