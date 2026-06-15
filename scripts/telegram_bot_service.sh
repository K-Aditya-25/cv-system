#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/adityakharbanda/cv-system"
LABEL="com.adityakharbanda.cv-system.telegram-bot"
PLIST_NAME="${LABEL}.plist"
SOURCE_PLIST="${ROOT}/launchd/${PLIST_NAME}"
TARGET_DIR="${HOME}/Library/LaunchAgents"
TARGET_PLIST="${TARGET_DIR}/${PLIST_NAME}"
DOMAIN="gui/$(id -u)"
SERVICE="${DOMAIN}/${LABEL}"

usage() {
  printf 'Usage: %s {install|start|stop|status|restart|uninstall}\n' "$0"
}

require_macos_tools() {
  command -v launchctl >/dev/null
  command -v plutil >/dev/null
}

is_loaded() {
  launchctl print "${SERVICE}" >/dev/null 2>&1
}

install_service() {
  require_macos_tools
  mkdir -p "${TARGET_DIR}" "${ROOT}/logs"
  plutil -lint "${SOURCE_PLIST}" >/dev/null
  cp "${SOURCE_PLIST}" "${TARGET_PLIST}"
  chmod 644 "${TARGET_PLIST}"
  printf 'Installed %s\n' "${TARGET_PLIST}"
}

start_service() {
  require_macos_tools
  [[ -f "${TARGET_PLIST}" ]] || install_service
  mkdir -p "${ROOT}/logs"
  if is_loaded; then
    launchctl kickstart -k "${SERVICE}"
  else
    launchctl bootstrap "${DOMAIN}" "${TARGET_PLIST}"
  fi
  printf 'Started %s\n' "${SERVICE}"
}

stop_service() {
  require_macos_tools
  if is_loaded; then
    launchctl bootout "${SERVICE}"
    printf 'Stopped %s\n' "${SERVICE}"
  else
    printf 'Not loaded: %s\n' "${SERVICE}"
  fi
}

status_service() {
  require_macos_tools
  if is_loaded; then
    launchctl print "${SERVICE}"
  else
    printf 'Not loaded: %s\n' "${SERVICE}"
  fi
}

uninstall_service() {
  stop_service
  rm -f "${TARGET_PLIST}"
  printf 'Removed %s\n' "${TARGET_PLIST}"
}

case "${1:-}" in
  install) install_service ;;
  start) start_service ;;
  stop) stop_service ;;
  status) status_service ;;
  restart) stop_service; start_service ;;
  uninstall) uninstall_service ;;
  *) usage; exit 2 ;;
esac
