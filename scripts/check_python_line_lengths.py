from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAX_LINES = 100
ROOT = Path(__file__).resolve().parents[1]


def uploaded_python_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / path for path in sorted(set(result.stdout.splitlines()))]


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    counts = [(path, line_count(path)) for path in uploaded_python_files()]
    violations = [(path, count) for path, count in counts if count > MAX_LINES]
    if violations:
        print(f"Python files must not exceed {MAX_LINES} lines:", file=sys.stderr)
        for path, count in violations:
            print(f"- {path.relative_to(ROOT)}: {count} lines", file=sys.stderr)
        return 1
    print(f"OK: all uploaded Python files are at most {MAX_LINES} lines.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
