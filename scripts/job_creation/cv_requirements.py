from __future__ import annotations

from pathlib import Path

from .constants import DEFAULT_CV_REQUIREMENTS
from .input_reader import read_multiline_input
from .paths import ROOT
from .resolvers import read_text

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

