# Project Details

This document keeps the implementation and maintenance details out of the README.

## Architecture

The system is intentionally small and file-based:

- Python scripts run the workflow.
- YAML stores career data and job-specific selections.
- Pydantic validates data files.
- Jinja2 renders LaTeX.
- LaTeX compiles the final PDF.
- Claude through the Anthropic API can run a persistent interactive CV generation and refinement session.
- A personal Telegram bot can run that workflow through long polling and reply with generated PDFs.

This is not a web app. It does not use PostgreSQL or a complex database. YAML is used first because it is readable, Git-friendly, and easy to edit. The Telegram adapter uses a local SQLite file only for conversation state.

## Folder Structure

```text
cv-system/
  .github/
    workflows/
      python-line-length.yml
  README.md
  CHANGELOG.md
  project_charter
  docs/
    project-details.md
    telegram-workflow-plan.md
  pyproject.toml
  uv.lock
  .python-version
  data/
    master.example.yaml
    master.private.yaml   # local only, ignored by Git
    telegram_bot.sqlite3  # local Telegram state, ignored by Git
    raw_inputs/
      README.md
  schemas/
    career_schema.py       # compatibility exports
    base.py
    common.py
    custom_sections.py
    database.py
    job_config.py
    primary_items.py
    secondary_items.py
    selection.py
    validators.py
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
    check_python_line_lengths.py
    create_job_from_description.py
    generate_cv.py         # compatibility entrypoint and exports
    run_telegram_bot.py     # personal Telegram long-polling entrypoint
    compile_pdf.sh
    cv_generation/         # deterministic renderer modules
    job_creation/          # Claude intake/refinement modules
    telegram_bot/          # Telegram API, state, routing, and workflow adapter
  outputs/
```

## Python File Size Check

The project charter limits every Python file to at most 100 physical lines. Check the current
uploaded file set locally with:

```bash
python3 scripts/check_python_line_lengths.py
```

The checker asks Git for tracked and non-ignored untracked `*.py` files, reports every oversized
file, and exits non-zero when it finds a violation. GitHub Actions runs the same command on every
push and pull request through `.github/workflows/python-line-length.yml`.

## Data Privacy

The repo is designed so code, schemas, templates, and fake example data can be public while real career data stays local.

- `data/master.example.yaml` is safe dummy data committed to the repo.
- `data/master.private.yaml` is the real local career database and is ignored by Git.
- `data/master.yaml` is also ignored for compatibility.
- `data/raw_inputs/*` is ignored so old CVs, LinkedIn exports, and notes are not uploaded.
- `.env` and `.env.*` are ignored so local API keys are not uploaded.
- `data/telegram_bot.sqlite3` is ignored because it contains local Telegram conversation state.

When using the Claude workflow, the Anthropic API receives the job description, user CV requirements or revision feedback, current job selection state during refinement, and a compact candidate inventory containing career IDs, skills, bullet text, tags, strengths, and project links. Use the manual workflow for roles or data you do not want to send to an external API.

The API key is not included in prompts, job files, or generated CVs. The Claude workflow script reads `ANTHROPIC_API_KEY` from the process environment, `.env.local`, or `.env`.

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

## Claude Interactive Session Behavior

The primary Claude command starts a persistent terminal session:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/create_job_from_description.py \
  --interactive \
  --provider claude \
  --compile-pdf
```

The session first prompts for a job description, then prompts for custom CV requirements or changes. Each multiline prompt is submitted by typing `END` on its own line. `Ctrl-Q` exits the session. The terminal reader temporarily disables normal terminal flow control while reading so `Ctrl-Q` can be caught by the Python process.

After the first submission, the script calls Claude, writes a job folder, generates the `.tex` file, compiles the PDF when `--compile-pdf` is set, and stays open. Every later prompt in the same session is treated as revision feedback for the same job folder and runs the refinement path in the background.

An existing job folder can be resumed in the same persistent loop:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/create_job_from_description.py \
  --refine-job jobs/my_real_job_folder \
  --interactive \
  --provider claude \
  --compile-pdf
```

In that mode, the first prompt is revision feedback for the existing job folder.

`--provider claude` is the user-facing provider value. `--provider anthropic` is still accepted as a backwards-compatible alias. Prompt-only mode still writes the prompt package without calling Claude.

In automatic Claude mode, job folders are named from the generated company and role, for example `acme_software_engineer`. If a folder already exists, the script appends a numeric suffix. Use `--job-id` only when overriding that default.

The default Claude model is set in `scripts/create_job_from_description.py`. Override it without editing code by setting `CV_LLM_MODEL`.

If the LLM returns malformed JSON, the script fails before writing the generated YAML/CV. If it returns structurally valid JSON with invalid selections, the repair/retry layer below runs before the command accepts the generated YAML.

The LLM prompt asks for selected experience and projects in recency order, and the candidate inventory includes their dates. The generator still sorts those sections again before rendering so manually edited or older selections remain consistent.

Per-job CV requirements can be supplied interactively, inline with `--cv-requirements`, or from a file with `--cv-requirements-file`. These can control emphasis, omissions, ordering, tone, length, or constraints on what not to mention.

While a Claude interactive session is running with `--compile-pdf`, the script watches the active generated `.tex` file. Manual edits to that file trigger `scripts/compile_pdf.sh` automatically. The watcher pauses while Claude generation or refinement is running, then resumes against the latest generated `.tex` path.

## Telegram Bot Behavior

Phase 1 adds a local personal Telegram bot as another interface to the Claude workflow. It uses the
official Telegram Bot API directly through the Python standard library. Long polling keeps setup
small: no public web server, webhook endpoint, domain, or database server is required.

Create the bot through Telegram's `@BotFather`. Store the token and allowed numeric private-chat IDs
outside Git in `.env.local`, then start the bot with an explicit private career-data file:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_CHAT_IDS=123456789,987654321
```

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/run_telegram_bot.py
```

The bot refuses to start unless `CV_MASTER_DATA`, `TELEGRAM_BOT_TOKEN`, and
`TELEGRAM_ALLOWED_CHAT_IDS` are configured. `/whoami` is available in private chats to discover the
numeric ID before adding it to the whitelist. CV operations reject unauthorized chats, groups, and
channels.

After `/new`, send the job description as one or more text chunks or upload a UTF-8 `.txt` file.
The `.txt` file is limited to 250 KB. `/done` submits accumulated chunks; then send optional CV
instructions and use `/done`, or send `/none` to use the default requirements. The bot compiles and
sends the generated PDF. Later ordinary text messages refine the active job folder and produce an
updated PDF until `/new` begins another job.

On startup, the bot discards Telegram updates received while it was offline and clears transient
draft, queue, and in-flight state. After every restart, `/new` opens a new job session and `/refine`
lists generated CVs so the user can choose an existing job folder before sending feedback. This
prevents stale or accidental offline messages from triggering Claude calls.

Use `/reset` to return the current chat to an idle state without restarting the bot process. It
clears drafts, queued work, recovery state, and the selected CV pointers, so `/resend` is unavailable
until another CV is generated or selected through `/refine`. Generated job folders remain on disk.

The bot stores the Telegram update offset, conversation state, current job folder, latest PDF,
queued refinements, and recoverable interrupted work in ignored local SQLite file
`data/telegram_bot.sqlite3`. A single background worker serializes generation and refinement so the
polling loop stays responsive and two updates cannot mutate the same job folder concurrently.

## LLM Selection Repair And Retry

Claude responses are not trusted directly. The workflow applies a two-layer validation process before writing final YAML or rendering the CV.

Layer 1 is deterministic skill-category repair. The script builds a reverse index from the configured master data skills:

```text
skill name -> canonical skill category
```

For each skill returned in `selection.skills`:

- If the selected skill exists in the selected category, it is kept unchanged.
- If the selected skill exists in a different master-data category, it is moved to that category.
- If the selected skill does not exist anywhere in master data, it is left in place so validation can fail explicitly.

This handles category placement errors such as Claude returning `Explainable AI` under `machine_learning` when the master data defines it under `ai_llm_engineering`. The repair is exact-string based; it does not fuzzy-match or infer similar skills.

Layer 2 is one Claude validation retry for main generation/refinement calls. After deterministic repair, the script validates the complete payload by building the render context. This catches invalid skill categories, unknown skills, missing IDs, invalid bullet selections, invalid custom section items, and similar issues before the generated YAML is accepted.

If validation still fails, the script sends Claude a compact correction prompt containing:

- the actual validation error raised at runtime
- the allowed skills grouped by category from the configured master data
- the previous JSON response from Claude
- rules requiring exact spelling, exact capitalization, valid categories, JSON-only output, and the complete response shape

The retry prompt intentionally does not resend the full job description or full candidate inventory for skill-only correction. The previous response plus the allowed skills are enough to correct unknown or misplaced skills without bloating the retry context. If the retry still fails validation, the command fails and prints the validation error.

Automatic one-page enforcement also receives deterministic skill-category repair. It does not spend an additional open-ended validation retry beyond the existing one-page enforcement call budget.

## One-Page Enforcement

Default behavior:

- CV length is set to `one_page` unless requirements or refinement feedback explicitly ask for a longer CV.
- When `--compile-pdf` is used, the script compiles the PDF and checks that the page count is exactly one page with `pdfinfo`.
- If the PDF is longer than one page, the script first persists a compact `page_margin` in `job_config.yaml` by halving the current margin and recompiles without spending an LLM call.
- If compact margins still do not produce a one-page PDF, the script removes the `additional_information` section from `job_config.yaml` and `selection.yaml`, then regenerates and recompiles without spending an LLM call.
- If compact margins plus `additional_information` removal still do not produce a one-page PDF, the script asks Claude for a shorter complete `job_config` and `selection`. The automatic prompt tells Claude that margins have already been halved and the additional information section has already been removed, so the remaining task is to summarize and keep only the content that is absolutely necessary for the role.
- A Claude-backed generation/refinement with `--compile-pdf` is capped at two Claude calls total: one initial generation/refinement call and one automatic one-page correction call. Further changes should be made with explicit refinement feedback in the persistent session.
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

The current MVP already has Claude-backed persistent job intake/refinement, basic job parsing and selection, prompt-only prompt export, deterministic skill-category repair, validation retry for invalid LLM selections, one-page PDF enforcement when compiling, and automatic recompilation when the active generated `.tex` file is manually edited during an interactive session.

Future enhancements could include:

- Supermemory-backed memory for persistent candidate context, job history, preferences, and reusable career evidence across CV generation runs.
- A messaging-accessible CV agent over WhatsApp or iMessage. The agent should accept a job description, requested changes, and any custom prompts or constraints, then return the generated PDF directly in the message thread.
- A lightweight refinement planner that classifies Telegram feedback into deterministic local edits, compact LLM refinements, or retrieved/full-context refinements. Every route should update validated `job_config.yaml` and `selection.yaml`, regenerate `.tex`, and preserve the full-context path as a fallback.
- More memory-efficient LLM prompting so the system does not send the compact candidate inventory on every request. Possible approaches include retrieving only relevant career records, summarising stable profile context, caching job-independent context, and passing compact IDs plus evidence snippets.
- additional LLM providers beyond Anthropic
- richer layout-aware fit checks beyond PDF page count
- multiple CV templates
- cover letter generation
- application tracking
- deeper semantic matching between job descriptions and career bullets
- Streamlit UI
- SQLite migration if YAML becomes too limiting

The planned Supermemory integration is documented in
[`docs/telegram-workflow-plan.md`](telegram-workflow-plan.md). Supermemory should remain a derived
retrieval layer for reviewed career evidence, stable preferences, and application history.
`data/master.private.yaml` and per-job YAML files remain authoritative. Never persist credentials or
every casual Telegram message automatically.
