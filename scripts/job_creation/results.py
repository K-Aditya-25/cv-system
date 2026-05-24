from __future__ import annotations

from pathlib import Path


def print_generation_result(
    job_folder: Path,
    tex_path: Path,
    pdf_page_count: int | None,
    *,
    refined: bool,
    compile_pdf: bool,
) -> None:
    if refined:
        print(f"Updated job folder: {job_folder}")
        print(f"Regenerated CV TeX: {tex_path}")
    else:
        print(f"Wrote job folder: {job_folder}")
        print(f"Wrote CV TeX: {tex_path}")
    if compile_pdf:
        print(f"Compiled PDF next to: {tex_path}")
        if pdf_page_count is not None:
            print(f"Verified PDF page count: {pdf_page_count}")
