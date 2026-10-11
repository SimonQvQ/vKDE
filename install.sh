#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
cat <<'ART'
          ██╗   ██╗██╗  ██╗██████╗ ███████╗
          ██║   ██║██║ ██╔╝██╔══██╗██╔════╝
          ██║   ██║█████╔╝ ██║  ██║█████╗
          ╚██╗ ██╔╝██╔═██╗ ██║  ██║██╔══╝
           ╚████╔╝ ██║  ██╗██████╔╝███████╗
            ╚═══╝  ╚═╝  ╚═╝╚═════╝ ╚══════╝
            very kool desktop environment · 0.1
ART
if [[ ${1:-} == --help ]]; then
  echo 'Usage: ./install.sh [--dry-run | --assets-only | --restore BACKUP]'
  exit 0
fi
case ${1:-} in
  ''|--dry-run|--assets-only) [[ $# -le 1 ]] || exit 2 ;;
  --restore) [[ $# -eq 2 ]] || { echo 'Supply the backup path.' >&2; exit 2; } ;;
  *) echo 'Unknown option; see --help.' >&2; exit 2 ;;
esac
if [[ ${1:-} != --restore ]]; then
  sha256sum --check assets/SHA256SUMS
fi
command -v python3 >/dev/null || { echo 'Install Python 3 first.' >&2; exit 1; }
if [[ ${1:-} != --dry-run && ${1:-} != --restore ]]; then
  [[ $EUID != 0 ]] || { echo 'Run as your desktop user, not root.' >&2; exit 1; }
  command -v pacman >/dev/null || { echo 'v0.1 automated installation supports Arch Linux with Plasma 6.' >&2; exit 1; }
  pacman -Q plasma-workspace | awk '$2 ~ /^6\./ {ok=1} END {exit !ok}' || { echo 'An existing Plasma 6 installation is required.' >&2; exit 1; }
  missing=()
  for pkg in kvantum python-dbus python-gobject qt6-tools; do
    pacman -Q "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
  done
  if ((${#missing[@]})); then sudo pacman -S --needed "${missing[@]}"; fi
fi
exec python3 scripts/install.py "$@"
