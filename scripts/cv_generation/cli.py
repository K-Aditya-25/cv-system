import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from scripts.cv_generation.context import build_render_context
from scripts.cv_generation.errors import CvGenerationError
from scripts.cv_generation.files import ROOT, load_yaml, resolve_master_data_path, safe_latex_name
from scripts.cv_generation.rendering import render_cv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a tailored LaTeX CV from a job folder.")
    parser.add_argument("job_folder", type=Path, help="Path to a job folder")
    return parser.parse_args()


def generate_job_cv(job_folder: Path) -> tuple[Path, Path]:
    database = CareerDatabase.model_validate(load_yaml(resolve_master_data_path()))
    job_config = JobConfig.model_validate(load_yaml(job_folder / "job_config.yaml"))
    selection = Selection.model_validate(load_yaml(job_folder / "selection.yaml"))
    rendered = render_cv(build_render_context(database, job_config, selection), job_config.template)
    output_filename = safe_latex_name(job_config.output_name)
    job_output_path = job_folder / output_filename
    outputs_path = ROOT / "outputs" / output_filename
    outputs_path.parent.mkdir(parents=True, exist_ok=True)
    job_output_path.write_text(rendered, encoding="utf-8")
    outputs_path.write_text(rendered, encoding="utf-8")
    return job_output_path, outputs_path


def main() -> int:
    job_folder = parse_args().job_folder
    if not job_folder.is_absolute():
        job_folder = ROOT / job_folder
    try:
        job_output_path, outputs_path = generate_job_cv(job_folder)
    except ValidationError as exc:
        print(f"Validation failed:\n{exc}", file=sys.stderr)
        return 1
    except CvGenerationError as exc:
        print(f"CV generation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {job_output_path}")
    print(f"Wrote {outputs_path}")
    return 0
