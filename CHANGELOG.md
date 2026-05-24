# Changelog

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
