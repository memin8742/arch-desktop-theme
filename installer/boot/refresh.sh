#!/usr/bin/bash
set -euo pipefail
umask 022
if ! mountpoint -q /boot; then
    printf '%s\n' 'The EFI system partition is not mounted at /boot.' >&2
    exit 1
fi

work=$(mktemp -d)
cleanup() {
    rm -f -- "$work/mkinitcpio.conf" "$work/initramfs.img" "$work/contents"
    rmdir -- "$work"
}
trap cleanup EXIT

python3 - "$work/mkinitcpio.conf" <<'PY'
from pathlib import Path
import re
import sys

config = Path('/etc/mkinitcpio.conf').read_text()
match = re.search(r'(?m)^HOOKS=\(([^)\n]*)\)', config)
if not match or 'systemd' not in match[1].split():
    raise SystemExit('Arch Blue expects a systemd-based initramfs.')
hooks = match[1].split()
if 'plymouth' not in hooks:
    hooks.insert(hooks.index('systemd') + 1, 'plymouth')
    config = config[:match.start(1)] + ' '.join(hooks) + config[match.end(1):]
Path(sys.argv[1]).write_text(config)
PY

mkinitcpio -c "$work/mkinitcpio.conf" -k /boot/vmlinuz-linux -g "$work/initramfs.img"
lsinitcpio "$work/initramfs.img" >"$work/contents"
grep -q 'plymouth/themes/arch-blue/arch-blue.script' "$work/contents"
grep -q 'plymouth/themes/arch-blue/boot-caption.png' "$work/contents"
install -m0644 /boot/vmlinuz-linux /boot/vmlinuz-arch-blue.new
install -m0644 "$work/initramfs.img" /boot/initramfs-arch-blue.img.new
mv -f -- /boot/vmlinuz-arch-blue.new /boot/vmlinuz-arch-blue
mv -f -- /boot/initramfs-arch-blue.img.new /boot/initramfs-arch-blue.img
