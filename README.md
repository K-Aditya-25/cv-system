# Programmatic CV Generation System

This project is an MVP for maintaining one structured career database and generating tailored CVs from it.

The core workflow is:

```text
career database + job description + job config + selection file -> tailored LaTeX CV -> PDF
```

The master career database is the source of truth. CVs are generated artifacts. A generated CV should never invent information: it should only use selected IDs and bullet IDs that already exist in the configured master data file.

## What This Is

This is a simple, practical CV generation system built with:

- Python
- `uv` for Python versions, environments, dependencies, locking, and running scripts
- YAML for career data and job-specific selections
- Pydantic v2 for validation
- Jinja2 for rendering LaTeX
- LaTeX for PDF output

This is not a web app. It does not use PostgreSQL or a complex database. YAML is intentionally used first because it is readable, Git-friendly, and easy to edit.

## Data Privacy

Your real career database should stay private. This repo is designed so the code, schema, templates, and fake example data can be public, while your real career data remains local.

- `data/master.example.yaml` is safe dummy data committed to the repo.
- `data/master.private.yaml` is your real local career database and is ignored by Git.
- `data/master.yaml` is also ignored for compatibility if you prefer that local filename.
- `data/raw_inputs/*` is ignored so old CVs, LinkedIn exports, and notes are not uploaded.

By default, scripts use `data/master.example.yaml`. To use your private file locally, set:

```bash
CV_MASTER_DATA=data/master.private.yaml uv run python scripts/validate_data.py
CV_MASTER_DATA=data/master.private.yaml uv run python scripts/generate_cv.py jobs/my_real_job_folder
```

The scripts also accept `CVMasterData` as a compatibility alias, but `CV_MASTER_DATA` is recommended for shell use.

## Folder Structure

```text
cv-system/
  README.md
  pyproject.toml
  uv.lock
  .python-version
  data/
    master.example.yaml
    master.private.yaml   # local only, ignored by Git
    raw_inputs/
      README.md
  schemas/
    career_schema.py
  templates/
    cv_template.tex.j2
  jobs/
    example_technical_ml_role/
      job_config.yaml
      job_description.md
      selection.yaml
    example_startup_events_role/
      job_config.yaml
      job_description.md
      selection.yaml
  scripts/
    validate_data.py
    generate_cv.py
    compile_pdf.sh
  outputs/
```

## Setup With uv

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Python 3.12, create the environment, and sync dependencies:

```bash
uv python install 3.12
uv venv
uv sync
```

The scripts do not require manual virtual environment activation. Run them through `uv run`.

## Validate Data

```bash
uv run python scripts/validate_data.py
```

This validates the configured master data file using the Pydantic models in `schemas/career_schema.py`. By default, it validates `data/master.example.yaml`. To validate your private database:

```bash
CV_MASTER_DATA=data/master.private.yaml uv run python scripts/validate_data.py
```

## Generate CVs

Generate the technical ML/software example:

```bash
uv run python scripts/generate_cv.py jobs/example_technical_ml_role
```

This uses `data/master.example.yaml` unless `CV_MASTER_DATA` is set.

Expected files:

```text
jobs/example_technical_ml_role/exampletech_ml_engineer_cv.tex
outputs/exampletech_ml_engineer_cv.tex
```

Generate the startup/events/community example:

```bash
uv run python scripts/generate_cv.py jobs/example_startup_events_role
```

Expected files:

```text
jobs/example_startup_events_role/communityforge_startup_events_cv.tex
outputs/communityforge_startup_events_cv.tex
```

## Compile PDF

Compile a generated `.tex` file:

```bash
bash scripts/compile_pdf.sh jobs/example_technical_ml_role/exampletech_ml_engineer_cv.tex
```

The script uses `latexmk -pdf` if available, then `tectonic`, then `pdflatex`. If none are installed, it prints a helpful error.

## How the Files Work

### Master Data Files

The structured career database can live in either:

- `data/master.example.yaml`: safe public sample data
- `data/master.private.yaml`: real private data, ignored by Git
- any other path passed through `CV_MASTER_DATA`

The master data includes:

- `profile`
- `education`
- `experience`
- `projects`
- `skills`
- `volunteering`
- `leadership`
- `achievements`
- `certifications`
- `custom_sections`

Every reusable item has an `id`. Bullets also have IDs. Job-specific CVs refer to these IDs from `selection.yaml`.

The example job folders use IDs from `data/master.example.yaml`. Your real job folders should use IDs from your private data file.

### Job Folders

Each job folder contains:

- `job_config.yaml`: positioning, variant, template, output name, section order
- `job_description.md`: pasted job description or notes
- `selection.yaml`: deterministic list of selected education, experience, projects, bullets, skills, and custom section items

Create a new job by copying one of the example folders and editing the files.

## Editing the Career Database

### Add Education

Add a new item under `education` in your private master data file with an ID:

```yaml
education:
  - id: university_msc_data_science
    institution: "Example University"
    location: "Dublin, Ireland"
    degree: "MSc Data Science"
    start_date: "2026"
    end_date: "2027"
    grade: "Distinction expected"
    coursework:
      - Machine Learning
      - Statistical Modelling
    bullets:
      - id: thesis_forecasting
        text: "Completed a thesis on probabilistic forecasting for operational datasets."
        tags: [machine-learning, forecasting]
        strength: 4
```

Then select it in a job folder:

```yaml
education:
  - university_msc_data_science
```

### Add Experience

Add a new item under `experience`. Keep bullets atomic and reusable:

```yaml
experience:
  - id: software_engineering_intern_newco
    company: "NewCo"
    title: "Software Engineering Intern"
    location: "London, UK"
    start_date: "Jun 2026"
    end_date: "Sep 2026"
    summary: "Built backend tooling for internal analytics workflows."
    technologies: [Python, FastAPI, Docker]
    bullets:
      - id: backend_api_delivery
        text: "Implemented FastAPI endpoints used by analysts to query operational metrics."
        tags: [backend, api, analytics]
        strength: 4
```

Select the experience and specific bullets:

```yaml
experience:
  - id: software_engineering_intern_newco
    bullets:
      - backend_api_delivery
```

### Add Projects

Add projects under `projects` with links and selectable bullets:

```yaml
projects:
  - id: ml_recommendation_service
    name: "ML Recommendation Service"
    date: "2026"
    category: "machine_learning"
    subtitle: "Personal project"
    description: "Built a small recommendation API with offline evaluation."
    technologies: [Python, scikit-learn, FastAPI]
    links:
      - label: "GitHub"
        url: "https://github.com/example/recommendation-service"
    bullets:
      - id: ranking_evaluation
        text: "Compared ranking models using precision@k and recall@k on held-out interactions."
        tags: [machine-learning, evaluation]
        strength: 5
```

### Add Skills

Skills are category-based and dynamic. Category names are not hardcoded in the LaTeX template.

```yaml
skills:
  programming_languages:
    - Python
    - TypeScript
  machine_learning:
    - PyTorch
    - scikit-learn
```

Select only the relevant skills for a job:

```yaml
skills:
  programming_languages:
    - Python
  machine_learning:
    - PyTorch
```

### Add Custom Sections

Use `custom_sections` for anything that does not fit neatly into the fixed sections.

```yaml
custom_sections:
  leadership_volunteering_outreach:
    title: "Leadership, Volunteering & Outreach"
    items:
      - id: technical_blog_writer
        text: "Technical Blog Writer: published tutorials on machine learning project work."
        tags: [writing, technical-communication]
        strength: 4
```

Select custom section items by ID:

```yaml
custom_sections:
  leadership_volunteering_outreach:
    - technical_blog_writer
```

## CV Variants

`job_config.yaml` supports these initial variants:

- `technical_ml`
- `software_engineering`
- `data_science`
- `startup_events`
- `leadership_community`
- `general`

Variants influence default behavior when `sections_order` is missing. For example, `technical_ml` puts technical skills near the top, while `startup_events` includes profile and outreach-oriented custom sections.

Explicit `sections_order` always wins:

```yaml
sections_order:
  - education
  - technical_skills
  - experience
  - projects
  - achievements
  - certifications
```

Use `technical_skills` when you want the skills section heading to read "Technical Skills". Use `skills` when you want the heading to read "Skills". Both render the selected skill categories dynamically.

## LaTeX Template

The default template is `templates/cv_template.tex.j2`.

It is intentionally compact, single-column, ATS-friendly, and LaTeX-native:

- centered candidate name
- centered contact and profile links
- dark blue section accent
- no sidebars
- no photos
- no graphics-heavy layout
- flexible section ordering
- dynamic skills categories
- generic custom sections

Special LaTeX characters in plain text are escaped by the generator. URLs are handled separately for `hyperref`.

## Troubleshooting

`Selected ID does not exist`

Check that the ID in `selection.yaml` exactly matches an ID in the master data file currently being used. If you are using private data, confirm `CV_MASTER_DATA=data/master.private.yaml` is set.

`Selected bullet does not belong to selected item`

Bullet IDs are scoped to their parent experience or project. Confirm the bullet is listed under the selected item in the configured master data file.

`Selected skill does not exist`

Skills must first be listed in the configured master data file, then selected by category in `selection.yaml`.

`Template not found`

Confirm `template` in `job_config.yaml` matches a file in `templates/`.

`No LaTeX compiler found`

Install `latexmk`, `tectonic`, or `pdflatex`. On macOS, MacTeX is the common full LaTeX distribution; Tectonic is a lighter alternative.

`The example jobs work, but my private jobs fail`

The example jobs are wired to `data/master.example.yaml`. Real job folders need selections that reference IDs in your private data. Run private jobs like this:

```bash
CV_MASTER_DATA=data/master.private.yaml uv run python scripts/generate_cv.py jobs/my_real_job_folder
```

## Recommended Future Data Ingestion Workflow

1. Collect old CVs, LinkedIn text, project notes, GitHub README text, and certificates.
2. Convert PDFs to text manually or with a tool.
3. Place raw text in `data/raw_inputs/`.
4. Ask GPT/Codex to extract unique reusable career information into `data/master.private.yaml`.
5. Validate with `CV_MASTER_DATA=data/master.private.yaml uv run python scripts/validate_data.py`.
6. Review manually.
7. Keep `data/master.private.yaml` local; commit only code, templates, schemas, and sanitized examples.

## Future Extensions

This MVP is designed so it can later grow into:

- GPT-based section and bullet selection
- automatic job description parsing
- multiple CV templates
- cover letter generation
- application tracking
- semantic matching between job descriptions and career bullets
- Streamlit UI
- SQLite migration if YAML becomes too limiting

Those are intentionally not implemented yet.
