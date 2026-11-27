"""Identify the themed terminal from a root shell without reading user shell code."""

import os
from pathlib import Path


def find_terminal():
    pid = os.getppid()
    for _ in range(16):
        if pid <= 1:
            break
        process = Path('/proc') / str(pid)
        try:
            arguments = (process / 'cmdline').read_bytes().split(b'\0')
            status = (process / 'status').read_text().splitlines()
        except OSError:
            break
        if any(arg.endswith(b'/.local/share/arch-desktop-theme/terminal.py') for arg in arguments):
            return pid
        pid = int(next(line.split()[1] for line in status if line.startswith('PPid:')))
    return None


if __name__ == '__main__':
    terminal = find_terminal()
    if terminal:
        print(terminal)
    else:
        raise SystemExit(1)
