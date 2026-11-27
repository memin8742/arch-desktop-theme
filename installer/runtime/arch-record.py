#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path
import os
import signal
import subprocess

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk


def command(arguments):
    return subprocess.run(arguments, text=True, capture_output=True, check=False)


def region_selected(callback):
    screen = Gdk.Screen.get_default()
    window = Gtk.Window(decorated=False)
    window.set_skip_taskbar_hint(True)
    window.set_keep_above(True)
    window.set_visual(screen.get_rgba_visual())
    window.set_app_paintable(True)
    window.fullscreen()
    canvas = Gtk.DrawingArea()
    canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                      Gdk.EventMask.POINTER_MOTION_MASK)
    window.add(canvas)
    start = end = None

    def bounds():
        return min(start[0], end[0]), min(start[1], end[1]), abs(start[0]-end[0]), abs(start[1]-end[1])

    def draw(_, context):
        context.set_operator(1)  # Cairo SOURCE lets the selected region appear through the window.
        context.set_source_rgba(.04, .12, .19, .66)
        context.paint()
        if start and end:
            x, y, width, height = bounds()
            context.set_source_rgba(0, 0, 0, 0)
            context.rectangle(x, y, width, height)
            context.fill()
            context.set_source_rgba(.04,.65,.94,1)
            context.set_line_width(2)
            context.rectangle(x, y, width, height)
            context.stroke()
        return False

    def press(_, event):
        nonlocal start, end
        if event.button == Gdk.BUTTON_PRIMARY:
            start = end = (int(event.x), int(event.y))
            canvas.queue_draw()
        return True

    def motion(_, event):
        nonlocal end
        if start:
            end = (int(event.x), int(event.y))
            canvas.queue_draw()
        return True

    def release(_, event):
        if start and event.button == Gdk.BUTTON_PRIMARY:
            motion(canvas, event)
            x, y, width, height = bounds()
            origin_x, origin_y = window.get_position()
            window.destroy()
            if width >= 8 and height >= 8:
                GLib.timeout_add(250, callback, (origin_x+x, origin_y+y, width, height))
        return True

    window.connect('key-press-event', lambda _, event: window.destroy() if event.keyval == Gdk.KEY_Escape else False)
    canvas.connect('draw', draw)
    canvas.connect('button-press-event', press)
    canvas.connect('motion-notify-event', motion)
    canvas.connect('button-release-event', release)
    window.show_all()
    return window


class Recorder(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.github.memin8742.ArchTheme.ScreenRecorder')
        self.process = None
        self.tray = None
        self.held = False
        self.file = None
        self.log = None

    def hold_session(self):
        if not self.held:
            self.hold()
            self.held = True

    def release_session(self):
        if self.held:
            self.release()
            self.held = False

    def error(self, message):
        alert = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text=message)
        alert.run()
        alert.destroy()

    def do_activate(self):
        if self.process:
            self.show_stop()
            return
        dialog = Gtk.Dialog(title='Ekran Kaydı', modal=True)
        self.add_window(dialog)
        dialog.add_button('Vazgeç', Gtk.ResponseType.CANCEL)
        dialog.add_button('Bölge seç', 1)
        dialog.add_button('Pencere seç', 2)
        box = dialog.get_content_area()
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(15)
        box.set_margin_bottom(10)
        box.add(Gtk.Label(label='Kaydedilecek ekran bölgesini veya pencereyi seçin.', xalign=0))
        speaker = Gtk.CheckButton(label='Sistem sesini kaydet')
        microphone = Gtk.CheckButton(label='Mikrofonu kaydet')
        box.add(speaker)
        box.add(microphone)
        dialog.show_all()
        response = dialog.run()
        sounds = speaker.get_active(), microphone.get_active()
        dialog.destroy()
        if response == 1:
            self.hold_session()
            picker = region_selected(lambda region: self.record(region, None, sounds))
            if picker is not None:
                picker.connect('destroy', self.cancel_selection)
        elif response == 2:
            self.hold_session()
            select = Gio.Subprocess.new(['xdotool', 'selectwindow'], Gio.SubprocessFlags.STDOUT_PIPE)
            select.communicate_utf8_async(None, None, self.window_selected, sounds)

    def cancel_selection(self, _):
        GLib.timeout_add(500, self.release_if_idle)

    def release_if_idle(self):
        if not self.process:
            self.release_session()
        return False

    def window_selected(self, select, result, sounds):
        _, output, _ = select.communicate_utf8_finish(result)
        output = output.strip()
        if select.get_successful() and output.isdecimal() and int(output):
            self.record(None, output, sounds)
        else:
            self.release_session()

    def record(self, region, window_id, sounds):
        folder = command(['xdg-user-dir', 'VIDEOS']).stdout.strip()
        directory = Path(folder or Path.home() / 'Videos') / 'Ekran Kayıtları'
        directory.mkdir(parents=True, exist_ok=True)
        self.file = directory / f'Kayit-{datetime.now():%Y%m%d-%H%M%S-%f}.mkv'
        display = os.environ.get('DISPLAY', ':0')
        capture = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                   '-f', 'x11grab', '-framerate', '25']
        if region:
            x, y, width, height = region
            capture += ['-video_size', f'{width}x{height}', '-i', f'{display}+{x},{y}']
        else:
            capture += ['-window_id', window_id, '-i', display]
        sources = []
        if sounds[0]:
            sink = command(['pactl', 'get-default-sink']).stdout.strip()
            if sink:
                sources.append(sink + '.monitor')
        if sounds[1]:
            source = command(['pactl', 'get-default-source']).stdout.strip()
            if source and not source.endswith('.monitor'):
                sources.append(source)
        if len(sources) != sum(sounds):
            self.error('Seçilen ses kaynağı bu bilgisayarda kullanılamıyor.')
            self.release_session()
            return False
        for source in sources:
            capture += ['-thread_queue_size', '256', '-f', 'pulse', '-i', source]
        if len(sources) == 2:
            capture += ['-filter_complex', '[1:a][2:a]amix=inputs=2[audio]', '-map', '0:v', '-map', '[audio]']
        elif sources:
            capture += ['-map', '0:v', '-map', '1:a']
        capture += ['-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-y', str(self.file)]
        state = Path.home() / '.local/state/arch-desktop-theme'
        state.mkdir(parents=True, exist_ok=True)
        self.log = state / 'recording.log'
        try:
            with self.log.open('w') as stream:
                self.process = subprocess.Popen(capture, stderr=stream)
        except OSError as error:
            self.error(str(error))
            self.release_session()
            return False
        self.tray = Gtk.StatusIcon.new_from_icon_name('media-record')
        self.tray.set_tooltip_text('Ekran kaydı sürüyor · Durdur')
        self.tray.connect('activate', lambda _: self.show_stop())
        GLib.timeout_add(500, self.poll)
        return False

    def show_stop(self):
        dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.INFO, text='Ekran kaydı sürüyor.')
        dialog.add_button('Sürdür', Gtk.ResponseType.CANCEL)
        dialog.add_button('Durdur ve kaydet', Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)

    def poll(self):
        if self.process.poll() is None:
            return True
        self.tray.set_visible(False)
        if self.file.is_file() and self.file.stat().st_size > 1024:
            command(['notify-send', 'Ekran kaydı kaydedildi', str(self.file)])
        else:
            self.error(self.log.read_text().strip() or 'Ekran kaydı oluşturulamadı.')
        self.process = None
        self.release_session()
        return False


if __name__ == '__main__':
    Recorder().run(None)
