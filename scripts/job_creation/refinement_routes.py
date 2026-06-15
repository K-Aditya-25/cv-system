from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RefinementRouteKind(str, Enum):
    LOCAL_EDIT = "local_edit"
    COMPACT_REFINEMENT = "compact_refinement"
    FULL_CONTEXT_REFINEMENT = "full_context_refinement"


@dataclass(frozen=True)
class LocalAction:
    type: str
    field: str | None = None
    value: Any = None
    section: str | None = None
    item_kind: str | None = None
    item_id: str | None = None


@dataclass(frozen=True)
class RefinementRoute:
    kind: RefinementRouteKind
    reason: str
    required_context: tuple[str, ...]
    confidence: float = 1.0
    local_action: LocalAction | None = None


LOCAL_CONTEXT = ("job_config.yaml", "selection.yaml")
COMPACT_CONTEXT = ("job_config.yaml", "selection.yaml", "generated_cv.tex")
FULL_CONTEXT = (
    "job_description.md",
    "cv_requirements.md",
    "job_config.yaml",
    "selection.yaml",
    "candidate_inventory",
)


def full_context_route(reason: str, confidence: float = 1.0) -> RefinementRoute:
    return RefinementRoute(
        RefinementRouteKind.FULL_CONTEXT_REFINEMENT,
        reason,
        FULL_CONTEXT,
        confidence,
    )
