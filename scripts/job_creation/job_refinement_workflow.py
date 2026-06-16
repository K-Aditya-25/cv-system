from __future__ import annotations

import argparse
from pathlib import Path

from .compact_refiner import refine_job_with_compact_prompt
from .job_refiner import refine_job_with_feedback as refine_job_with_full_context
from .local_refiner import refine_job_with_local_edit
from .refine_context import load_refine_context
from .refinement_route_diagnostics import format_route_log
from .refinement_router import route_refinement_feedback
from .refinement_routes import RefinementRouteKind


def refine_job_with_feedback(
    args: argparse.Namespace,
    master_data_path: Path,
    job_folder: Path,
    revision_feedback: str,
) -> tuple[Path, int | None]:
    context = load_refine_context(master_data_path, job_folder)
    route = route_refinement_feedback(revision_feedback, context)
    print(format_route_log(route), flush=True)
    if route.kind == RefinementRouteKind.LOCAL_EDIT and route.local_action is not None:
        return refine_job_with_local_edit(args, context, revision_feedback, route.local_action)
    if route.kind == RefinementRouteKind.COMPACT_REFINEMENT:
        return refine_job_with_compact_prompt(args, context, revision_feedback)
    return refine_job_with_full_context(
        args, master_data_path, context.job_folder, revision_feedback,
    )
