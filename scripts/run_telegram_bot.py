import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.telegram_bot.config import load_config
from scripts.telegram_bot.runtime import BotRuntime


def main() -> int:
    try:
        config = load_config()
    except ValueError as error:
        print(f"Telegram bot configuration failed: {error}", file=sys.stderr)
        return 1
    BotRuntime(config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
