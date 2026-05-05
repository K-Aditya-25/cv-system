from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from schemas.career_schema import CareerDatabase  # noqa: E402


def load_yaml(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc


def main() -> int:
    master_path = ROOT / "data" / "master.yaml"
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
