from __future__ import annotations

from scripts.generate_cv import resolve_master_data_path
from .cli_args import parse_args
from .command_handlers import create_new_job, refine_existing_job
from .interactive import run_interactive_claude_session
from .paths import ROOT
from .text_utils import normalize_provider, is_claude_provider

def main() -> int:
    args = parse_args()
    args.provider = normalize_provider(args.provider)

    master_data_path = args.master_data
    if master_data_path is None:
        master_data_path = resolve_master_data_path()
    elif not master_data_path.is_absolute():
        master_data_path = ROOT / master_data_path

    if args.interactive and is_claude_provider(args.provider):
        return run_interactive_claude_session(args, master_data_path)

    if args.refine_job:
        return refine_existing_job(args, master_data_path)
    return create_new_job(args, master_data_path)


if __name__ == "__main__":
    raise SystemExit(main())
