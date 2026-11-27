#!/usr/bin/env python3
"""Reversible, user-level Arch/Xfce installer. No shell=True, no sudo config writes."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

import assets

ROOT = Path(__file__).resolve().parents[1]
NAME = 'arch-desktop-theme'
PACKAGES = ['python-gobject', 'vte3', 'zsh', 'zsh-syntax-highlighting',
            'zsh-autosuggestions', 'ttf-fira-code', 'picom', 'xclip', 'wmctrl',
            'xorg-xprop', 'xdotool', 'libnotify', 'xfce4-screensaver',
            'xfce4-screenshooter', 'xfce4-whiskermenu-plugin', 'xfce4-pulseaudio-plugin',
            'xfce4-power-manager', 'copyq', 'papirus-icon-theme', 'fastfetch', 'grc', 'tree']
BEGIN, END = '# BEGIN ARCH-DESKTOP-THEME', '# END ARCH-DESKTOP-THEME'


def run(args, check=True):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and p.returncode:
        raise RuntimeError('İşlem başarısız: ' + str(args[0]) + '\n' + p.stderr.strip())
    return p


def paths(home=None):
    home = Path(home or Path.home()).absolute()
    return home, home / '.local/share' / NAME, home / '.local/state' / NAME


def merge_block(text, block):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError('Yönetilen ayar bloğu bozuk; dosya korunarak işlem durduruldu.')
    if BEGIN in text:
        start, finish = text.index(BEGIN), text.index(END)+len(END)
        text = text[:start] + text[finish:]
    return text.rstrip() + '\n\n' + BEGIN + '\n' + block.rstrip() + '\n' + END + '\n'


class Transaction:
    def __init__(self, home, backup=None):
        self.home, _, state = paths(home)
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
        self.backup = Path(backup) if backup else state / 'backups' / stamp
        self.backup.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.record = {'home': str(self.home), 'files': {}, 'settings': [], 'status': 'started'}
        self.save()

    def safe(self, target):
        target = Path(target)
        if '..' in target.parts:
            raise ValueError('Üst dizine çıkış reddedildi: ' + str(target))
        target = target.absolute()
        if not target.is_relative_to(self.home) or target == self.home:
            raise ValueError('Kullanıcı dizini dışına yazma reddedildi: ' + str(target))
        current = target
        while current != self.home:
            if current.is_symlink():
                raise ValueError('Sembolik bağlantı korunuyor; önce elle inceleyin: ' + str(current))
            current = current.parent
        return target

    def save(self):
        atomic(self.backup / 'backup.json', json.dumps(self.record, ensure_ascii=False, indent=2).encode())

    def write(self, target, data, mode=0o644):
        target = self.safe(target)
        key = target.relative_to(self.home).as_posix()
        if key not in self.record['files']:
            info = {'existed': target.exists(), 'mode': target.stat().st_mode & 0o777 if target.exists() else mode}
            if target.exists():
                if not target.is_file(): raise ValueError('Normal dosya değil: ' + str(target))
                original = self.backup / 'files' / key
                original.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target, original)
            self.record['files'][key] = info
            self.save()  # Journal before mutation, so interrupted installs can be restored.
        data = data.encode('utf-8') if isinstance(data, str) else data
        atomic(target, data, mode)
        self.record['files'][key]['installed_sha256'] = hashlib.sha256(data).hexdigest()
        self.save()

    def xf(self, channel, prop, kind, value, array=False):
        old = run(['xfconf-query', '-c', channel, '-p', prop], False)
        present = old.returncode == 0
        # Preserve actual type from xfconf XML where possible; callers mutate only known typed keys.
        self.record['settings'].append({'channel': channel, 'property': prop,
            'kind': kind, 'array': array, 'existed': present, 'old': old.stdout.rstrip('\n')})
        self.save()
        args = ['xfconf-query', '-c', channel, '-p', prop]
        if not present: args += ['-n']
        if array:
            args += ['-a']
            for item in value: args += ['-t', kind, '-s', str(item)]
        else:
            if not present: args += ['-t', kind]
            args += ['-s', str(value).lower() if isinstance(value, bool) else str(value)]
        run(args)

    def finish(self):
        self.record['status'] = 'applied'
        self.save()


def atomic(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.arch-theme-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def restore(backup, home=None, settings=True):
    home, _, state = paths(home)
    backup = Path(backup).resolve()
    if not backup.is_relative_to((state / 'backups').resolve()): raise ValueError('Geçersiz yedek konumu.')
    record = json.loads((backup / 'backup.json').read_text(encoding='utf-8'))
    if record['home'] != str(home): raise ValueError('Bu yedek başka kullanıcıya ait.')
    # File paths are checked independently of the manifest.
    guard = object.__new__(Transaction)
    guard.home = home
    conflicts = []
    for key, info in reversed(list(record['files'].items())):
        target = guard.safe(home / key)
        if target.exists() and info.get('installed_sha256'):
            if hashlib.sha256(target.read_bytes()).hexdigest() != info['installed_sha256']:
                conflicts.append(key)
                continue  # Do not erase edits made after installation.
        if info['existed']:
            source = backup / 'files' / key
            if not source.resolve().is_relative_to((backup / 'files').resolve()): raise ValueError('Geçersiz yedek yolu.')
            atomic(target, source.read_bytes(), info['mode'])
        elif target.exists(): target.unlink()
    if settings:
        for item in reversed(record['settings']):
            args = ['xfconf-query', '-c', item['channel'], '-p', item['property']]
            if not item['existed']: run(args+['-r'], False)
            elif not item['array']: run(args+['-s', item['old']], False)
            else:
                # xfconf-query array output starts with a heading and blank line.
                values = item['old'].splitlines()[2:]
                cmd = args + ['-a']
                for value in values: cmd += ['-t', item['kind'], '-s', value]
                run(cmd, False)
    print('Yedek geri yüklendi: ' + str(backup))
    if conflicts: print('Sonradan değiştiği için korunan dosyalar: ' + ', '.join(conflicts))
    return conflicts


def preflight():
    if sys.platform != 'linux' or not Path('/etc/arch-release').is_file():
        raise RuntimeError('Arch Linux gerekiyor. Bu bilgisayarda kurulum yapılmadı.')
    if os.geteuid() == 0: raise RuntimeError('Kendi kullanıcınızla çalıştırın; sudo kullanmayın.')
    if os.environ.get('XDG_SESSION_TYPE') == 'wayland' or not os.environ.get('DISPLAY'):
        raise RuntimeError('Xfce X11 oturumunda çalıştırın. Wayland desteklenmiyor.')
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    if 'xfce' not in desktop: raise RuntimeError('Önce giriş ekranından Xfce oturumunu açın.')
    for cmd in ['xfconf-query', 'xfce4-panel', 'xfwm4', 'thunar', 'xfdesktop']:
        if not shutil.which(cmd): raise RuntimeError('Xfce bileşeni eksik: ' + cmd)
    # Never take over an independently configured compositor.
    if run(['pgrep', '-x', 'picom'], False).returncode == 0:
        _, data, _ = paths()
        if not (data / 'installed.json').exists():
            raise RuntimeError('Mevcut Picom çalışıyor. Ayarları birleştirmek için önce mevcut Picom başlangıcını inceleyin; otomatik ezilmedi.')


def missing_packages():
    return [p for p in PACKAGES if run(['pacman', '-Q', p], False).returncode != 0]


def desktop_file(name, command, icon, arguments=()):
    # Desktop Entry quoting differs from shell quoting. argv is never evaluated by a shell.
    def quote(value):
        value = str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
        return '"' + value + '"'
    command = ' '.join(quote(a) for a in [command, *arguments])
    return f'[Desktop Entry]\nType=Application\nName={name}\nExec={command}\nIcon={icon}\nTerminal=false\nCategories=System;\n'


def install(home=None):
    preflight()
    missing = missing_packages()
    if missing:
        print('Gereken paketler: ' + ', '.join(missing))
        print('Arch paket uyumu için sistem de güncellenir. Parolayı yalnız sudo sorar.')
        if input('Paketleri kurmak için e yazın: ').strip().lower() != 'e': return
        subprocess.run(['sudo', 'pacman', '-Syu', '--needed', *missing], check=True)
    home, data, state = paths(home)
    tx = Transaction(home)
    print('Geri dönüş yedeği: ' + str(tx.backup))
    try:
        config = json.loads((ROOT / 'paket/04-ayarlar-ve-ozellikler.json').read_text(encoding='utf-8-sig'))
        for name in ['terminal.py', 'helper.py', 'theme.zsh', 'assets.py', 'install.py']:
            tx.write(data / name, (ROOT / 'installer' / name).read_bytes())
        tx.write(data / 'design.json', json.dumps(config, ensure_ascii=False))
        tx.write(data / 'wallpaper.png', (ROOT / 'paket/01-duvar-kagidi.png').read_bytes())
        tx.write(data / 'terminal.css', assets.TERMINAL_CSS)
        tx.write(data / 'picom.conf', assets.PICOM)
        width = 1920
        dimensions = run(['xdotool', 'getdisplaygeometry'], False).stdout.split()
        if len(dimensions) == 2: width = int(dimensions[0])
        tx.write(data / 'panel.svg', assets.panel_svg(width))
        tx.write(data / 'theme.css', assets.css(data / 'panel.svg'))
        gtk = home / '.config/gtk-3.0/gtk.css'
        existing = gtk.read_text(encoding='utf-8') if gtk.exists() else ''
        # CSS uses comment markers; preserve unrelated user CSS.
        begin, end = '/* BEGIN ARCH-DESKTOP-THEME */', '/* END ARCH-DESKTOP-THEME */'
        if begin in existing:
            a, b = existing.index(begin), existing.index(end)+len(end)
            existing = existing[:a] + existing[b:]
        tx.write(gtk, f'{begin}\n@import url("{(data / "theme.css").as_uri()}");\n{end}\n'+existing)
        for name, content in assets.xfwm_files().items():
            tx.write(home / '.themes/Arch-Blue/xfwm4' / name, content)
        zsh = home / '.zshrc'
        existing = zsh.read_text(encoding='utf-8') if zsh.exists() else ''
        # No absolute username path in shell source, no global login shell change.
        tx.write(zsh, merge_block(existing, '[[ -n $ARCH_THEME_TERMINAL ]] && source "$HOME/.local/share/arch-desktop-theme/theme.zsh"'))
        launcher = home / '.local/bin/arch-terminal'
        # Script path handles whitespace/unicode home directories without shell substitution.
        tx.write(launcher, '#!/usr/bin/env python3\nimport os, pathlib, sys\nos.execv(sys.executable, [sys.executable, str(pathlib.Path.home()/".local/share/arch-desktop-theme/terminal.py"), *sys.argv[1:]])\n', 0o755)
        helper = home / '.local/bin/arch-theme'
        tx.write(helper, '#!/usr/bin/env python3\nimport os, pathlib, sys\nos.execv(sys.executable, [sys.executable, str(pathlib.Path.home()/".local/share/arch-desktop-theme/helper.py"), *sys.argv[1:]])\n', 0o755)
        tx.write(home / '.local/share/applications/arch-terminal.desktop', desktop_file('Arch Terminal', launcher, 'utilities-terminal'))
        tx.write(home / '.local/share/applications/arch-theme-sensors.desktop', desktop_file('Sistem bilgisi — Arch Theme', helper, 'utilities-system-monitor', ['sensors']))
        tx.write(home / '.config/autostart/arch-theme-compositor.desktop', desktop_file('Arch Theme ışık', helper, 'preferences-desktop-theme', ['compositor']))
        # Native clipboard manager supports text and image history; never export its private data.
        tx.write(home / '.config/autostart/arch-theme-clipboard.desktop', '[Desktop Entry]\nType=Application\nName=Pano geçmişi\nExec=copyq\nOnlyShowIn=XFCE;\n')
        for prop, kind, value in [('/general/theme','string','Arch-Blue'), ('/general/use_compositing','bool',False), ('/general/workspace_count','int',4)]: tx.xf('xfwm4',prop,kind,value)
        tx.xf('xsettings','/Net/ThemeName','string','Adwaita-dark')
        tx.xf('xsettings','/Net/IconThemeName','string','Papirus-Dark')
        tx.xf('thunar','/misc-use-csd','bool',False)
        desktop_props = run(['xfconf-query','-c','xfce4-desktop','-l']).stdout.splitlines()
        wallpapers = [p for p in desktop_props if p.endswith('/last-image')]
        if not wallpapers: raise RuntimeError('Xfdesktop duvar kâğıdı alanı bulunamadı. Masaüstü ayarlarını bir kez açıp yeniden deneyin.')
        for prop in wallpapers:
            tx.xf('xfce4-desktop',prop,'string',str(data/'wallpaper.png'))
            tx.xf('xfce4-desktop',prop.rsplit('/',1)[0]+'/image-style','int',5)
        configure_panel(tx, home)
        shortcuts = {'<Super>t':str(launcher), '<Super>e':'thunar', '<Super>l':'xfce4-screensaver-command --lock',
                     '<Super>v':'copyq toggle', 'Print':'xfce4-screenshooter', '<Super>Down':str(helper)+' down'}
        # xfconf stores commands as strings; quote paths for GLib shell parsing.
        import shlex
        shortcuts['<Super>t'] = shlex.quote(str(launcher))
        shortcuts['<Super>Down'] = shlex.quote(str(helper))+' down'
        for key, command in shortcuts.items(): tx.xf('xfce4-keyboard-shortcuts','/commands/custom/'+key,'string',command)
        wm = {'<Super>Up':'maximize_window_key', '<Super>Left':'tile_left_key', '<Super>Right':'tile_right_key'}
        wm.update({f'<Super>{n}':f'workspace_{n}_key' for n in range(1,5)})
        for key, action in wm.items(): tx.xf('xfce4-keyboard-shortcuts','/xfwm4/custom/'+key,'string',action)
        # Remove a conflicting Super+Down WM binding, after journaling its current value.
        prop = '/xfwm4/custom/<Super>Down'
        if run(['xfconf-query','-c','xfce4-keyboard-shortcuts','-p',prop],False).returncode == 0:
            tx.xf('xfce4-keyboard-shortcuts',prop,'string','')
        report = feature_report()
        tx.write(data / 'installed.json', json.dumps({'version':(ROOT/'VERSION').read_text().strip() if (ROOT/'VERSION').exists() else '1.1.0', 'backup':str(tx.backup),'features':report},ensure_ascii=False,indent=2))
        tx.finish()
    except BaseException:
        print('Kurulum tamamlanamadı; bu işlemde değişen ayarlar geri yükleniyor.')
        restore(tx.backup, home)
        raise
    subprocess.Popen([str(helper),'compositor'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.Popen(['copyq'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('\nTema uygulandı. Panel ve uygulamaların tüm ayarları alması için oturumu kapatıp tekrar açın.')
    print('Açık işleriniz otomatik kapatılmaz. Yeni terminal: Başlat+T. Kontrol: bash kur.sh --check')
    print('\nBu sürümde otomatik uygulanmayanlar:')
    for row in report:
        if row['status'] != 'configured': print(' • '+row['feature']+': '+row['detail'])


def configure_panel(tx, home):
    # Preserve every existing panel/plugin; use the first panel rather than replace its XML.
    panels = run(['xfconf-query','-c','xfce4-panel','-p','/panels']).stdout
    ids = [int(x.strip()) for x in panels.splitlines() if x.strip().isdigit()]
    if not ids: raise RuntimeError('Xfce paneli bulunamadı; panel ayarları korunarak durduruldu.')
    pid = ids[0]
    base = f'/panels/panel-{pid}'
    for key, kind, val in [('position','string','p=6;x=0;y=0'), ('position-locked','bool',True), ('size','uint',38), ('length','uint',100), ('mode','uint',0), ('background-style','uint',0)]: tx.xf('xfce4-panel',base+'/'+key,kind,val)
    props = run(['xfconf-query','-c','xfce4-panel','-l']).stdout.splitlines()
    # Existing plugins (sound, power, tray, notifications, clipboard) are not deleted.
    for prop in props:
        if prop.startswith('/plugins/plugin-') and prop.count('/') == 2:
            plugin = run(['xfconf-query','-c','xfce4-panel','-p',prop]).stdout.strip()
            if plugin == 'tasklist':
                tx.xf('xfce4-panel',prop+'/show-labels','bool',False)
                tx.xf('xfce4-panel',prop+'/show-handle','bool',False)
            if plugin == 'pager': tx.xf('xfce4-panel',prop+'/rows','uint',1)


def feature_report():
    return [
        {'feature':'Masaüstü, Xfwm çerçevesi, üst panel, Thunar koyu tema','status':'configured','detail':'Yerel Xfce/GTK ayarları; birebir görsel kabulü hedef ekranda yapılmalı.'},
        {'feature':'Terminal, Zsh renkleri, iki satır istem, bölmeler, arama, kopyalama','status':'configured','detail':'Gerçek VTE/PTTY; zemin alfa 0.8, yazı opak. Shift seçimi yalnız düzenlenen Zsh komut satırındadır.'},
        {'feature':'Metin ve görsel pano geçmişi','status':'configured','detail':'CopyQ, Başlat+V; geçmiş dışa aktarılmaz.'},
        {'feature':'Thunar %80 yalnız zemin saydamlığı','status':'configured','detail':'Thunar 4.20+ RGBA görseli ve GTK zemin alfa; yazı ve simgelerde genel pencere opaklığı yok. Birleştirici açıkken yeni açılan pencerelerde uygulanır.'},
        {'feature':'Açılış ve giriş ekranının birebir tasarımı','status':'pending','detail':'Önyükleyici/initramfs/giriş yöneticisi otomatik değiştirilmez. 05/06 referansları korunur.'},
        {'feature':'Kilit ekranı','status':'partial','detail':'Başlat+L gerçek Xfce Screensaver kilidini açar; görsel 06 birebir uygulanmış değildir.'},
        {'feature':'Batarya Ev %55/%80 ve Seyahat %100','status':'pending','detail':'Donanım/power-manager incelenmeden şarj eşikleri değiştirilmez. Sistem kutusunda gerçek destek okunur.'},
        {'feature':'Panelde olmayan özel kutular ve ekran kaydı','status':'partial','detail':'Var olan panel öğeleri korunur. Sistem bilgisi arch-theme sensors ile açılır; kayıt aracı otomatik kurulmaz.'},
        {'feature':'Terminal içi CPU/MEM/NET kartları','status':'pending','detail':'Gerçek fastfetch kuruludur; referanstaki grafik kartları terminale otomatik eklenmez.'},
        {'feature':'Tek başına Başlat ile menü','status':'pending','detail':'Super+harf kısayollarını bozmamak için tek tuş bağlaması eklenmedi. Mevcut uygulama menüsü korunur.'},
        {'feature':'Pasif çerçeve ve ışık','status':'partial','detail':'Kontur yaklaşık %10 soluk; Picom gölgesinin aktif/pasif alfa farkı bu sürümde yok. İçerik soldurulmaz.'},
    ]


def verify():
    _, data, _ = paths()
    if not (data/'installed.json').exists(): raise RuntimeError('Bu kullanıcıda kurulum kaydı bulunamadı.')
    info = json.loads((data/'installed.json').read_text())
    print('Kurulu sürüm: '+info['version']+'\nYedek: '+info['backup'])
    for row in info['features']: print(row['status']+' — '+row['feature']+': '+row['detail'])
    missing = missing_packages()
    if missing: raise RuntimeError('Eksik paketler: '+', '.join(missing))
    result = run([sys.executable,str(data/'terminal.py'),'--self-check'],False)
    print(result.stdout)
    if result.returncode: raise RuntimeError('Terminal bileşen denetimi başarısız: '+result.stderr)
    print('Bileşen denetimi tamamlandı. Gerçek klavye/görsel kabul testi ayrıca yapılmalıdır.')


def export_theme():
    home, data, _ = paths()
    if not (data/'installed.json').exists(): raise RuntimeError('Önce tema kurulmalı.')
    destination = home / ('arch-theme-ayarlar-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.tar.gz')
    # Strict allowlist, no ~/.config dump, command history, clipboard, SSH or personal files.
    allowed = ['theme.css','terminal.css','picom.conf','panel.svg','theme.zsh','design.json','wallpaper.png']
    with tarfile.open(destination,'w:gz') as archive:
        for name in allowed:
            p = data/name
            if p.is_file() and not p.is_symlink(): archive.add(p,arcname=name,recursive=False)
    print('Yalnız tema ayarları dışa aktarıldı: '+str(destination))


def main():
    parser = argparse.ArgumentParser(description='Arch Theme / Xfce kurulum aracı')
    parser.add_argument('--plan',action='store_true')
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    if args.plan:
        print('Hedef: Arch Linux, Xfce, X11. Önce yedek; duvar kâğıdı, Xfwm/GTK, üst panel, özel VTE terminal, Zsh, kısayollar ve CopyQ.')
        for r in feature_report(): print(r['status']+' — '+r['feature']+': '+r['detail'])
        print('Paketler: '+', '.join(PACKAGES)); return
    preflight()
    if args.check: verify(); return
    while True:
        print('\nArch Theme — Xfce\n1  Kur / güncelle\n2  Kontrol et\n3  Yedeğe dön\n4  Tema ayarlarını dışa aktar\n0  Çık')
        choice = input('Seçiminiz: ').strip()
        if choice == '0': return
        if choice == '1':
            print('Mevcut ayarlar yedeklenir. Uygulanabilenler ve eksikler önce gösteriliyor:')
            for r in feature_report(): print(' • '+r['feature']+' — '+r['detail'])
            if input('\nBu kapsamla kurmak için e yazın: ').strip().lower() == 'e': install()
        elif choice == '2': verify()
        elif choice == '3':
            _, _, state = paths()
            backups = sorted((state/'backups').glob('*/backup.json'),reverse=True)
            for i,p in enumerate(backups): print(str(i+1)+'  '+p.parent.name)
            value = input('Yedek numarası (boş: vazgeç): ').strip()
            if value.isdigit() and 1 <= int(value) <= len(backups):
                restore(backups[int(value)-1].parent)
                print('Oturumu kapatıp tekrar açın. Kurulan Arch paketleri kaldırılmaz.')
        elif choice == '4': export_theme()


if __name__ == '__main__':
    try: main()
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print('\nHata: '+str(error),file=sys.stderr); sys.exit(1)
    except (KeyboardInterrupt, EOFError): print('\nİptal edildi.'); sys.exit(130)
