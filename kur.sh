#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ${1:-} == --help ]]; then
  printf '%s\n' 'Arch Theme — Xfce kurulumu' 'bash kur.sh          Türkçe kurulum menüsü' 'bash kur.sh --plan   Değişiklik yapmadan inceleme' 'bash kur.sh --check  Kurulumu kontrol et'
  exit 0
fi
if [[ $(uname -s) != Linux || ! -f /etc/arch-release ]]; then
  printf '%s\n' 'Bu araç Arch Linux içindeki Xfce/X11 oturumunda çalışır.' >&2
  exit 1
fi
if [[ $EUID == 0 ]]; then
  printf '%s\n' 'sudo bash kur.sh kullanmayın. Kendi kullanıcınızla bash kur.sh çalıştırın.' >&2
  exit 1
fi
if ! command -v python3 >/dev/null; then
  if [[ $# != 0 ]]; then printf '%s\n' 'Önce Python kurulmalı: sudo pacman -Syu python'; exit 1; fi
  printf '%s\n' 'Kurulum aracı için Python gerekiyor. Arch güncellenerek Python kurulacak.'
  read -r -p 'Devam edilsin mi? [e/H] ' reply
  [[ $reply == [eE] ]] || exit 0
  sudo pacman -Syu --needed python
fi
exec python3 installer/install.py "$@"
