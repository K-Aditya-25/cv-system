from __future__ import annotations

import argparse, sys
from pathlib import Path

from .constants import DEFAULT_CV_REQUIREMENTS
from .errors import IntakeError
from .input_reader import read_multiline_input
from .paths import ROOT
from .text_utils import short_text_slug
from .text_utils import read_text

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


