# Programmatic CV Generation System

This project maintains one structured career database and generates tailored CVs from it.

The main workflow is:

```text
career data + job-specific selection -> LaTeX CV -> PDF
```

The automated workflow can also use Claude through the Anthropic API:

```text
job description + career data -> tailored job folder -> LaTeX CV -> PDF
```

The career database is the source of truth. Generated CVs should only use facts, IDs, and bullet IDs that already exist in the configured master data file.

## What You Need

- Python 3.12
- `uv`
- A LaTeX compiler for PDFs: `latexmk`, `tectonic`, or `pdflatex`
- Optional: `pdfinfo` for one-page PDF checks
- Optional: `ANTHROPIC_API_KEY` for Claude-powered job intake and refinement

Install and sync the Python environment:

```bash
uv python install 3.12
uv venv
uv sync
```

The scripts are run through `uv run`; you do not need to activate the virtual environment manually.

## Data Files

By default, commands use the safe example data:

```text
data/master.example.yaml
```

For real CVs, use your private local data file:

```text
data/master.private.yaml
```

That private file is ignored by Git. Use `CV_MASTER_DATA` to point commands at it:

```bash
CV_MASTER_DATA=data/master.private.yaml uv run python scripts/validate_data.py
```

## Run The Project

Validate the example data:

```bash
uv run python scripts/validate_data.py
```

Validate your private data:

```bash
CV_MASTER_DATA=data/master.private.yaml uv run python scripts/validate_data.py
```

Generate a CV from an existing local job folder:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/generate_cv.py jobs/my_real_job_folder
```

To test with non-private data, create a local job folder whose `selection.yaml` uses IDs from `data/master.example.yaml`, then run:

```bash
uv run python scripts/generate_cv.py jobs/my_local_example_job
```

Compile a generated CV to PDF:

```bash
bash scripts/compile_pdf.sh jobs/my_real_job_folder/generated_cv_name.tex
```

## Claude Job Intake

Store your Anthropic API key in an ignored local env file:

```bash
read -s ANTHROPIC_API_KEY
printf 'ANTHROPIC_API_KEY=%s\n' "$ANTHROPIC_API_KEY" > .env.local
unset ANTHROPIC_API_KEY
```

Create a job-specific CV interactively from a pasted job description:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/create_job_from_description.py \
  --interactive \
  --provider anthropic \
  --compile-pdf
```

In interactive mode, paste the job description, type `END`, paste any CV preferences, then type `END` again.

Use prompt-only mode when you want to inspect the prompt without calling Claude:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/create_job_from_description.py \
  --interactive \
  --provider prompt-only
```

Refine an existing generated job folder:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/create_job_from_description.py \
  --refine-job jobs/my_real_job_folder \
  --interactive \
  --provider anthropic \
  --compile-pdf
```

When `--compile-pdf` is used, the intake workflow compiles the CV, checks that the PDF is one page, and can ask Claude for a shorter revised selection if the result is too long.

## More Detail

Backend details, file formats, data modeling guidance, prompt behavior, troubleshooting, and future extension notes live in [docs/project-details.md](docs/project-details.md).
