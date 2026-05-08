from __future__ import annotations

import sys
import os
from pathlib import Path

import yaml
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from schemas.career_schema import CareerDatabase  # noqa: E402


DEFAULT_MASTER_DATA_PATH = ROOT / "data" / "master.example.yaml"


def resolve_master_data_path() -> Path:
    configured_path = os.environ.get("CV_MASTER_DATA") or os.environ.get("CVMasterData")
    if configured_path:
        path = Path(configured_path)
        return path if path.is_absolute() else ROOT / path
    return DEFAULT_MASTER_DATA_PATH


def load_yaml(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc


def main() -> int:
    master_path = resolve_master_data_path()
    try:
        payload = load_yaml(master_path)
        CareerDatabase.model_validate(payload)
    except FileNotFoundError:
        print(f"Data file not found: {master_path}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(f"Validation failed for {master_path}:", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1

    print(f"OK: {master_path} is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
