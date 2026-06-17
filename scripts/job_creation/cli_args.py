from __future__ import annotations

import argparse, os
from pathlib import Path

from .constants import DEFAULT_ANTHROPIC_MODEL
from .paths import ROOT

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
        help=(
            "Prompt for input. With --provider claude, keep a persistent CV "
            "generation/refinement session open until Ctrl-Q."
        ),
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
        choices=["prompt-only", "claude", "anthropic", "tensorix"],
        default=os.environ.get("CV_LLM_PROVIDER", "prompt-only"),
        help=(
            "Use prompt-only to write the prompt package without calling an LLM, "
            "claude to call the Anthropic Claude API, or tensorix to call an "
            "OpenAI-compatible Tensorix model. anthropic is accepted as a "
            "backwards-compatible alias."
        ),
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
