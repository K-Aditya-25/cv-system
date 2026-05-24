from __future__ import annotations

import re, shutil, subprocess
from pathlib import Path

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from scripts.generate_cv import DEFAULT_PAGE_MARGIN, build_render_context, render_cv, safe_latex_name
from .constants import ONE_PAGE_LIMIT
from .errors import IntakeError
from .paths import ROOT

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


def assert_pdf_is_exactly_one_page(pdf_path: Path) -> int:
    page_count = count_pdf_pages(pdf_path)
    if page_count != ONE_PAGE_LIMIT:
        raise IntakeError(f"{pdf_path} has {page_count} pages; expected exactly 1 page.")
    return page_count


def halve_margin(margin: str) -> str:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)([A-Za-z]+)\s*", margin)
    if not match:
        raise IntakeError(f"Cannot halve unsupported LaTeX margin value: {margin}")
    value = float(match.group(1)) / 2
    unit = match.group(2)
    return f"{value:g}{unit}"

