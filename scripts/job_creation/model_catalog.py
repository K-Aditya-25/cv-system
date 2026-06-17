from __future__ import annotations

import os
from dataclasses import dataclass

from .constants import DEFAULT_ANTHROPIC_MODEL

DEFAULT_GLM_TENSORIX_MODEL = "z-ai/glm-5.2"
DEFAULT_KIMI_TENSORIX_MODEL = "moonshotai/kimi-k2.6"


@dataclass(frozen=True)
class ModelRoute:
    key: str
    label: str
    provider: str
    model: str
    aliases: tuple[str, ...] = ()


def configured_model_routes() -> tuple[ModelRoute, ...]:
    return (
        ModelRoute(
            key="claude",
            label="Claude",
            provider="claude",
            model=os.environ.get(
                "CV_CLAUDE_MODEL",
                os.environ.get("CV_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL),
            ),
            aliases=("1", "anthropic", "sonnet"),
        ),
        ModelRoute(
            key="glm",
            label="GLM 5.2 (Tensorix)",
            provider="tensorix",
            model=os.environ.get(
                "CV_GLM_MODEL",
                os.environ.get("TENSORIX_GLM_MODEL", DEFAULT_GLM_TENSORIX_MODEL),
            ),
            aliases=("2", "glm 5.2", "glm-5.2", "zai", "z.ai"),
        ),
        ModelRoute(
            key="kimi",
            label="Kimi (Tensorix)",
            provider="tensorix",
            model=os.environ.get(
                "CV_KIMI_MODEL",
                os.environ.get("TENSORIX_KIMI_MODEL", DEFAULT_KIMI_TENSORIX_MODEL),
            ),
            aliases=("3", "kimi k2.6", "kimi-k2.6", "moonshot"),
        ),
    )


def model_route_for_key(key: str) -> ModelRoute | None:
    normalized = key.strip().lower()
    for route in configured_model_routes():
        if route.key == normalized:
            return route
    return None


def resolve_model_choice(choice: str) -> ModelRoute | None:
    normalized = " ".join(choice.strip().lower().split())
    if not normalized:
        return None
    for index, route in enumerate(configured_model_routes(), start=1):
        candidates = {
            str(index),
            route.key,
            route.label.lower(),
            route.model.lower(),
            *route.aliases,
        }
        if normalized in candidates:
            return route
    return None


def default_model_route() -> ModelRoute:
    configured = os.environ.get("CV_DEFAULT_MODEL", "").strip()
    if configured:
        route = resolve_model_choice(configured)
        if route is not None:
            return route
    return configured_model_routes()[0]


def model_menu_text() -> str:
    lines = ["Choose the model for this CV:"]
    for index, route in enumerate(configured_model_routes(), start=1):
        lines.append(f"{index}. {route.label} - {route.model}")
    lines.append("Reply with 1, 2, or 3.")
    return "\n".join(lines)
