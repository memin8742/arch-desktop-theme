"""Optional system pieces for Arch. Desktop setup remains unprivileged."""

import datetime
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'installer'
FILES = Path('/usr/share/arch-desktop-theme')
BACKUPS = Path('/var/backups/arch-desktop-theme')
ENTRY = Path('/boot/loader/entries/arch-blue-splash.conf')
KERNEL = Path('/boot/vmlinuz-arch-blue')
INITRAMFS = Path('/boot/initramfs-arch-blue.img')
REFRESH = Path('/usr/local/sbin/arch-blue-refresh-boot')
GREETER_OPTION = Path('/etc/lightdm/lightdm.conf.d/90-arch-blue-greeter.conf')
LOGIN_OPTION = Path('/etc/lightdm/lightdm.conf.d/95-arch-blue-login.conf')
BEGIN, END = '# BEGIN ARCH BLUE', '# END ARCH BLUE'


def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True, capture_output=capture).stdout


class Backup:
    def __init__(self):
        BACKUPS.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory = Path(tempfile.mkdtemp(prefix=datetime.datetime.now().strftime('%Y%m%d-'), dir=BACKUPS))
        self.saved = {}
        self.flush()

    def flush(self):
        (self.directory / 'files.json').write_text(json.dumps(self.saved, indent=2))

    def remember(self, path):
        if str(path) in self.saved:
            return
        if path.is_symlink() or path.exists() and not path.is_file():
            raise RuntimeError(f'Normal dosya bekleniyor: {path}')
        if path.exists():
            name = str(len(self.saved))
            shutil.copy2(path, self.directory / name)
            self.saved[str(path)] = name
        else:
            self.saved[str(path)] = None
        self.flush()

    def write(self, path, content, mode=0o644):
        self.remember(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            if isinstance(content, str):
                content = content.encode()
            stream.write(content)
        temporary = Path(stream.name)
        try:
            temporary.chmod(mode)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def restore(directory):
    directory = directory.resolve()
    if directory.parent != BACKUPS or not (directory / 'files.json').is_file():
        raise RuntimeError('Geçersiz sistem yedeği.')
    saved = json.loads((directory / 'files.json').read_text())
    for filename, snapshot in reversed(list(saved.items())):
        path = Path(filename)
        if snapshot is None:
            path.unlink(missing_ok=True)
        else:
            shutil.copy2(directory / snapshot, path)
    default = directory / 'default.txt'
    if default.exists():
        run('bootctl', 'set-default', default.read_text().strip())
    print('Sistem yedeği geri yüklendi:', directory)


def append_block(original, block):
    without = re.sub(r'(?ms)^' + re.escape(BEGIN) + r'\n.*?^' + re.escape(END) + r'\n?', '', original)
    return without.rstrip('\n') + '\n\n' + BEGIN + '\n' + block.rstrip() + '\n' + END + '\n'


def configure_root(backup):
    root = pwd.getpwnam('root')
    home, shell = Path(root.pw_dir), Path(root.pw_shell).name
    if shell not in ('bash', 'zsh') or not Path('/usr/bin/zsh').is_file():
        raise RuntimeError('Root profili için sistemde Zsh ve Bash veya Zsh giriş kabuğu gerekiyor.')
    profile = FILES / 'root'
    backup.write(profile / '.zshrc', f'source "{profile}/theme.zsh"\n')
    for target, source in [('theme.zsh', 'theme.zsh'), ('system-summary.py', 'runtime/system-summary.py'),
                           ('detect.py', 'root_terminal.py')]:
        backup.write(profile / target, (SOURCE / source).read_bytes())
    detector = f'/usr/bin/python3 -I "{profile}/detect.py"'
    if shell == 'bash':
        block = f'''if [[ $- == *i* && -t 0 ]] && _arch_theme_pid=$({detector}); then
  export ARCH_THEME_WINDOW_PID="$_arch_theme_pid" ARCH_THEME_TERMINAL=1
  export ZDOTDIR="{profile}"
  exec /usr/bin/zsh -i
fi'''
        login = next((home / name for name in ('.bash_profile', '.bash_login', '.profile')
                      if (home / name).is_file()), home / '.bash_profile')
        targets = [login, home / '.bashrc']
    else:
        block = f'''if [[ -o interactive && -t 0 ]] && _arch_theme_pid=$({detector}); then
  export ARCH_THEME_WINDOW_PID="$_arch_theme_pid" ARCH_THEME_TERMINAL=1
  source "{profile}/theme.zsh"
fi'''
        targets = [home / '.zshrc']
    for target in targets:
        if target.is_symlink():
            raise RuntimeError(f'Sembolik bağlantı korunuyor: {target}')
        original = target.read_text() if target.exists() else ''
        mode = target.stat().st_mode & 0o777 if target.exists() else 0o600
        backup.write(target, append_block(original, block), mode)
    print('Arch Terminal içinde açılan root oturumlarına Zsh seçim profili eklendi.')


def boot_entry():
    if not Path('/sys/firmware/efi').is_dir():
        raise RuntimeError('EFI ile açılmış systemd-boot gerekiyor.')
    run('mountpoint', '-q', '/boot')
    run('bootctl', 'is-installed')
    candidates = []
    for candidate in ENTRY.parent.glob('*.conf'):
        if candidate == ENTRY:
            continue
        source = candidate.read_text()
        if (re.search(r'(?m)^linux[ \t]+/vmlinuz-linux[ \t]*$', source)
                and re.search(r'(?m)^initrd[ \t]+/initramfs-linux.img[ \t]*$', source)):
            candidates.append((candidate, source))
    if len(candidates) != 1:
        raise RuntimeError('Bir standart Arch systemd-boot girdisi bulunmalı.')
    candidate, source = candidates[0]
    options = re.search(r'(?m)^options[ \t]+(.+)$', source)
    if not options or re.search(r'(?:rd\.luks|cryptdevice|rd\.lvm)', options[1]):
        raise RuntimeError('Bu initramfs yapılandırması desteklenmiyor.')
    replacements = {'title': 'Arch Linux (Arch Blue)', 'linux': '/vmlinuz-arch-blue',
                    'initrd': '/initramfs-arch-blue.img', 'options': options[1] + ' quiet splash'}
    for key, value in replacements.items():
        if key == 'initrd':
            source = re.sub(r'(?m)^initrd[ \t]+/initramfs-linux.img[ \t]*$', f'initrd {value}', source, count=1)
        else:
            source = re.sub(r'(?m)^' + key + r'[ \t]+.+$', f'{key} {value}', source, count=1)
    return candidate, source


def pixel_strip(rgba):
    def chunk(name, value):
        return struct.pack('!I', len(value)) + name + value + struct.pack('!I', zlib.crc32(name + value))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 2, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\x00' + bytes(rgba)) * 2)) + chunk(b'IEND', b''))


def configure_login(backup):
    if not shutil.which('lightdm'):
        raise RuntimeError('Bu giriş teması için LightDM gerekiyor.')
    check = ("import gi, sys; gi.require_version('Gtk','3.0'); gi.require_version('LightDM','1'); "
             "from gi.repository import GdkPixbuf, Gtk, LightDM; "
             "[GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 16, 16, True) for path in sys.argv[1:]]")
    probe = (sys.executable, '-I', '-c', check, str(ROOT / 'paket/01-duvar-kagidi.png'),
             str(SOURCE / 'boot/greeter-entry.svg'))
    try:
        run(*probe, capture=True)
    except subprocess.CalledProcessError:
        run('pacman', '-Syu', '--needed', 'python-gobject', 'gtk3', 'lightdm', 'librsvg')
        run(*probe)
    greeter = FILES / 'greeter'
    # These assets must be traversable by the unprivileged LightDM account,
    # including when sudo inherits a restrictive installation umask.
    run('install', '-d', '-m', '0755', str(FILES), str(greeter), '/usr/share/backgrounds/arch-blue')
    backup.write(Path('/usr/share/backgrounds/arch-blue/wallpaper.png'),
                 (ROOT / 'paket/01-duvar-kagidi.png').read_bytes())
    backup.write(greeter / 'greeter.py', (SOURCE / 'greeter.py').read_bytes())
    backup.write(greeter / 'entry.svg', (SOURCE / 'boot/greeter-entry.svg').read_bytes())
    backup.write(Path('/usr/share/xgreeters/arch-blue.desktop'),
                 f'[Desktop Entry]\nType=Application\nName=Arch Blue\nExec=/usr/bin/python3 -I {greeter}/greeter.py\n')
    backup.write(LOGIN_OPTION, '[Seat:*]\ngreeter-session=arch-blue\n')


def configure_boot(backup, default):
    stock, contents = boot_entry()
    if not Path('/usr/bin/plymouth-set-default-theme').exists():
        run('pacman', '-Syu', '--needed', 'plymouth')
    theme = Path('/usr/share/plymouth/themes/arch-blue')
    wallpaper = (ROOT / 'paket/01-duvar-kagidi.png').read_bytes()
    backup.write(theme / 'wallpaper.png', wallpaper)
    for name in ['arch-blue.plymouth', 'arch-blue.script', 'boot-caption.png']:
        backup.write(theme / name, (SOURCE / 'boot' / name).read_bytes())
    backup.write(theme / 'track.png', pixel_strip((13, 55, 90, 255)))
    backup.write(theme / 'fill.png', pixel_strip((10, 166, 240, 255)))
    backup.remember(Path('/etc/plymouth/plymouthd.conf'))
    run('plymouth-set-default-theme', 'arch-blue')
    backup.write(REFRESH, (SOURCE / 'boot/refresh.sh').read_bytes(), 0o755)
    backup.remember(KERNEL)
    backup.remember(INITRAMFS)
    run(str(REFRESH))
    backup.write(ENTRY, contents)
    hook = """[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = linux
Target = mkinitcpio
Target = plymouth
Target = systemd

[Action]
Description = Refreshing the Arch Blue boot image
When = PostTransaction
Exec = /usr/local/sbin/arch-blue-refresh-boot
"""
    backup.write(Path('/etc/pacman.d/hooks/99-arch-blue-initramfs.hook'), hook)
    if shutil.which('lightdm'):
        configure_login(backup)
        if default:
            backup.write(GREETER_OPTION, '[Seat:*]\nautologin-user=\n')
    else:
        print('LightDM bulunamadı; yalnız açılış teması uygulandı.')
    if default:
        information = json.loads(run('bootctl', 'list', '--json=short', capture=True))
        previous = next((item['id'] for item in information if item.get('isDefault')), stock.name)
        (backup.directory / 'default.txt').write_text(previous)
        run('bootctl', 'set-default', ENTRY.name)
    print('Açılış girdisi:', ENTRY.name, '| Standart Arch girdisi:', stock.name)


def menu():
    print('1  Root terminali için Shift+ok seçimi\n2  Açılış ve LightDM teması ekle\n'
          '3  Açılış ve LightDM temasını varsayılan yap\n4  Sistem yedeğine dön\n'
          '5  Yalnız LightDM giriş ekranını uygula\n0  Dön')
    choice = input('Seçiminiz: ').strip()
    if choice == '0':
        return
    if choice == '4':
        print('Sistem yedekleri:', BACKUPS)
        name = input('Yedek klasör adı: ').strip()
        if not re.fullmatch(r'\d{8}-[a-zA-Z0-9_]+', name):
            raise RuntimeError('Geçersiz sistem yedek adı.')
        run('sudo', sys.executable, __file__, 'restore', name)
    elif choice in ('1', '2', '3', '5'):
        if choice == '3':
            print('Arch Blue varsayılan açılış olur. LightDM açılışta parola ister.')
        if input('Uygulamak için e yazın: ').strip().lower() == 'e':
            actions = {'1': 'root', '2': 'boot', '3': 'default', '5': 'login'}
            run('sudo', sys.executable, __file__, actions[choice])


def main():
    args = sys.argv[1:]
    if not args and os.geteuid() != 0:
        menu()
        return
    if os.geteuid() != 0 or not Path('/etc/arch-release').is_file():
        raise RuntimeError('Sistem bileşenleri Arch Linux ve sudo gerektirir.')
    if len(args) == 2 and args[0] == 'restore':
        restore(BACKUPS / args[1])
    elif len(args) == 1 and args[0] in ('root', 'boot', 'default', 'login'):
        backup = Backup()
        try:
            if args[0] == 'root':
                configure_root(backup)
            elif args[0] == 'login':
                configure_login(backup)
            else:
                configure_boot(backup, args[0] == 'default')
        except Exception:
            restore(backup.directory)
            raise
        print('Sistem yedeği:', backup.directory)
    else:
        raise RuntimeError('Geçersiz sistem işlemi.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
