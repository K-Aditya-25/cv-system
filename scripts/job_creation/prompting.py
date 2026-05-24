from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .paths import ROOT


def write_yaml(path: Path, payload: Any) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def yaml_text(payload: Any) -> str:
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)


def render_prompt_template(template_name: str, **context: Any) -> str:
    env = Environment(
        loader=FileSystemLoader(ROOT / "prompts"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    return env.get_template(template_name).render(**context)
