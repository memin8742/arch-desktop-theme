#!/usr/bin/env python3
"""Small X11 actions and an on-demand hardware window; never polls in background."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

DATA = Path(__file__).resolve().parent


def output(args):
    return subprocess.run(args,capture_output=True,text=True,errors='replace').stdout.strip()


def down():
    import fcntl
    # Wait until physical Down is released. Holding it cannot restore and then minimize.
    # A per-user lock ignores repeats while the first press is waiting for release.
    state = Path.home()/'.local/state/arch-desktop-theme'
    state.mkdir(parents=True,exist_ok=True)
    with (state/'down.lock').open('w') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: return
        wid = output(['xdotool','getactivewindow'])
        if not wid.isdigit(): return
        prop = output(['xprop','-id',wid,'_NET_WM_STATE'])
        if '_NET_WM_STATE_MAXIMIZED_' in prop:
            subprocess.run(['wmctrl','-ir',hex(int(wid)),'-b','remove,maximized_vert,maximized_horz'],check=True)
        else: subprocess.run(['xdotool','windowminimize',wid],check=True)
        # Query the actual X keymap, no arbitrary debounce delay used as key-release evidence.
        import ctypes
        x = ctypes.CDLL('libX11.so.6')
        x.XOpenDisplay.restype=ctypes.c_void_p
        x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
        x.XQueryKeymap.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
        x.XCloseDisplay.argtypes=[ctypes.c_void_p]
        display=x.XOpenDisplay(None)
        if not display: return
        try:
            code=x.XKeysymToKeycode(display,0xff54)
            keys=ctypes.create_string_buffer(32)
            while True:
                x.XQueryKeymap(display,keys)
                if not (keys.raw[code//8] & (1 << (code%8))): break
                time.sleep(.025)
        finally: x.XCloseDisplay(display)


def compositor():
    # A separate X display or another user's compositor does not own this display.
    display = os.environ.get('DISPLAY', '').split('.', 1)[0]
    for pid in output(['pgrep', '-u', str(os.getuid()), '-x', 'picom']).split():
        try:
            environment = Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
        except OSError:
            continue
        if any(value.startswith(b'DISPLAY=') and value[8:].split(b'.', 1)[0] == os.fsencode(display)
               for value in environment):
            return
    state=Path.home()/'.local/state/arch-desktop-theme'
    state.mkdir(parents=True,exist_ok=True)
    with (state/'picom.log').open('a') as log:
        p=subprocess.Popen(['picom','--config',str(DATA/'picom.conf')],stdout=log,stderr=log)
        time.sleep(.8)
        if p.poll() is not None:
            # Restore a working compositor if the GPU/backend rejects this configuration.
            subprocess.run(['xfconf-query','-c','xfwm4','-p','/general/use_compositing','-s','true'])
            subprocess.run(['notify-send','Arch Theme','Picom açılamadı; Xfce birleştiricisi yeniden açıldı. Kontrol menüsünden günlüğü inceleyin.'])


def read(path, default=None):
    try: return Path(path).read_text().strip()
    except (OSError,ValueError): return default


def hardware(sysroot=Path('/sys')):
    rows=[]
    for device in sorted((sysroot/'class/hwmon').glob('hwmon*')):
        name=read(device/'name',device.name)
        for temp in sorted(device.glob('temp*_input')):
            raw=read(temp)
            if raw is None: continue
            try: value=float(raw)/1000
            except ValueError: continue
            label=read(temp.with_name(temp.name.replace('_input','_label')),temp.stem.replace('_input',''))
            rows.append((f'{name} / {label}',f'{value:.1f} °C'))
    for card in sorted((sysroot/'class/drm').glob('card[0-9]*')):
        if '-' in card.name: continue
        total=read(card/'device/mem_info_vram_total')
        used=read(card/'device/mem_info_vram_used')
        if total and used:
            rows.append((card.name+' VRAM',f'{int(used)/2**20:.0f} / {int(total)/2**20:.0f} MiB (sürücü bildirimi)'))
        elif (card/'device').exists(): rows.append((card.name+' VRAM','Sürücü ayrılmış VRAM verisi sunmuyor; paylaşımlı bellek olabilir.'))
    for battery in sorted((sysroot/'class/power_supply').glob('*')):
        if read(battery/'type') != 'Battery': continue
        rows.append((battery.name,' / '.join(filter(None,[read(battery/'capacity','?')+'%',read(battery/'status')]))))
        start=read(battery/'charge_control_start_threshold'); end=read(battery/'charge_control_end_threshold')
        rows.append(('Şarj eşikleri',f'{start} → {end}%' if start and end else 'Bu sürücü iki eşiği birlikte sunmuyor.'))
    return rows


def sensors():
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk, GLib
    window=Gtk.Window(title='Sistem bilgisi')
    window.set_default_size(430,400)
    window.connect('destroy',Gtk.main_quit)
    scroll=Gtk.ScrolledWindow(); window.add(scroll)
    label=Gtk.Label(xalign=0, selectable=True, margin=16)
    scroll.add(label)
    previous=None
    def update():
        nonlocal previous
        fields=read('/proc/stat','cpu 0 0 0 0').splitlines()[0].split()[1:]
        times=list(map(int,fields)); total=sum(times[:8]); idle=times[3]+times[4]
        cpu='Ölçülüyor…'
        if previous and total>previous[0]: cpu=f'{100*(1-(idle-previous[1])/(total-previous[0])):.1f}%'
        previous=(total,idle)
        mem={line.split(':')[0]:int(line.split()[1]) for line in read('/proc/meminfo','').splitlines()}
        disk=shutil.disk_usage(Path.home())
        rows=[('CPU',cpu),('RAM',f'{(mem.get("MemTotal",0)-mem.get("MemAvailable",0))/2**20:.1f} / {mem.get("MemTotal",0)/2**20:.1f} GiB'),('Disk',f'{disk.used/2**30:.0f} / {disk.total/2**30:.0f} GiB')]+hardware()
        label.set_text('\n\n'.join(k+'\n'+v for k,v in rows))
        return window.get_visible()
    window.connect('key-press-event',lambda w,e: (w.destroy() or True) if e.keyval==65307 else False)
    window.show_all(); update(); GLib.timeout_add_seconds(2,update); Gtk.main()


def notify(window):
    active=output(['xdotool','getactivewindow'])
    pid=output(['xprop','-id',active,'_NET_WM_PID']) if active.isdigit() else ''
    if window and pid.rsplit(' ',1)[-1] == window: return
    subprocess.run(['notify-send','İşlem tamamlandı','Terminaldeki uzun işlem sona erdi.'])


if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'sensors'
    if action=='down': down()
    elif action=='compositor': compositor()
    elif action=='sensors': sensors()
    elif action=='notify': notify(sys.argv[2] if len(sys.argv)>2 else '')
    else: raise SystemExit('Kullanım: arch-theme [sensors|down|compositor]')
