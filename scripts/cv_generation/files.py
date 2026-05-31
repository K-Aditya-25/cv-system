import os
import re
from pathlib import Path
from typing import Any

import yaml

from scripts.cv_generation.errors import CvGenerationError

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MASTER_DATA_PATH = ROOT / "data" / "master.example.yaml"


def resolve_master_data_path() -> Path:
    configured_path = os.environ.get("CV_MASTER_DATA") or os.environ.get("CVMasterData")
    if configured_path:
        path = Path(configured_path)
        return path if path.is_absolute() else ROOT / path
    return DEFAULT_MASTER_DATA_PATH


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise CvGenerationError(f"File not found: {path}") from None
    except yaml.YAMLError as exc:
        raise CvGenerationError(f"Invalid YAML in {path}: {exc}") from exc


def safe_latex_name(output_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", output_name):
        raise CvGenerationError(
            "output_name must contain only letters, numbers, dashes, underscores, or dots"
        )
    return output_name if output_name.endswith(".tex") else f"{output_name}.tex"
