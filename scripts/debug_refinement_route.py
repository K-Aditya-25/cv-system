from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_cv import resolve_master_data_path
from scripts.job_creation.refine_context import load_refine_context
from scripts.job_creation.refinement_route_diagnostics import format_route_cli
from scripts.job_creation.refinement_router import route_refinement_feedback


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run a CV refinement route decision.")
    parser.add_argument("job_folder", type=Path)
    parser.add_argument("feedback")
    parser.add_argument(
        "--master-data",
        type=Path,
        help="Master data YAML path. Defaults like the main CV CLI.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    master_data = _master_data_path(args.master_data)
    context = load_refine_context(master_data, args.job_folder)
    route = route_refinement_feedback(args.feedback, context)
    print(format_route_cli(route))
    return 0


def _master_data_path(path: Path | None) -> Path:
    if path is None:
        return resolve_master_data_path()
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
