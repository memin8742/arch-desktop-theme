"""Run only in disposable Arch CI/Xvfb as a normal user, never on an owner's desktop."""
import importlib.util
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

import helper
import install

if os.environ.get('GITHUB_ACTIONS') != 'true':
    raise SystemExit('Bu test yalnız geçici GitHub Actions ortamında çalıştırılır.')

def call(*args): return subprocess.check_output(args,text=True).strip()
def xf(channel,prop,kind,value): call('xfconf-query','-c',channel,'-p',prop,'-n','-t',kind,'-s',str(value))

children=[]
logs=[]
home=Path.home()
try:
    call('dbus-update-activation-environment','DISPLAY','XAUTHORITY','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE')
    xf('xfce4-panel','/configver','int',2)
    # A known, minimal panel fixture, not a user's existing live panel.
    call('xfconf-query','-c','xfce4-panel','-p','/panels','-n','-a','-t','int','-s','1')
    call('xfconf-query','-c','xfce4-panel','-p','/panels/panel-1/plugin-ids','-n','-a','-t','int','-s','1')
    xf('xfce4-panel','/plugins/plugin-1','string','tasklist')
    xf('xfce4-panel','/panels/panel-1/position','string','p=6;x=0;y=0')
    xf('xfce4-desktop','/backdrop/screen0/monitor0/workspace0/last-image','string','/tmp/original.png')
    for command in [['xfsettingsd','--no-daemon'],['xfwm4','--compositor=off'],['xfce4-panel'],['xfdesktop']]:
        log=tempfile.TemporaryFile(); logs.append((command,log))
        children.append(subprocess.Popen(command,stdout=log,stderr=log))
    time.sleep(2)
    assert children[1].poll() is None, 'Xfwm exited before testing'
    assert 'xfwm4' in call('wmctrl','-m').lower(), 'Real Xfwm is required'
    (home/'.zshrc').write_text('export ARCH_PRESERVED=yes\n')
    install.install()
    # Model the documented logout/login: existing GTK processes read CSS at startup.
    subprocess.run(['thunar','--quit'],check=False)
    subprocess.run(['xfce4-panel','--restart'],check=False)
    _,data,state=install.paths()
    assert 'ARCH_PRESERVED=yes' in (home/'.zshrc').read_text()
    assert call('xfconf-query','-c','xfwm4','-p','/general/theme') == 'Arch-Blue'
    assert call('xfconf-query','-c','xfce4-keyboard-shortcuts','-p','/commands/custom/<Super>Up').endswith(' up')
    assert call('xfconf-query','-c','xfce4-panel','-p','/plugins/plugin-1/show-labels') == 'false'
    subprocess.run([sys.executable,str(data/'terminal.py'),'--self-check'],check=True)
    spec=importlib.util.spec_from_file_location('arch_terminal',data/'terminal.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    Gtk,GLib=module.Gtk,module.GLib
    app=module.Application(); app.register(None)
    app.activate()
    window=app.get_windows()[0]
    def spin(predicate,timeout=8):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            while Gtk.events_pending(): Gtk.main_iteration_do(False)
            if predicate(): return
            time.sleep(.02)
        raise AssertionError('Timed out: '+str(predicate))
    first=window.current
    spin(lambda: bool(first.shell_pid))
    target=home/'same directory'; target.mkdir()
    first.feed_child(('cd "'+str(target)+'"\n').encode())
    spin(lambda: module.cwd_for(first)==str(target))
    window.new_tab(); second=window.current
    spin(lambda: bool(second.shell_pid))
    spin(lambda: module.cwd_for(second)==str(target))
    assert window.book.get_current_page()==1, 'New tab did not become active'
    window.split(Gtk.Orientation.HORIZONTAL)
    third=window.current
    spin(lambda: bool(third.shell_pid))
    spin(lambda: bool(window.frame_separators.windows))
    assert len(window.terms)==3
    assert first.shell_pid!=second.shell_pid!=third.shell_pid
    marker=home/'pty-command-worked'
    third.feed_child(('printf okay > "'+str(marker)+'"\n').encode())
    spin(marker.exists)
    assert marker.read_text()=='okay'
    # Ctrl+C without selection must leave a foreground job running; shifted copy sends SIGINT.
    interrupted=home/'interrupted'
    ready=home/'interrupt-ready'
    script=home/'interrupt.py'
    script.write_text('import signal,time,pathlib\nsignal.signal(signal.SIGINT,lambda *a:(pathlib.Path('+repr(str(interrupted))+').write_text("yes"),exit(0)))\npathlib.Path('+repr(str(ready))+').touch()\ntime.sleep(30)\n')
    third.feed_child(('python3 "'+str(script)+'"\n').encode())
    spin(lambda: not window.at_prompt(third))
    spin(ready.exists)
    window.copy(third)
    assert not interrupted.exists()
    third.feed_child(b'\x03')
    spin(interrupted.exists)
    spin(lambda: window.at_prompt(third))
    pasted=home/'paste-marker'
    module.Gtk.Clipboard.get(module.Gdk.SELECTION_CLIPBOARD).set_text('printf pasted > "'+str(pasted)+'"',-1)
    third.paste_clipboard()
    end=time.monotonic()+.3
    while time.monotonic()<end:
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        time.sleep(.01)
    assert not pasted.exists(), 'Paste added an unsolicited Enter'
    third.feed_child(b'\r')
    spin(pasted.exists)
    window.entry.set_text('printf pasted')
    window.search_changed()
    assert third.search_find_previous(), 'Output search did not find real scrollback'
    window.hide_search()
    # Real ZLE syntax, prompt colour, buffer selection and clipboard integration.
    third.feed_child(b'printf abcde')
    time.sleep(.1)
    third.feed_child(b'\x1b[1;2D\x1b[1;2D\x1b[99;5u')
    def copied():
        # GTK still owns the earlier paste until ZLE's xclip takes over.
        # Never synchronously wait for our own GTK clipboard while its loop is paused.
        try:
            return subprocess.run(['xclip','-selection','clipboard','-o'],capture_output=True,timeout=.15).stdout==b'de'
        except subprocess.TimeoutExpired: return False
    spin(copied)
    third.feed_child(b'\x03')
    window.split(Gtk.Orientation.VERTICAL)
    fourth=window.current
    spin(lambda: window.at_prompt(fourth))
    second.grab_focus()
    spin(lambda: window.current == second)
    call('xdotool','key','ctrl+shift+b')
    spin(lambda: fourth not in window.terms)
    assert window.current == second and third in window.terms and first in window.terms
    call('xdotool','key','ctrl+shift+b')
    spin(lambda: third not in window.terms)
    spin(lambda: not window.frame_separators.windows)
    call('xdotool','key','ctrl+shift+b')  # One pane in this tab: do nothing.
    spin(lambda: window.current == second)
    assert len(window.terms)==2 and window.book.get_n_pages()==2
    # Native Thunar process, composited RGBA visual and theme CSS loaded on new windows.
    wid=call('xdotool','getactivewindow')
    normal_geometry=call('xdotool','getwindowgeometry','--shell',wid)
    call('wmctrl','-ir',hex(int(wid)),'-b','add,maximized_vert,maximized_horz')
    spin(lambda: '_NET_WM_STATE_MAXIMIZED_VERT' in call('xprop','-id',wid,'_NET_WM_STATE'))
    call('xdotool','keydown','Down')
    down_process=subprocess.Popen([sys.executable,str(DATA_HELPER := data/'helper.py'),'down'])
    try:
        spin(lambda: '_NET_WM_STATE_MAXIMIZED_VERT' not in call('xprop','-id',wid,'_NET_WM_STATE'))
        assert down_process.poll() is None, 'Down repeat latch released before physical key release'
        subprocess.run([sys.executable,str(DATA_HELPER),'down'],check=True,timeout=2)
    finally:
        call('xdotool','keyup','Down')
    down_process.wait(timeout=2)
    assert '_NET_WM_STATE_HIDDEN' not in call('xprop','-id',wid,'_NET_WM_STATE'), 'Holding Down minimized after restoring'
    subprocess.run([sys.executable,str(DATA_HELPER),'down'],check=True,timeout=2)
    spin(lambda: '_NET_WM_STATE_HIDDEN' in call('xprop','-id',wid,'_NET_WM_STATE'))
    desktop=call('xdotool','search','--onlyvisible','--class','^Xfdesktop$').splitlines()[-1]
    # A minimal Xvfb session may leave _NET_ACTIVE_WINDOW empty after all apps minimize.
    # Supply the real desktop window ID and keep all subsequent X11 calls real.
    output=helper.output
    with patch.object(helper,'output',side_effect=lambda args: desktop if args==['xdotool','getactivewindow'] else output(args)):
        for _ in range(3):
            helper.window_shortcut('down')
    assert 'Map State: IsViewable' in call('xwininfo','-id',desktop)
    call('xdotool','keydown','Up')
    up_process=subprocess.Popen([sys.executable,str(DATA_HELPER),'up'])
    try:
        spin(lambda: '_NET_WM_STATE_HIDDEN' not in call('xprop','-id',wid,'_NET_WM_STATE'))
        assert up_process.poll() is None, 'Up repeat latch released before physical key release'
        subprocess.run([sys.executable,str(DATA_HELPER),'up'],check=True,timeout=2)
    finally:
        call('xdotool','keyup','Up')
    up_process.wait(timeout=2)
    assert '_NET_WM_STATE_MAXIMIZED_' not in call('xprop','-id',wid,'_NET_WM_STATE')
    assert call('xdotool','getwindowgeometry','--shell',wid)==normal_geometry
    call('xdotool','key','super+Down')
    spin(lambda: '_NET_WM_STATE_HIDDEN' in call('xprop','-id',wid,'_NET_WM_STATE'))
    call('xdotool','key','super+Up')
    spin(lambda: '_NET_WM_STATE_HIDDEN' not in call('xprop','-id',wid,'_NET_WM_STATE'))
    spin(lambda: '_NET_WM_STATE_HIDDEN' not in call('xprop','-id',wid,'_NET_WM_STATE'))
    children.append(subprocess.Popen(['thunar',str(home)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE))
    time.sleep(.8)
    ids=call('xdotool','search','--onlyvisible','--class','Thunar').splitlines()
    assert ids, 'Native Thunar did not map a window'
    assert 'Depth: 32' in call('xwininfo','-id',ids[-1]), 'Thunar did not select an RGBA visual'
    geometry=dict(line.split('=',1) for line in call('xdotool','getwindowgeometry','--shell',ids[-1]).splitlines())
    x=ctypes.CDLL('libX11.so.6')
    x.XOpenDisplay.restype=ctypes.c_void_p
    x.XGetImage.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ctypes.c_ulong,ctypes.c_int]
    x.XGetImage.restype=ctypes.c_void_p
    x.XGetPixel.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
    x.XGetPixel.restype=ctypes.c_ulong
    x.XDestroyImage.argtypes=[ctypes.c_void_p]
    x.XCloseDisplay.argtypes=[ctypes.c_void_p]
    display=x.XOpenDisplay(None)
    image=x.XGetImage(display,int(ids[-1]),int(geometry['WIDTH'])-24,int(geometry['HEIGHT'])-40,1,1,ctypes.c_ulong(-1).value,2)
    assert image, 'Could not read native Thunar background pixel'
    alpha=(x.XGetPixel(image,0,0)>>24)&255
    x.XDestroyImage(image); x.XCloseDisplay(display)
    assert 195 <= alpha <= 213, f'Expected 80% local background alpha, got {alpha}/255'
    display=x.XOpenDisplay(None)
    image=x.XGetImage(display,int(wid),window.get_allocated_width()-28,window.get_allocated_height()-45,
                      1,1,ctypes.c_ulong(-1).value,2)
    assert image, 'Could not read native terminal background pixel'
    alpha=(x.XGetPixel(image,0,0)>>24)&255
    x.XDestroyImage(image); x.XCloseDisplay(display)
    assert 225 <= alpha <= 234, f'Expected 90% local terminal background alpha, got {alpha}/255'
    # Export only the disposable CI desktop, never a user screenshot.
    end=time.monotonic()+.3
    while time.monotonic()<end:
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        time.sleep(.01)
    # Picom renders to the Composite overlay; a root-window read omits redirected clients.
    import gi
    gi.require_version('GdkX11','3.0')
    from gi.repository import GdkX11
    comp=ctypes.CDLL('libXcomposite.so.1')
    comp.XCompositeGetOverlayWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    comp.XCompositeGetOverlayWindow.restype=ctypes.c_ulong
    comp.XCompositeReleaseOverlayWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    x.XDefaultRootWindow.argtypes=[ctypes.c_void_p]; x.XDefaultRootWindow.restype=ctypes.c_ulong
    display=x.XOpenDisplay(None); root=x.XDefaultRootWindow(display)
    overlay=comp.XCompositeGetOverlayWindow(display,root)
    foreign=GdkX11.X11Window.foreign_new_for_display(module.Gdk.Display.get_default(),overlay)
    width,height=map(int,call('xdotool','getdisplaygeometry').split())
    pixbuf=module.Gdk.pixbuf_get_from_window(foreign,0,0,width,height)
    pixbuf.savev('/tmp/arch-theme-ci.png','png',[],[])
    comp.XCompositeReleaseOverlayWindow(display,root); x.XCloseDisplay(display)
    window.destroy()
    while Gtk.events_pending(): Gtk.main_iteration_do(False)
    journal=json.loads((data/'installed.json').read_text())
    install.restore(journal['backup'])
    assert (home/'.zshrc').read_text()=='export ARCH_PRESERVED=yes\n'
    print('PASS: Arch/Xfwm, backup/restore, PTYs, split undo, tabs, Super+Down/Up, Ctrl+C, SIGINT, ZLE, clipboard, RGBA windows.')
finally:
    for process in children:
        process.terminate()
    for command,log in logs:
        log.seek(0); print('PROCESS:',command,'\n',log.read().decode(errors='replace')[-4000:]); log.close()
