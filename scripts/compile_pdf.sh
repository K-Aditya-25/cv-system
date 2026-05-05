#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: bash scripts/compile_pdf.sh path/to/generated_cv.tex" >&2
  exit 1
fi

tex_file="$1"

if [ ! -f "$tex_file" ]; then
  echo "TeX file not found: $tex_file" >&2
  exit 1
fi

tex_dir="$(cd "$(dirname "$tex_file")" && pwd)"
tex_name="$(basename "$tex_file")"

if command -v latexmk >/dev/null 2>&1; then
  (cd "$tex_dir" && latexmk -pdf -interaction=nonstopmode -halt-on-error "$tex_name")
elif command -v tectonic >/dev/null 2>&1; then
  (cd "$tex_dir" && tectonic "$tex_name")
elif command -v pdflatex >/dev/null 2>&1; then
  (cd "$tex_dir" && pdflatex -interaction=nonstopmode -halt-on-error "$tex_name")
  (cd "$tex_dir" && pdflatex -interaction=nonstopmode -halt-on-error "$tex_name")
else
  echo "No LaTeX compiler found." >&2
  echo "Install latexmk, tectonic, or pdflatex, then rerun this command." >&2
  echo "On macOS, MacTeX is the common full LaTeX distribution; Tectonic is a lighter alternative." >&2
  exit 1
fi
