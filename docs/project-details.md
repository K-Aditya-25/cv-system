# Project Details

This document keeps the implementation and maintenance details out of the README.

## Architecture

The system is intentionally small and file-based:

- Python scripts run the workflow.
- YAML stores career data and job-specific selections.
- Pydantic validates data files.
- Jinja2 renders LaTeX.
- LaTeX compiles the final PDF.
- Claude through the Anthropic API can create and refine job-specific selections.

This is not a web app. It does not use PostgreSQL or a complex database. YAML is used first because it is readable, Git-friendly, and easy to edit.

## Folder Structure

```text
cv-system/
  README.md
  docs/
    project-details.md
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
  prompts/
    job_intake_system.md
    job_intake_user.md.j2
    job_refine_user.md.j2
  jobs/
    my_real_job_folder/
      job_config.yaml
      job_description.md
      selection.yaml
  scripts/
    validate_data.py
    create_job_from_description.py
    generate_cv.py
    compile_pdf.sh
  outputs/
```

## Data Privacy

The repo is designed so code, schemas, templates, and fake example data can be public while real career data stays local.

- `data/master.example.yaml` is safe dummy data committed to the repo.
- `data/master.private.yaml` is the real local career database and is ignored by Git.
- `data/master.yaml` is also ignored for compatibility.
- `data/raw_inputs/*` is ignored so old CVs, LinkedIn exports, and notes are not uploaded.
- `.env` and `.env.*` are ignored so local API keys are not uploaded.

When using the LLM intake workflow, the configured provider receives the job description and a compact candidate inventory containing career IDs, skills, bullet text, tags, strengths, and project links. Use the manual workflow for roles or data you do not want to send to an external API.

The API key is not included in prompts, job files, or generated CVs. The intake script reads `ANTHROPIC_API_KEY` from the process environment, `.env.local`, or `.env`.

## Master Data Files

The structured career database can live in:

- `data/master.example.yaml`
- `data/master.private.yaml`
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

Every reusable item has an `id`. Bullets also have IDs. Job-specific CVs refer to those IDs from `selection.yaml`.

Job folders are ignored by Git because they can contain private job descriptions, selections, and generated CVs. Local job folders should use IDs from whichever master data file is configured for generation.

Generated CVs order selected experience and selected projects by recency at render time. Current or ongoing items such as `Present`, `Current`, or `Ongoing` appear first, followed by dated items from newest to oldest. This means future additions only need accurate `start_date`/`end_date` values for experience or `date` values for projects; manual `selection.yaml` ordering does not control these two rendered sections.

## Job Folders

Each job folder contains:

- `job_config.yaml`: company, role, variant, template, output name, section order, and display flags
- `job_description.md`: pasted job description or notes
- `selection.yaml`: selected education, experience, projects, bullets, skills, and custom section items

Claude-generated job folders can also include:

- `cv_requirements.md`
- `llm_prompt.md`
- `llm_refine_prompt.md`
- `one_page_enforcement.md`
- `job_summary.txt`
- `selection_rationale.md`
- `revision_feedback.md`
- generated `.tex`
- compiled `.pdf`

## Claude Intake Behavior

The v1 intake command creates a new job folder from pasted job description text. It can either call Claude through the Anthropic API for job parsing and selection, or run in prompt-only mode so the exact prompt package can be inspected first.

In automatic Claude mode, job folders are named from the generated company and role, for example `acme_software_engineer`. If a folder already exists, the script appends a numeric suffix. Use `--job-id` only when overriding that default.

The default Claude model is set in `scripts/create_job_from_description.py`. Override it without editing code by setting `CV_LLM_MODEL`.

If the LLM returns invalid IDs or malformed JSON, the script fails before writing the generated YAML/CV unless it is inside an automatic one-page enforcement correction loop.

The LLM prompt asks for selected experience and projects in recency order, and the candidate inventory includes their dates. The generator still sorts those sections again before rendering so manually edited or older selections remain consistent.

Per-job CV requirements can be supplied interactively, inline with `--cv-requirements`, or from a file with `--cv-requirements-file`. These can control emphasis, omissions, ordering, tone, length, or constraints on what not to mention.

## One-Page Enforcement

Default v1 behavior:

- CV length is set to `one_page` unless requirements or refinement feedback explicitly ask for a longer CV.
- When `--compile-pdf` is used, the script compiles the PDF and checks that the page count is exactly one page with `pdfinfo`.
- If the PDF is longer than one page, the script first persists a compact `page_margin` in `job_config.yaml` by halving the current margin and recompiles without spending an LLM call.
- If compact margins still do not produce a one-page PDF, the script asks Claude for a shorter complete `job_config` and `selection`.
- A Claude-backed create/refine command with `--compile-pdf` is capped at two Claude calls total: one initial generation/refinement call and one automatic one-page correction call. Further changes should be made with explicit refinement.
- Experience and project bullets should be short enough to fit on one CV line whenever possible.
- Education stays compact.
- Coursework and education bullets are hidden unless explicitly requested or unusually relevant.
- Internship/job technology lists are hidden by default.
- Project technology lists are hidden by default and capped at three items when shown.
- Projects with GitHub, Devpost, or Kaggle links are preferred when relevance is otherwise comparable.
- Relevant projects without those links can still be selected and will render without clickable project links.
- Section headings are forced onto separate lines by the LaTeX template.

## Editing The Career Database

### Add Education

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

Select it in a job folder:

```yaml
education:
  - university_msc_data_science
```

### Add Experience

Keep bullets atomic and reusable:

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

Projects should include portfolio links where possible:

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

Select only relevant skills for a job:

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

`job_config.yaml` supports:

- `technical_ml`
- `software_engineering`
- `data_science`
- `startup_events`
- `leadership_community`
- `general`

Variants influence default section ordering when `sections_order` is missing. Explicit `sections_order` always wins.

Use `technical_skills` when the section heading should read "Technical Skills". Use `skills` when the heading should read "Skills". Both render selected skill categories dynamically.

## LaTeX Template

The default template is `templates/cv_template.tex.j2`.

It is compact, single-column, ATS-friendly, and LaTeX-native:

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

Check that the ID in `selection.yaml` exactly matches an ID in the master data file currently being used.

`Selected bullet does not belong to selected item`

Bullet IDs are scoped to their parent experience or project. Confirm the bullet is listed under the selected item in the configured master data file.

`Selected skill does not exist`

Skills must first be listed in the configured master data file, then selected by category in `selection.yaml`.

`Template not found`

Confirm `template` in `job_config.yaml` matches a file in `templates/`.

`No LaTeX compiler found`

Install `latexmk`, `tectonic`, or `pdflatex`. On macOS, MacTeX is the common full LaTeX distribution; Tectonic is a lighter alternative.

`Cannot determine compiled PDF page count`

Install `pdfinfo`, or run without `--compile-pdf` if page-count enforcement is not needed.

`A job folder fails with private data`

Job folders need selections that reference IDs in the configured master data:

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

PDF parsing is not implemented in this MVP.

## Future Extensions

The current MVP already has Anthropic-backed v1 job intake, basic job parsing and selection, prompt-only prompt export, refinement, and one-page PDF enforcement when compiling.

Future enhancements could include:

- additional LLM providers beyond Anthropic
- richer layout-aware fit checks beyond PDF page count
- multiple CV templates
- cover letter generation
- application tracking
- deeper semantic matching between job descriptions and career bullets
- Streamlit UI
- SQLite migration if YAML becomes too limiting
