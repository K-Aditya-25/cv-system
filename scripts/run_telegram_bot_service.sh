#!/usr/bin/env bash
set -euo pipefail

cd /Users/adityakharbanda/cv-system

mkdir -p logs

export CV_MASTER_DATA=data/master.private.yaml
export PATH="/Users/adityakharbanda/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

exec uv run python scripts/run_telegram_bot.py
