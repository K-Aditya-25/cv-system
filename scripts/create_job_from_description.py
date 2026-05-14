from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from schemas.career_schema import CareerDatabase, JobConfig, Selection  # noqa: E402
from scripts.generate_cv import (  # noqa: E402
    CvGenerationError,
    build_render_context,
    load_yaml,
    render_cv,
    resolve_master_data_path,
    safe_latex_name,
)


DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_CV_REQUIREMENTS = (
    "No extra user requirements were provided. Tailor the CV to the job description using "
    "the most relevant truthful evidence from the candidate inventory."
)
MAX_ONE_PAGE_ENFORCEMENT_ATTEMPTS = 2
MAX_ONE_PAGE_LLM_ATTEMPTS = 2
ONE_PAGE_LIMIT = 1
LOCAL_ENV_FILES = [".env.local", ".env"]
PASTE_END_MARKER = "END"
LONGER_CV_PATTERNS = [
    "two page",
    "two-page",
    "2 page",
    "2-page",
    "multi page",
    "multi-page",
    "longer cv",
    "long cv",
    "more than one page",
    "more than 1 page",
]
PROJECT_LINK_HOSTS = ("github", "devpost", "kaggle")


class IntakeError(Exception):
    pass


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug or "new_job"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise IntakeError(f"Job description file not found: {path}") from None


def read_multiline_input(prompt: str, end_marker: str = PASTE_END_MARKER) -> str:
    print(prompt)
    print(f"Paste text below, then type {end_marker} on its own line and press Enter.")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == end_marker:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def short_text_slug(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text)
    if words:
        return slugify("_".join(words[:8]))[:80]
    return "pasted_job"


def timestamped_job_id() -> str:
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def job_config_folder_id(job_config: JobConfig) -> str:
    return slugify(f"{job_config.company}_{job_config.role}")


def resolve_job_description(args: argparse.Namespace) -> tuple[str, str]:
    sources = [
        bool(args.job_description_file),
        bool(args.job_description_text),
        bool(args.job_description_stdin),
        bool(args.interactive),
    ]
    if sum(sources) != 1:
        raise IntakeError(
            "Provide exactly one job description source: file path, --job-description-text, "
            "--job-description-stdin, or --interactive."
        )

    if args.interactive:
        job_description = read_multiline_input("Job description")
        if not job_description:
            raise IntakeError("Job description cannot be empty")
        return job_description, short_text_slug(job_description)

    if args.job_description_text:
        job_description = args.job_description_text.strip()
        if not job_description:
            raise IntakeError("Job description cannot be empty")
        return job_description, short_text_slug(job_description)

    if args.job_description_stdin:
        job_description = sys.stdin.read().strip()
        if not job_description:
            raise IntakeError("Job description from stdin cannot be empty")
        return job_description, short_text_slug(job_description)

    job_description_file = args.job_description_file
    if not job_description_file.is_absolute():
        job_description_file = ROOT / job_description_file
    return read_text(job_description_file), job_description_file.stem


def resolve_revision_feedback(args: argparse.Namespace) -> str:
    sources = [
        bool(args.feedback),
        bool(args.feedback_file),
        bool(args.feedback_stdin),
        bool(args.interactive),
    ]
    if sum(sources) != 1:
        raise IntakeError(
            "Provide exactly one revision feedback source: --feedback, --feedback-file, "
            "--feedback-stdin, or --interactive."
        )

    if args.interactive:
        feedback = read_multiline_input("Revision feedback for the generated CV")
        if not feedback:
            raise IntakeError("Revision feedback cannot be empty")
        return feedback

    if args.feedback:
        feedback = args.feedback.strip()
        if not feedback:
            raise IntakeError("Revision feedback cannot be empty")
        return feedback

    if args.feedback_stdin:
        feedback = sys.stdin.read().strip()
        if not feedback:
            raise IntakeError("Revision feedback from stdin cannot be empty")
        return feedback

    feedback_file = args.feedback_file
    if not feedback_file.is_absolute():
        feedback_file = ROOT / feedback_file
    return read_text(feedback_file)


def combine_cv_requirements(inline_requirements: str | None, requirements_file: Path | None) -> str:
    requirements: list[str] = []
    if inline_requirements and inline_requirements.strip():
        requirements.append(inline_requirements.strip())
    if requirements_file:
        path = requirements_file if requirements_file.is_absolute() else ROOT / requirements_file
        requirements.append(read_text(path))
    return "\n\n".join(requirements).strip() or DEFAULT_CV_REQUIREMENTS


def resolve_cv_requirements(args: argparse.Namespace) -> str:
    if args.interactive and not args.cv_requirements and not args.cv_requirements_file:
        requirements = read_multiline_input(
            "CV requirements and preferences. Leave empty if you have none."
        )
        return requirements or DEFAULT_CV_REQUIREMENTS
    return combine_cv_requirements(args.cv_requirements, args.cv_requirements_file)


def explicitly_requests_longer_cv(*texts: str) -> bool:
    combined = " ".join(text.lower() for text in texts if text)
    return any(pattern in combined for pattern in LONGER_CV_PATTERNS)


def parse_env_line(line: str, env_name: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    if key.strip() != env_name:
        return None
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
    return value or None


def get_env_secret(env_name: str) -> str | None:
    value = os.environ.get(env_name)
    if value:
        return value
    for env_file in LOCAL_ENV_FILES:
        path = ROOT / env_file
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            value = parse_env_line(line, env_name)
            if value:
                return value
    return None


def write_yaml(path: Path, payload: Any) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def yaml_text(payload: Any) -> str:
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)


def render_prompt_template(template_name: str, **context: Any) -> str:
    env = Environment(
        loader=FileSystemLoader(ROOT / "prompts"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    return env.get_template(template_name).render(**context)


def compact_bullets(items: list[Any]) -> list[dict[str, Any]]:
    compacted = []
    for item in items:
        item_data = item.model_dump()
        compacted.append(
            {
                "id": item_data["id"],
                "title": item_data.get("title")
                or item_data.get("name")
                or item_data.get("role")
                or item_data.get("degree"),
                "organization": item_data.get("company")
                or item_data.get("institution")
                or item_data.get("organization"),
                "summary": item_data.get("summary") or item_data.get("description"),
                "technologies": item_data.get("technologies", []),
                "links": item_data.get("links", []),
                "bullets": [
                    {
                        "id": bullet["id"],
                        "text": bullet["text"],
                        "tags": bullet.get("tags", []),
                        "strength": bullet.get("strength"),
                    }
                    for bullet in item_data.get("bullets", [])
                ],
            }
        )
    return compacted


def build_candidate_inventory(database: CareerDatabase) -> str:
    custom_sections: dict[str, Any] = {}
    for key, section in database.custom_sections.items():
        custom_sections[key] = {
            "title": section.title,
            "items": [
                {
                    "id": item.id,
                    "text": item.text,
                    "tags": item.tags,
                    "strength": item.strength,
                }
                for item in section.items
            ],
        }

    inventory = {
        "profile_summary": database.profile.summary,
        "education": [
            {
                "id": item.id,
                "institution": item.institution,
                "degree": item.degree,
                "coursework": item.coursework,
                "bullets": [
                    {
                        "id": bullet.id,
                        "text": bullet.text,
                        "tags": bullet.tags,
                        "strength": bullet.strength,
                    }
                    for bullet in item.bullets
                ],
            }
            for item in database.education
        ],
        "experience": compact_bullets(database.experience),
        "projects": compact_bullets(database.projects),
        "skills": database.skills,
        "volunteering": compact_bullets(database.volunteering),
        "leadership": compact_bullets(database.leadership),
        "achievements": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "tags": item.tags,
                "strength": item.strength,
            }
            for item in database.achievements
        ],
        "certifications": [
            {
                "id": item.id,
                "name": item.name,
                "issuer": item.issuer,
                "tags": item.tags,
                "strength": item.strength,
            }
            for item in database.certifications
        ],
        "custom_sections": custom_sections,
        "allowed_cv_variants": [
            "technical_ml",
            "software_engineering",
            "data_science",
            "startup_events",
            "leadership_community",
            "general",
        ],
        "allowed_section_keys": list(
            dict.fromkeys(
                [
                    "profile",
                    "education",
                    "technical_skills",
                    "skills",
                    "experience",
                    "projects",
                    "volunteering",
                    "leadership",
                    "achievements",
                    "certifications",
                    *database.custom_sections.keys(),
                ]
            )
        ),
    }
    return yaml.safe_dump(inventory, sort_keys=False, allow_unicode=True)


def strip_json_fences(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_llm_json(raw_text: str) -> dict[str, Any]:
    text = strip_json_fences(raw_text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IntakeError(f"LLM response was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise IntakeError("LLM response must be a JSON object")
    return payload


def call_anthropic(system_prompt: str, user_prompt: str, model: str) -> str:
    api_key = get_env_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise IntakeError("ANTHROPIC_API_KEY is not set in the environment, .env.local, or .env")

    request_payload = {
        "model": model,
        "max_tokens": 6000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": os.environ.get(
                "ANTHROPIC_VERSION", DEFAULT_ANTHROPIC_VERSION
            ),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise IntakeError(f"Anthropic API request failed: HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise IntakeError(f"Anthropic API request failed: {exc.reason}") from exc

    content = response_payload.get("content", [])
    text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
    text = "\n".join(part for part in text_parts if part).strip()
    if not text:
        raise IntakeError("Anthropic API response did not contain text")
    return text


def validate_intake_payload(
    payload: dict[str, Any],
    *,
    allow_longer_cv: bool,
) -> tuple[JobConfig, Selection]:
    try:
        job_config = JobConfig.model_validate(payload.get("job_config"))
        selection = Selection.model_validate(payload.get("selection"))
    except ValidationError as exc:
        raise IntakeError(f"Generated job config or selection failed schema validation:\n{exc}") from exc
    if not allow_longer_cv:
        job_config.cv_length = "one_page"
    return job_config, selection


def is_project_portfolio_link(link: Any) -> bool:
    text = f"{link.label} {link.url}".lower()
    return any(host in text for host in PROJECT_LINK_HOSTS)


def selected_projects_without_portfolio_links(
    database: CareerDatabase,
    selection: Selection,
) -> list[str]:
    projects_by_id = {project.id: project for project in database.projects}
    missing_links: list[str] = []
    for selected_project in selection.projects:
        project = projects_by_id.get(selected_project.id)
        if project is None:
            continue
        if not any(is_project_portfolio_link(link) for link in project.links):
            missing_links.append(selected_project.id)
    return missing_links


def warn_selected_projects_without_portfolio_links(
    database: CareerDatabase,
    selection: Selection,
) -> None:
    missing_links = selected_projects_without_portfolio_links(database, selection)
    if missing_links:
        print(
            "Warning: selected project(s) do not have a GitHub, Devpost, or Kaggle "
            "link in master data and will render without project links: "
            + ", ".join(missing_links),
            file=sys.stderr,
        )


def write_job_files(
    job_folder: Path,
    job_description: str,
    cv_requirements: str,
    system_prompt: str,
    user_prompt: str,
    payload: dict[str, Any],
    job_config: JobConfig,
    selection: Selection,
) -> None:
    job_folder.mkdir(parents=True, exist_ok=False)
    (job_folder / "job_description.md").write_text(job_description + "\n", encoding="utf-8")
    (job_folder / "cv_requirements.md").write_text(cv_requirements + "\n", encoding="utf-8")
    (job_folder / "llm_prompt.md").write_text(
        "# System Prompt\n\n"
        + system_prompt.strip()
        + "\n\n# User Prompt\n\n"
        + user_prompt.strip()
        + "\n",
        encoding="utf-8",
    )
    write_yaml(job_folder / "job_config.yaml", job_config.model_dump(mode="json"))
    write_yaml(job_folder / "selection.yaml", selection.model_dump(mode="json"))

    summary = str(payload.get("job_summary_text") or "").strip()
    if summary:
        (job_folder / "job_summary.txt").write_text(summary + "\n", encoding="utf-8")

    rationale = payload.get("selection_rationale") or []
    if rationale:
        rationale_lines = ["# Selection Rationale", ""]
        rationale_lines.extend(f"- {item}" for item in rationale)
        (job_folder / "selection_rationale.md").write_text(
            "\n".join(rationale_lines) + "\n", encoding="utf-8"
        )


def write_prompt_file(path: Path, system_prompt: str, user_prompt: str) -> None:
    path.write_text(
        "# System Prompt\n\n"
        + system_prompt.strip()
        + "\n\n# User Prompt\n\n"
        + user_prompt.strip()
        + "\n",
        encoding="utf-8",
    )


def append_revision_feedback(job_folder: Path, feedback: str) -> None:
    feedback_path = job_folder / "revision_feedback.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with feedback_path.open("a", encoding="utf-8") as file:
        file.write(f"## {timestamp}\n\n{feedback.strip()}\n\n")


def append_one_page_enforcement_prompt(
    job_folder: Path,
    attempt: int,
    page_count: int,
    system_prompt: str,
    user_prompt: str,
) -> None:
    prompt_path = job_folder / "one_page_enforcement.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with prompt_path.open("a", encoding="utf-8") as file:
        file.write(
            f"## {timestamp} - Attempt {attempt}\n\n"
            f"Detected PDF pages: {page_count}\n\n"
            "# System Prompt\n\n"
            + system_prompt.strip()
            + "\n\n# User Prompt\n\n"
            + user_prompt.strip()
            + "\n\n"
        )


def write_revised_job_files(
    job_folder: Path,
    revision_feedback: str,
    system_prompt: str,
    user_prompt: str,
    payload: dict[str, Any],
    job_config: JobConfig,
    selection: Selection,
) -> None:
    append_revision_feedback(job_folder, revision_feedback)
    write_prompt_file(job_folder / "llm_refine_prompt.md", system_prompt, user_prompt)
    write_yaml(job_folder / "job_config.yaml", job_config.model_dump(mode="json"))
    write_yaml(job_folder / "selection.yaml", selection.model_dump(mode="json"))

    summary = str(payload.get("job_summary_text") or "").strip()
    if summary:
        (job_folder / "job_summary.txt").write_text(summary + "\n", encoding="utf-8")

    rationale = payload.get("selection_rationale") or []
    if rationale:
        rationale_lines = ["# Selection Rationale", ""]
        rationale_lines.extend(f"- {item}" for item in rationale)
        (job_folder / "selection_rationale.md").write_text(
            "\n".join(rationale_lines) + "\n", encoding="utf-8"
        )


def generate_cv(job_folder: Path, database: CareerDatabase, job_config: JobConfig, selection: Selection) -> Path:
    context = build_render_context(database, job_config, selection)
    rendered = render_cv(context, job_config.template)
    output_filename = safe_latex_name(job_config.output_name)
    job_output_path = job_folder / output_filename
    outputs_path = ROOT / "outputs" / output_filename
    outputs_path.parent.mkdir(parents=True, exist_ok=True)
    job_output_path.write_text(rendered, encoding="utf-8")
    outputs_path.write_text(rendered, encoding="utf-8")
    return job_output_path


def pdf_path_for_tex(tex_path: Path) -> Path:
    return tex_path.with_suffix(".pdf")


def compile_pdf(tex_path: Path) -> None:
    subprocess.run(
        ["bash", str(ROOT / "scripts" / "compile_pdf.sh"), str(tex_path)],
        cwd=ROOT,
        check=True,
    )


def count_pdf_pages(pdf_path: Path) -> int:
    if not pdf_path.exists():
        raise IntakeError(f"Compiled PDF was not found: {pdf_path}")

    if not shutil.which("pdfinfo"):
        raise IntakeError(
            "Cannot determine compiled PDF page count because pdfinfo is not installed "
            "or is not available on PATH."
        )

    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise IntakeError(
            "Cannot determine compiled PDF page count because pdfinfo is not available on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        message = f"Cannot determine compiled PDF page count with pdfinfo for {pdf_path}"
        if details:
            message += f": {details}"
        raise IntakeError(message) from exc

    match = re.search(r"^Pages:\s*(\d+)\s*$", result.stdout, flags=re.MULTILINE)
    if not match:
        raise IntakeError(
            f"Cannot determine compiled PDF page count from pdfinfo output: {pdf_path}"
        )
    return int(match.group(1))


def compile_pdf_and_count_pages(tex_path: Path) -> int:
    compile_pdf(tex_path)
    return count_pdf_pages(pdf_path_for_tex(tex_path))


def build_one_page_enforcement_feedback(
    page_count: int,
    attempt: int,
    validation_error: str | None = None,
) -> str:
    feedback = (
        f"Automatic one-page PDF enforcement attempt {attempt}.\n\n"
        f"The compiled CV PDF currently has {page_count} pages. This workflow requires "
        "the final CV to fit on exactly one PDF page, so revise the complete job_config "
        "and complete selection to make the rendered CV fit on one page.\n\n"
        "Keep output_name unchanged. Set cv_length to \"one_page\". Reduce content by "
        "removing the lowest-priority sections, items, bullets, skills, coursework, "
        "education bullets, and inline technology lists as needed. Prefer fewer stronger "
        "items over broad coverage. Return the full revised JSON object, not a patch."
    )
    if validation_error:
        feedback += (
            "\n\nThe previous automatic revision was rejected by validation:\n"
            f"{validation_error}\n\n"
            "Return a corrected one-page revision that satisfies every schema and selection rule."
        )
    return feedback


def should_retry_llm_revision_error(error: IntakeError) -> bool:
    message = str(error)
    non_retryable_prefixes = (
        "ANTHROPIC_API_KEY",
        "Anthropic API request failed",
        "Anthropic API response did not contain text",
    )
    return not message.startswith(non_retryable_prefixes)


def enforce_one_page_pdf(
    *,
    job_folder: Path,
    database: CareerDatabase,
    job_description: str,
    cv_requirements: str,
    candidate_inventory: str,
    system_prompt: str,
    model: str,
    job_config: JobConfig,
    selection: Selection,
    tex_path: Path,
) -> tuple[Path, int]:
    page_count = compile_pdf_and_count_pages(tex_path)

    for attempt in range(1, MAX_ONE_PAGE_ENFORCEMENT_ATTEMPTS + 1):
        if page_count <= ONE_PAGE_LIMIT:
            return tex_path, page_count

        print(
            f"Compiled PDF has {page_count} pages; requesting one-page revision "
            f"attempt {attempt}/{MAX_ONE_PAGE_ENFORCEMENT_ATTEMPTS}."
        )
        validation_error: str | None = None
        for llm_attempt in range(1, MAX_ONE_PAGE_LLM_ATTEMPTS + 1):
            revision_feedback = build_one_page_enforcement_feedback(
                page_count,
                attempt,
                validation_error,
            )
            user_prompt = render_prompt_template(
                "job_refine_user.md.j2",
                job_description=job_description,
                cv_requirements=cv_requirements,
                revision_feedback=revision_feedback,
                current_job_config=yaml_text(job_config.model_dump(mode="json")),
                current_selection=yaml_text(selection.model_dump(mode="json")),
                candidate_inventory=candidate_inventory,
            )
            append_one_page_enforcement_prompt(
                job_folder,
                attempt,
                page_count,
                system_prompt,
                user_prompt,
            )
            raw_response = call_anthropic(system_prompt, user_prompt, model)
            try:
                payload = parse_llm_json(raw_response)
                job_config, selection = validate_intake_payload(payload, allow_longer_cv=False)
                warn_selected_projects_without_portfolio_links(database, selection)
                break
            except IntakeError as exc:
                if not should_retry_llm_revision_error(exc) or (
                    llm_attempt == MAX_ONE_PAGE_LLM_ATTEMPTS
                ):
                    raise
                validation_error = str(exc)
                print(
                    "One-page revision failed validation; requesting corrected "
                    f"revision {llm_attempt + 1}/{MAX_ONE_PAGE_LLM_ATTEMPTS}."
                )
        write_revised_job_files(
            job_folder,
            revision_feedback,
            system_prompt,
            user_prompt,
            payload,
            job_config,
            selection,
        )
        tex_path = generate_cv(job_folder, database, job_config, selection)
        page_count = compile_pdf_and_count_pages(tex_path)

    if page_count > ONE_PAGE_LIMIT:
        raise IntakeError(
            "One-page PDF enforcement failed after "
            f"{MAX_ONE_PAGE_ENFORCEMENT_ATTEMPTS} revision attempts: "
            f"{pdf_path_for_tex(tex_path)} still has {page_count} pages."
        )

    return tex_path, page_count


def unique_job_folder(jobs_root: Path, requested_job_id: str) -> Path:
    base_job_id = slugify(requested_job_id)
    candidate = jobs_root / base_job_id
    if not candidate.exists():
        return candidate
    for index in range(2, 1000):
        candidate = jobs_root / f"{base_job_id}_{index}"
        if not candidate.exists():
            return candidate
    raise IntakeError(f"Could not find an available job folder name for: {base_job_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a job folder and tailored CV from a job description."
    )
    parser.add_argument("job_description_file", type=Path, nargs="?")
    parser.add_argument(
        "--job-description-text",
        help="Raw pasted job description text. Useful for one-command intake without files.",
    )
    parser.add_argument(
        "--job-description-stdin",
        action="store_true",
        help="Read the raw job description from stdin.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for pasted job description and CV requirements, or feedback in refine mode.",
    )
    parser.add_argument(
        "--refine-job",
        type=Path,
        help="Existing job folder to revise from feedback instead of creating a new job.",
    )
    parser.add_argument(
        "--feedback",
        help="Revision feedback for --refine-job.",
    )
    parser.add_argument(
        "--feedback-file",
        type=Path,
        help="Markdown/text file containing revision feedback for --refine-job.",
    )
    parser.add_argument(
        "--feedback-stdin",
        action="store_true",
        help="Read revision feedback for --refine-job from stdin.",
    )
    parser.add_argument(
        "--job-id",
        help="Folder name under jobs/. Defaults to a slug from the job description filename.",
    )
    parser.add_argument(
        "--jobs-root",
        type=Path,
        default=ROOT / "jobs",
        help="Directory where the job folder is created.",
    )
    parser.add_argument(
        "--master-data",
        type=Path,
        help="Master data YAML path. Defaults to CV_MASTER_DATA/CVMasterData or data/master.example.yaml.",
    )
    parser.add_argument(
        "--provider",
        choices=["prompt-only", "anthropic"],
        default=os.environ.get("CV_LLM_PROVIDER", "prompt-only"),
        help="Use prompt-only to write the prompt package without calling an LLM.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("CV_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL),
        help="LLM model name for provider calls.",
    )
    parser.add_argument(
        "--compile-pdf",
        action="store_true",
        help="Compile the generated TeX file to PDF and enforce a one-page result.",
    )
    parser.add_argument(
        "--cv-requirements",
        help=(
            "Per-job user preferences for the CV, such as section omissions, emphasis, "
            "tone, ordering, or content constraints."
        ),
    )
    parser.add_argument(
        "--cv-requirements-file",
        type=Path,
        help="Markdown/text file containing per-job CV requirements.",
    )
    return parser.parse_args()


def create_new_job(args: argparse.Namespace, master_data_path: Path) -> int:
    jobs_root = args.jobs_root if args.jobs_root.is_absolute() else ROOT / args.jobs_root
    try:
        job_description, default_job_id = resolve_job_description(args)
        cv_requirements = resolve_cv_requirements(args)
        database = CareerDatabase.model_validate(load_yaml(master_data_path))
        candidate_inventory = build_candidate_inventory(database)
        system_prompt = render_prompt_template("job_intake_system.md")
        user_prompt = render_prompt_template(
            "job_intake_user.md.j2",
            job_description=job_description,
            cv_requirements=cv_requirements,
            candidate_inventory=candidate_inventory,
        )

        if args.provider == "prompt-only":
            job_id = slugify(args.job_id or default_job_id or timestamped_job_id())
            job_folder = unique_job_folder(jobs_root, job_id)
            job_folder.mkdir(parents=True, exist_ok=False)
            (job_folder / "job_description.md").write_text(
                job_description + "\n", encoding="utf-8"
            )
            (job_folder / "cv_requirements.md").write_text(
                cv_requirements + "\n", encoding="utf-8"
            )
            write_prompt_file(job_folder / "llm_prompt.md", system_prompt, user_prompt)
            print(f"Wrote prompt package to {job_folder}")
            print("Run again with --provider anthropic to generate YAML and CV automatically.")
            return 0

        if args.provider != "anthropic":
            raise IntakeError(f"Unsupported provider: {args.provider}")

        raw_response = call_anthropic(system_prompt, user_prompt, args.model)
        payload = parse_llm_json(raw_response)
        job_config, selection = validate_intake_payload(
            payload,
            allow_longer_cv=explicitly_requests_longer_cv(cv_requirements),
        )
        warn_selected_projects_without_portfolio_links(database, selection)
        job_id = slugify(args.job_id) if args.job_id else job_config_folder_id(job_config)
        job_folder = unique_job_folder(jobs_root, job_id)
        write_job_files(
            job_folder,
            job_description,
            cv_requirements,
            system_prompt,
            user_prompt,
            payload,
            job_config,
            selection,
        )
        tex_path = generate_cv(job_folder, database, job_config, selection)
        pdf_page_count: int | None = None
        if args.compile_pdf:
            tex_path, pdf_page_count = enforce_one_page_pdf(
                job_folder=job_folder,
                database=database,
                job_description=job_description,
                cv_requirements=cv_requirements,
                candidate_inventory=candidate_inventory,
                system_prompt=system_prompt,
                model=args.model,
                job_config=job_config,
                selection=selection,
                tex_path=tex_path,
            )
    except (CvGenerationError, IntakeError, ValidationError, subprocess.CalledProcessError) as exc:
        print(f"Job intake failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote job folder: {job_folder}")
    print(f"Wrote CV TeX: {tex_path}")
    if args.compile_pdf:
        print(f"Compiled PDF next to: {tex_path}")
        if pdf_page_count is not None:
            print(f"Verified PDF page count: {pdf_page_count}")
    return 0


def refine_existing_job(args: argparse.Namespace, master_data_path: Path) -> int:
    job_folder = args.refine_job
    if not job_folder.is_absolute():
        job_folder = ROOT / job_folder

    try:
        if not job_folder.exists():
            raise IntakeError(f"Job folder does not exist: {job_folder}")

        revision_feedback = resolve_revision_feedback(args)
        database = CareerDatabase.model_validate(load_yaml(master_data_path))
        current_job_config = JobConfig.model_validate(load_yaml(job_folder / "job_config.yaml"))
        current_selection = Selection.model_validate(load_yaml(job_folder / "selection.yaml"))
        job_description = read_text(job_folder / "job_description.md")
        cv_requirements_path = job_folder / "cv_requirements.md"
        cv_requirements = (
            read_text(cv_requirements_path)
            if cv_requirements_path.exists()
            else DEFAULT_CV_REQUIREMENTS
        )
        candidate_inventory = build_candidate_inventory(database)
        system_prompt = render_prompt_template("job_intake_system.md")
        user_prompt = render_prompt_template(
            "job_refine_user.md.j2",
            job_description=job_description,
            cv_requirements=cv_requirements,
            revision_feedback=revision_feedback,
            current_job_config=yaml_text(current_job_config.model_dump(mode="json")),
            current_selection=yaml_text(current_selection.model_dump(mode="json")),
            candidate_inventory=candidate_inventory,
        )

        if args.provider == "prompt-only":
            append_revision_feedback(job_folder, revision_feedback)
            write_prompt_file(job_folder / "llm_refine_prompt.md", system_prompt, user_prompt)
            print(f"Wrote refinement prompt to {job_folder / 'llm_refine_prompt.md'}")
            print("Run again with --provider anthropic to revise YAML and regenerate the CV.")
            return 0

        if args.provider != "anthropic":
            raise IntakeError(f"Unsupported provider: {args.provider}")

        raw_response = call_anthropic(system_prompt, user_prompt, args.model)
        payload = parse_llm_json(raw_response)
        job_config, selection = validate_intake_payload(
            payload,
            allow_longer_cv=explicitly_requests_longer_cv(cv_requirements, revision_feedback),
        )
        warn_selected_projects_without_portfolio_links(database, selection)
        write_revised_job_files(
            job_folder,
            revision_feedback,
            system_prompt,
            user_prompt,
            payload,
            job_config,
            selection,
        )
        tex_path = generate_cv(job_folder, database, job_config, selection)
        pdf_page_count: int | None = None
        if args.compile_pdf:
            tex_path, pdf_page_count = enforce_one_page_pdf(
                job_folder=job_folder,
                database=database,
                job_description=job_description,
                cv_requirements=cv_requirements,
                candidate_inventory=candidate_inventory,
                system_prompt=system_prompt,
                model=args.model,
                job_config=job_config,
                selection=selection,
                tex_path=tex_path,
            )
    except (CvGenerationError, IntakeError, ValidationError, subprocess.CalledProcessError) as exc:
        print(f"Job refinement failed: {exc}", file=sys.stderr)
        return 1

    print(f"Updated job folder: {job_folder}")
    print(f"Regenerated CV TeX: {tex_path}")
    if args.compile_pdf:
        print(f"Compiled PDF next to: {tex_path}")
        if pdf_page_count is not None:
            print(f"Verified PDF page count: {pdf_page_count}")
    return 0


def main() -> int:
    args = parse_args()

    master_data_path = args.master_data
    if master_data_path is None:
        master_data_path = resolve_master_data_path()
    elif not master_data_path.is_absolute():
        master_data_path = ROOT / master_data_path

    if args.refine_job:
        return refine_existing_job(args, master_data_path)
    return create_new_job(args, master_data_path)


if __name__ == "__main__":
    raise SystemExit(main())
