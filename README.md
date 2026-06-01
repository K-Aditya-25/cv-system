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
- Optional: `ANTHROPIC_API_KEY` for the Claude-powered interactive CV session
- Optional: `TAVILY_API_KEY` and `BRAVE_SEARCH_API_KEY` for Telegram job-URL search fallbacks
- Optional: `TELEGRAM_RESOLVER_PLAYWRIGHT=1` to render job pages that require JavaScript

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

Check that every tracked Python file follows the 100-line limit:

```bash
uv run python scripts/check_python_line_lengths.py
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

## Claude Interactive CV Session

Store your Anthropic API key in an ignored local env file:

```bash
read -s ANTHROPIC_API_KEY
printf 'ANTHROPIC_API_KEY=%s\n' "$ANTHROPIC_API_KEY" > .env.local
unset ANTHROPIC_API_KEY
```

Start the main Claude-powered CV workflow:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/create_job_from_description.py \
  --interactive \
  --provider claude \
  --compile-pdf
```

The session prompts for a job description first. Paste it, then type `END` on its own line. It then prompts for custom CV requirements or changes; enter those and type `END` again.

After that, the command calls Claude, writes the job folder, generates the `.tex` file, compiles the PDF, and stays open. Review the generated PDF while the process is still running. To refine it, enter feedback in the terminal and type `END`; each follow-up prompt updates the same job folder through the refinement workflow. Press `Ctrl-Q` at any prompt to exit.

Claude responses are validated before rendering. If Claude puts a known skill under the wrong category, the workflow moves it to the category defined in the master data. If Claude selects a skill that is not in the master data at all, the workflow sends one correction prompt with the validation error and allowed skill list.

While the session is running with `--compile-pdf`, manual edits to the generated `.tex` file automatically trigger:

```bash
bash scripts/compile_pdf.sh path/to/generated_cv.tex
```

Resume a persistent Claude session from an existing job folder:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/create_job_from_description.py \
  --refine-job jobs/my_real_job_folder \
  --interactive \
  --provider claude \
  --compile-pdf
```

In this mode, the first prompt you enter is refinement feedback for that existing job folder.

Use prompt-only mode only when you want to inspect the generated prompt without calling Claude:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/create_job_from_description.py \
  path/to/job_description.txt \
  --cv-requirements "Custom CV requirements here" \
  --provider prompt-only
```

When `--compile-pdf` is used with Claude generation or refinement, the workflow compiles the CV and checks that the PDF is exactly one page. If it is too long, the workflow first retries with compact margins, then removes the `additional_information` section, then can spend one automatic Claude revision call. That keeps each generation/refinement capped at two Claude calls total: one main generation/refinement call and one one-page correction call.

## Telegram Bot

The personal Telegram bot runs locally with long polling. After `/new`, it accepts a generic public
HTTPS job URL with LinkedIn-prioritized handling. It extracts with HTTP first, can use an optional
Playwright fallback, and can search with Tavily first and Brave second only when direct extraction
fails and their API keys are configured. Direct LinkedIn and other public job URLs can succeed
without either search key. If URL intake cannot resolve the posting, the bot explicitly asks for a
careers-page or direct job-post URL retry. Pasted text chunks and UTF-8 `.txt` documents remain a
deterministic fallback. The bot reports progress in plain language and confirms the extracted
company and role when available, then asks for optional CV instructions, runs the existing Claude
workflow, and replies with the compiled PDF.

Later ordinary text messages refine the active CV until `/new` starts another job. After restarting
the bot process, offline messages are discarded intentionally. Use `/new` for a new job or `/refine`
to choose an existing generated CV before sending feedback.

Create a bot with Telegram's `@BotFather`, then store its token and your allowed private-chat ID in
the ignored `.env.local` file:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_CHAT_IDS=123456789
TAVILY_API_KEY=...          # optional
BRAVE_SEARCH_API_KEY=...    # optional
TELEGRAM_RESOLVER_PLAYWRIGHT=1  # optional; requires Playwright and Chromium
```

Use `/whoami` in a private chat to discover its numeric chat ID. `CV_MASTER_DATA` must be set
explicitly when the bot starts so it cannot accidentally generate a CV from example data:

```bash
CV_MASTER_DATA=data/master.private.yaml \
uv run python scripts/run_telegram_bot.py
```

The bot supports:

| Command | Behavior |
| --- | --- |
| `/start`, `/help` | Show the workflow and command reference. |
| `/whoami` | Show the current private-chat ID. |
| `/new` | Start collecting a new job description. |
| `/refine` | List generated CVs and choose one to refine. |
| `/done` | Submit accumulated description chunks or optional instructions. |
| `/none` | Generate without additional CV instructions. |
| `/cancel` | Discard the current draft or retained recovery action. |
| `/reset` | Clear the session and active CV without deleting generated files. |
| `/status` | Show the current conversation state. |
| `/resend` | Send the latest completed PDF again. |

URL intake accepts public HTTPS targets only and applies safety checks before retrieval. Search API
keys are read from the environment and are not persisted in Telegram state, job folders, prompts,
or generated files. Send pasted chunks or a UTF-8 `.txt` file after `/new` when URL resolution is
not suitable. Telegram state is kept locally in ignored SQLite file `data/telegram_bot.sqlite3`.
The bot is for personal use: CV operations only run in explicitly allowed private chats.

Indeed and GradIreland job-board adapters are planned future extensions.

## More Detail

Backend details, file formats, data modeling guidance, prompt behavior, troubleshooting, and future extension notes live in [docs/project-details.md](docs/project-details.md).
