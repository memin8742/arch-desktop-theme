import shutil
import subprocess
import sys
import time
from textwrap import wrap
from pathlib import Path

CYAN = '\x1b[38;2;73;174;230m'
WHITE = '\x1b[38;2;255;255;255m'
RESET = '\x1b[0m'
SPARK = '▁▂▃▄▅▆▇█'


def sample():
    parts = Path('/proc/stat').read_text().splitlines()[0].split()[1:9]
    cpu = [int(value) for value in parts]
    received = sent = 0
    for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
        name, _, fields = line.partition(':')
        if name.strip() == 'lo':
            continue
        values = fields.split()
        received += int(values[0])
        sent += int(values[8])
    return sum(cpu), cpu[3] + cpu[4], received + sent


def rates(duration=.12, points=8):
    cpu_rates, network_rates = [], []
    before = sample()
    for _ in range(points):
        started = time.monotonic()
        time.sleep(duration)
        total, idle, traffic = sample()
        elapsed = time.monotonic() - started
        cpu_rates.append(max(0, 1 - (idle - before[1]) / max(total - before[0], 1)))
        network_rates.append(max(0, traffic - before[2]) / elapsed)
        before = total, idle, traffic
    return cpu_rates, network_rates


def colored(value, color):
    return f'{color}{value}{RESET}' if sys.stdout.isatty() else value


def main():
    meminfo = {line.partition(':')[0]: int(line.split()[1])
               for line in Path('/proc/meminfo').read_text().splitlines()}
    total = meminfo['MemTotal'] / (1024 ** 2)
    used = (meminfo['MemTotal'] - meminfo['MemAvailable']) / (1024 ** 2)
    cpu_model = next((line.partition(':')[2].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                      if line.startswith('model name')), '')
    version = subprocess.check_output(['/bin/zsh', '--version'], text=True).split()
    os_name = next((line.partition('=')[2].strip('"')
                    for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('NAME=')), 'Linux')
    cols = shutil.get_terminal_size().columns
    arch = ['      /\\', '     /  \\', '    /    \\', '   /  ,,  \\', '  /   ||   \\', " /_-'    '-_\\"]
    values = [('OS', os_name), ('Shell', ' '.join(version[:2])),
              ('CPU', cpu_model), ('Memory', f'{used:.1f} / {total:.1f} GiB')]
    lines = []
    logo = arch if cols >= 40 else []
    value_width = max(15, cols - 9 - (17 if logo else 0))
    for key, value in values:
        pieces = wrap(value, value_width) or ['']
        lines.append(colored(f'{key + ":":<8}', CYAN) + colored(pieces[0], WHITE))
        lines.extend(' ' * 8 + colored(piece, WHITE) for piece in pieces[1:])
    for index in range(max(len(logo), len(lines))):
        art = colored(f'{logo[index]:<15}', CYAN) if index < len(logo) else ' ' * 15
        line = lines[index] if index < len(lines) else ''
        print(f'{art}  {line}' if logo else line)
    if sys.stdout.isatty():
        print((' ' * 17 if logo else '') + ''.join(f'\x1b[48;5;{color}m   ' for color in (17, 160, 208, 190, 40, 38, 27, 129)) + RESET)
    print()
    memory = 1 - meminfo['MemAvailable'] / meminfo['MemTotal']
    cpu, network = rates()
    bars = lambda values, scale: ''.join(SPARK[min(7, round(7 * rate / scale))] for rate in values)
    notices = [
        ('CPU', f'{sum(cpu) / len(cpu):.0%}', bars(cpu, 1)),
        ('MEM', f'{memory:.0%}', '█' * round(8 * memory) + '░' * (8 - round(8 * memory))),
        ('NET', f'{sum(network) / len(network) / 1024:.1f} KiB/s', bars(network, max(max(network), 1))),
    ]
    boxes = [(colored(f'╭{"─" * 17}╮', CYAN),
              colored(f'│ {name}', CYAN) + colored(f'{value:>12}', WHITE) + colored(' │', CYAN),
              colored(f'│ {chart:^15} │', CYAN),
              colored(f'╰{"─" * 17}╯', CYAN)) for name, value, chart in notices]
    if cols >= 63:
        for row in zip(*boxes):
            print('  '.join(row))
    else:
        for name, value, chart in notices:
            print(colored(f'{name}:', CYAN), f'{value:>11}', colored(chart, CYAN))


if __name__ == '__main__':
    main()
