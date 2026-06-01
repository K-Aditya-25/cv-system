# Changelog

## 2026-06-01

- Added a personal Telegram bot with long polling, private-chat whitelisting, pasted or `.txt`
  job-description intake, background CV generation, PDF delivery, and explicit CV refinement.
- Added startup handling that discards offline messages and clears transient work so stale messages
  cannot spend model credits after a restart.
- Added `/refine` for selecting an existing generated CV and `/reset` for clearing the current chat
  session and active CV without deleting generated job folders.
- Documented the future refinement context router for reducing unnecessary LLM prompt tokens.
- Documented the planned Supermemory retrieval layer, guardrails, and phased rollout.
- Added Telegram workflow regression tests and ignored local SQLite conversation state.

## 2026-05-31

- Split the remaining oversized Python modules and test files into focused files under the 100-line limit.
- Added a deterministic tracked-Python-file line-count check and a GitHub Actions workflow that rejects files over 100 lines.

## 2026-05-24

- Split `scripts/create_job_from_description.py` into focused modules under `scripts/job_creation`.
- Kept `scripts/create_job_from_description.py` as a thin compatibility entrypoint for existing imports, tests, and direct CLI execution.
- Added persistent Claude interactive CV generation and refinement behavior, including automatic recompilation after manual TeX edits.
- Documented deterministic skill-category repair and validation retry behavior for Claude selections.
- Added tests covering skill-category repair and validation retry prompts.
- Added `project_charter` with project rules for modular, verifiable, readable, and understandable Python code.
- Added the rule that Python files must not exceed 100 lines.
- Added the project changelog and its push-time update rule.

## 2026-05-15

- Added one-page PDF enforcement with compact margin fallback for Claude-backed CV generation and refinement.
- Added automatic removal of the `additional_information` section before spending an LLM retry on page-length reduction.
- Capped automatic one-page enforcement to the configured Claude call budget.
- Expanded tests for one-page PDF enforcement and retry behavior.

## 2026-05-14

- Split public README content from deeper implementation details in `docs/project-details.md`.
- Added validation retry behavior for invalid LLM selections.
- Allowed relevant selected projects even when the master data has no GitHub, Devpost, or Kaggle link.
- Stopped tracking generated job folders and output artifacts.

## 2026-05-09

- Added the LLM-backed job intake and CV refinement workflow.
- Added prompt-only and Claude provider flows for generating tailored job folders and CV files.
