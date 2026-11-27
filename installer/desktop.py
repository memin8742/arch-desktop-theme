"""The Arch Blue layout on the native Xfce panel and GTK file manager."""

from pathlib import Path
import re
import shutil
import subprocess

import assets

RUNTIME = Path(__file__).with_name('runtime')
PANEL = 'xfce4-panel'
WALLPAPER = 'wallpaper.png'
MENU_KEY = '<Primary><Shift>F12'
SUPER_MAP = 'Super_L=Control_L|Shift_L|F12;Super_R=Control_L|Shift_L|F12'
DEFAULT_DOCK = ['showdesktop', 'separator', 'launcher', 'launcher', 'launcher',
                'launcher', 'separator', 'directorymenu']


def xfconf(channel, prop):
    return subprocess.run(['xfconf-query', '-c', channel, '-p', prop],
                          capture_output=True, text=True, check=False).stdout.strip()


def array_items(channel, prop):
    result = xfconf(channel, prop)
    return result.splitlines()[2:] if result.startswith('Value is an array') else []


def panel_ids(prop):
    return [int(line) for line in array_items(PANEL, prop) if line.strip().isdigit()]


def xfce_launchers(tx, home, data, desktop_file):
    bin_dir = home / '.local/bin'
    for name in ['arch-network', 'arch-record']:
        tx.write(bin_dir / name, (RUNTIME / f'{name}.py').read_bytes(), 0o755)
    tx.write(bin_dir / 'arch-thunar', '''#!/bin/sh
if locale -a | grep -qi '^tr_TR\\.utf8$'; then
  export LC_MESSAGES=tr_TR.UTF-8 LANGUAGE=tr
fi
exec thunar "$@"
''', 0o755)
    tx.write(home / '.config/autostart/arch-theme-super-menu.desktop',
             desktop_file('Arch Menu Keyboard', 'xcape', 'input-keyboard', ('-t', '300', '-e', SUPER_MAP)))
    picom_start = home / '.config/autostart/picom.desktop'
    if not picom_start.exists() and Path('/etc/xdg/autostart/picom.desktop').is_file():
        tx.write(picom_start, '[Desktop Entry]\nType=Application\nName=Picom\nHidden=true\n')
    tx.write(home / '.local/share/applications/arch-record.desktop',
             desktop_file('Ekran Kaydı', bin_dir / 'arch-record', 'media-record'))
    tx.write(home / '.local/share/icons/hicolor/scalable/apps/arch-terminal-mark.svg',
             (RUNTIME / 'arch-terminal-mark.svg').read_bytes())
    for relative, contents in assets.icon_files().items():
        tx.write(home / '.local/share/icons/Arch-Blue' / relative, contents)
    tx.write(data / 'system-summary.py', (RUNTIME / 'system-summary.py').read_bytes())


def configure_desktop(tx, home):
    for prop, kind, val in [
        ('/general/title_alignment', 'string', 'left'),
        ('/general/title_font', 'string', 'Adwaita Sans 10'),
        ('/general/button_layout', 'string', 'O|HMC'),
    ]:
        tx.xf('xfwm4', prop, kind, val)
    workspace_names = array_items('xfwm4', '/general/workspace_names')
    if not workspace_names or workspace_names == [f'Workspace {n}' for n in range(1, 5)]:
        tx.xf('xfwm4', '/general/workspace_names', 'string', ['1', '2', '3', '4'], array=True)
    tx.xf('xfce4-desktop', '/desktop-icons/style', 'int', 0)
    tx.xf('thunar', '/last-icon-view-zoom-level', 'string', 'THUNAR_ZOOM_LEVEL_75_PERCENT')
    tx.xf('thunar', '/last-separator-position', 'int', 160)
    tx.xf('thunar', '/shortcuts-icon-size', 'string', 'THUNAR_ICON_SIZE_24')
    startup = '/sessions/Failsafe/Client3_Command'
    if array_items('xfce4-session', startup) == ['Thunar', '--daemon']:
        tx.xf('xfce4-session', startup, 'string',
              [str(home / '.local/bin/arch-thunar'), '--daemon'], array=True)
    menu_binding = '/commands/custom/' + MENU_KEY
    existing_menu = xfconf('xfce4-keyboard-shortcuts', menu_binding)
    if existing_menu and existing_menu != 'xfce4-popup-whiskermenu':
        raise RuntimeError(f'{MENU_KEY} kısayolu başka bir komut için kullanılıyor.')
    tx.xf('xfce4-keyboard-shortcuts', menu_binding, 'string', 'xfce4-popup-whiskermenu')

    file = home / '.config/gtk-3.0/bookmarks'
    before = file.read_text() if file.exists() else ''
    bookmarks = []
    if shutil.which('xdg-user-dir'):
        for kind, label in [('DOCUMENTS', 'Belgeler'), ('DOWNLOAD', 'İndirilenler'),
                            ('PICTURES', 'Resimler'), ('MUSIC', 'Müzik'), ('VIDEOS', 'Videolar'),
                            ('PROJECTS', 'Projeler')]:
            value = subprocess.run(['xdg-user-dir', kind], capture_output=True, text=True,
                                   check=False).stdout.strip()
            directory = Path(value)
            if directory.is_absolute() and directory.is_dir() and directory != home:
                bookmarks.append(f'{directory.as_uri()} {label}')
    bookmarks.append('trash:/// Çöp Kutusu')
    used = {line.partition(' ')[0] for line in before.splitlines()}
    extra = [line for line in bookmarks if line.partition(' ')[0] not in used]
    if extra:
        tx.write(file, '\n'.join([*before.splitlines(), *extra]) + '\n')


def configure_panel(tx, home, desktop_file):
    panels = panel_ids('/panels')
    if not panels:
        raise RuntimeError('Xfce paneli bulunamadı. Varsayılan paneli açıp yeniden deneyin.')
    active = next((p for p in panels if xfconf(PANEL, f'/panels/panel-{p}/position').startswith('p=6;')), panels[0])
    base = f'/panels/panel-{active}'
    plugins = panel_ids(base + '/plugin-ids')
    channel = subprocess.check_output(['xfconf-query', '-c', PANEL, '-l'], text=True)
    reserved = {int(n) for n in re.findall(r'^/plugins/plugin-(\d+)(?:/|$)', channel, re.M)}
    names = {i: xfconf(PANEL, f'/plugins/plugin-{i}') for i in plugins}
    used = set()
    launchers = home / '.config/xfce4/panel'

    def plugin(name, role):
        matching = [n for n in plugins if names[n] == name and n not in used]
        number = next((n for n in matching if xfconf(PANEL, f'/plugins/plugin-{n}/arch-blue-role') == role), None)
        if number is None and name in ('whiskermenu', 'pager', 'tasklist', 'systray',
                                       'notification-plugin', 'pulseaudio', 'clock'):
            number = next(iter(matching), None)
        if number is None:
            number = max(reserved, default=0) + 1
            reserved.add(number)
            tx.xf(PANEL, f'/plugins/plugin-{number}', 'string', name)
        used.add(number)
        path = f'/plugins/plugin-{number}'
        if xfconf(PANEL, path + '/arch-blue-role') != role:
            tx.xf(PANEL, path + '/arch-blue-role', 'string', role)
        return number, path

    def separator(role, expand=False):
        number, path = plugin('separator', role)
        tx.xf(PANEL, path + '/style', 'uint', 0)
        tx.xf(PANEL, path + '/expand', 'bool', expand)
        return number

    def launcher(role, name, icon, executable, arguments=()):
        definition = desktop_file(name, executable, icon, arguments)
        # Migrate launchers from the earlier hand-installed desktop without duplicating them.
        for candidate in plugins:
            path = f'/plugins/plugin-{candidate}'
            if names[candidate] != 'launcher' or xfconf(PANEL, path + '/arch-blue-role'):
                continue
            previous = launchers / f'launcher-{candidate}' / 'arch-theme.desktop'
            if previous.is_file() and f'Name={name}\n' in previous.read_text(encoding='utf-8'):
                tx.xf(PANEL, path + '/arch-blue-role', 'string', role)
                break
        number, path = plugin('launcher', role)
        item = 'arch-theme.desktop'
        tx.write(launchers / f'launcher-{number}' / item, definition)
        tx.xf(PANEL, path + '/items', 'string', [item], array=True)
        return number

    bin_dir = home / '.local/bin'
    menu, path = plugin('whiskermenu', 'menu')
    tx.xf(PANEL, path + '/button-title', 'string', 'Arch Linux')
    menu_icon = '/usr/share/pixmaps/archlinux-logo.svg'
    if not Path(menu_icon).is_file():
        menu_icon = 'distributor-logo-archlinux'
    tx.xf(PANEL, path + '/button-icon', 'string', menu_icon)
    for name in ['show-button-title', 'show-button-icon']:
        tx.xf(PANEL, path + '/' + name, 'bool', True)
    pager, path = plugin('pager', 'workspaces')
    tx.xf(PANEL, path + '/rows', 'uint', 1)
    tx.xf(PANEL, path + '/miniature-view', 'bool', False)
    task, path = plugin('tasklist', 'running')
    for key in ['show-labels', 'show-handle']:
        tx.xf(PANEL, path + '/' + key, 'bool', False)
    tx.xf(PANEL, path + '/grouping', 'uint', 1)
    clock, path = plugin('clock', 'clock')
    tx.xf(PANEL, path + '/mode', 'uint', 2)
    tx.xf(PANEL, path + '/digital-format', 'string', '%a, %e %b  %H:%M')

    ids = [separator('left-edge'), separator('left-edge-2'), separator('left-edge-3'),
           menu, separator('menu-separator'), pager,
           launcher('terminal', 'Terminal', 'arch-terminal-mark', bin_dir / 'arch-terminal'),
           launcher('files', 'Dosyalar', 'folder', bin_dir / 'arch-thunar')]
    for role, label, candidates in [('browser', 'Tarayıcı', ('firefox', 'chromium', 'brave', 'google-chrome')),
                                    ('editor', 'VS Code', ('code', 'codium'))]:
        executable = next((shutil.which(name) for name in candidates if shutil.which(name)), None)
        if executable:
            ids.append(launcher(role, label, Path(executable).name, executable))
    ids += [separator('left-space', True), task, separator('right-space', True),
            launcher('sensors', 'Sistem bilgisi', 'utilities-system-monitor', bin_dir / 'arch-theme', ('sensors',)),
            launcher('clipboard', 'Pano geçmişi', 'edit-paste', 'copyq', ('toggle',)),
            launcher('record', 'Ekran Kaydı', 'media-record', bin_dir / 'arch-record'),
            plugin('notification-plugin', 'notifications')[0], plugin('pulseaudio', 'sound')[0]]
    if shutil.which('nmcli'):
        ids.append(launcher('network', 'Ağ bağlantıları', 'network-wired', bin_dir / 'arch-network'))
    ids.append(plugin('systray', 'tray')[0])
    default_plugins = {'applicationsmenu', 'separator', 'actions', 'screenshooter'}
    for i in plugins:
        if i not in used and names[i] not in default_plugins:
            ids.append(i)
    ids += [clock, separator('right-edge-3'), separator('right-edge-2'), separator('right-edge')]
    for key, kind, value in [('position', 'string', 'p=6;x=0;y=0'), ('position-locked', 'bool', True),
                             ('size', 'uint', 38), ('icon-size', 'uint', 22), ('length', 'uint', 100),
                             ('mode', 'uint', 0), ('background-style', 'uint', 0)]:
        tx.xf(PANEL, base + '/' + key, kind, value)
    tx.xf(PANEL, base + '/plugin-ids', 'int', ids, array=True)
    kept = []
    for other in panels:
        other_base = f'/panels/panel-{other}'
        types = [xfconf(PANEL, f'/plugins/plugin-{n}') for n in panel_ids(other_base + '/plugin-ids')]
        if other == active or types != DEFAULT_DOCK:
            kept.append(other)
    if kept != panels:
        tx.xf(PANEL, '/panels', 'int', kept, array=True)

    return {role: number for number in used
            if (role := xfconf(PANEL, f'/plugins/plugin-{number}/arch-blue-role'))}
