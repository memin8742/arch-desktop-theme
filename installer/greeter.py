"""Arch Blue's GTK login screen. LightDM manages PAM and starts the session."""
import datetime
import os
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('LightDM', '1')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, LightDM


WALLPAPER = '/usr/share/backgrounds/arch-blue/wallpaper.png'
MONTHS = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
          'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')


def icon(name, size):
    image = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.BUTTON)
    image.set_pixel_size(size)
    return image


def button(name, callback, tooltip):
    widget = Gtk.Button()
    widget.set_name(name)
    widget.set_relief(Gtk.ReliefStyle.NONE)
    widget.set_tooltip_text(tooltip)
    widget.get_accessible().set_name(tooltip)
    widget.connect('clicked', callback)
    return widget


def choose(anchor, options, selected):
    menu = Gtk.Menu()
    for text, value in options:
        item = Gtk.MenuItem.new_with_label(text)
        item.connect('activate', lambda unused, value=value: selected(value))
        menu.append(item)
    menu.attach_to_widget(anchor, None)
    menu.show_all()
    menu.popup_at_widget(anchor, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)


def read_status(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=.6,
                                env={**os.environ, 'LC_ALL':'C'}, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


class Login:
    def __init__(self):
        self.dm = LightDM.Greeter()
        self.dm.connect('show-prompt', self.prompt)
        self.dm.connect('show-message', lambda _, text, kind: self.notice.set_text(text))
        self.dm.connect('authentication-complete', self.authenticated)
        self.dm.connect('autologin-timer-expired', self.autologin)
        if not self.dm.connect_to_daemon_sync():
            raise RuntimeError('LightDM bağlantısı kurulamadı.')

        self.window = Gtk.Window(title='Arch Blue')
        self.window.set_decorated(False)
        self.window.connect('delete-event', lambda *_: True)
        for event in ('key-press-event', 'button-press-event'):
            self.window.connect(event, self.cancel_timer)
        monitor = Gdk.Display.get_default().get_primary_monitor() or Gdk.Display.get_default().get_monitor(0)
        rect = monitor.get_geometry()
        self.window.move(rect.x, rect.y)
        self.window.set_default_size(rect.width, rect.height)
        self.window.fullscreen()
        self.overlay = Gtk.Overlay()
        self.window.add(self.overlay)
        self.overlay.add(Gtk.DrawingArea())
        self.wallpaper = GdkPixbuf.Pixbuf.new_from_file(WALLPAPER)
        self.backdrop = Gtk.Image()
        self.overlay.add_overlay(self.backdrop)
        self.overlay.set_overlay_pass_through(self.backdrop, True)
        self.positions = {}
        self.overlay.connect('get-child-position', self.position)
        self.scale = 1
        self.icons = []
        self.provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(self.window.get_screen(), self.provider,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.clock = Gtk.Label(name='clock')
        self.date = Gtk.Label(name='date')
        self.place(self.clock, .5, .078)
        self.place(self.date, .5, .156)
        self.tick()
        GLib.timeout_add_seconds(1, self.tick)

        self.users = LightDM.UserList.get_instance()
        listed = [] if self.dm.get_hide_users_hint() else self.users.get_users()
        hint = self.dm.get_select_user_hint()
        self.username = hint or (listed[0].get_name() if listed else None)
        self.sessions = {s.get_key(): s.get_name() for s in LightDM.get_sessions()}
        self.session = None
        self.session_changed = False
        self.waiting = False
        self.user_button = button('user', self.pick_user, 'Kullanıcı seç')
        self.user_label = Gtk.Label()
        self.user_box = Gtk.Box(spacing=12)
        avatar = self.image('avatar-default-symbolic', 29)
        avatar.set_name('avatar')
        self.user_box.pack_start(avatar, False, False, 0)
        self.user_box.pack_start(self.user_label, False, False, 0)
        self.user_button.add(self.user_box)
        self.place(self.user_button, .5, .805, align='user')

        self.field = Gtk.Overlay()
        self.shape = Gtk.Image()
        self.field.add(self.shape)
        row = Gtk.Box()
        self.entry = Gtk.Entry(name='password')
        self.entry.set_visibility(False)
        self.entry.set_invisible_char('●')
        self.entry.connect('activate', self.submit)
        self.entry.get_accessible().set_name('Parola')
        row.pack_start(self.entry, True, True, 0)
        self.arrow = button('submit', self.submit, 'Oturum aç')
        self.arrow.add(Gtk.Label(label='→'))
        row.pack_end(self.arrow, False, False, 0)
        self.field.add_overlay(row)
        self.place(self.field, .5, .876)
        self.notice = Gtk.Label(name='notice', wrap=True)
        self.notice.set_max_width_chars(48)
        self.place(self.notice, .5, .948)
        self.session_button = button('session', self.pick_session, 'Masaüstü oturumunu seç')
        self.session_label = Gtk.Label()
        self.decorate(self.session_button, 'video-display-symbolic', self.session_label)
        self.place(self.session_button, .016, .952, align='left')

        self.status = Gtk.Box(spacing=8)
        layout = button('layout', self.pick_layout, 'Klavye düzeni')
        self.layout_label = Gtk.Label()
        self.decorate(layout, 'input-keyboard-symbolic', self.layout_label)
        self.status.pack_start(layout, False, False, 0)
        self.status.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        self.audio = button('audio', self.toggle_sound, 'Sesi aç veya kapat')
        self.speaker = self.image('audio-volume-high-symbolic', 23)
        self.audio.add(self.speaker)
        self.status.pack_start(self.audio, False, False, 0)
        self.network = self.image('network-wired-symbolic', 24)
        self.status.pack_start(self.network, False, False, 0)
        self.place(self.status, .984, .032, align='right')
        power = Gtk.Box(spacing=6)
        for label, name, allowed, action in [
            ('Yeniden başlat', 'view-refresh-symbolic', LightDM.get_can_restart, LightDM.restart),
            ('Kapat', 'system-shutdown-symbolic', LightDM.get_can_shutdown, LightDM.shutdown),
        ]:
            control = button('power', lambda _, text=label, fn=action: self.power_action(text, fn), label)
            control.add(self.image(name, 25))
            control.set_sensitive(allowed())
            if power.get_children():
                power.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
            power.pack_start(control, False, False, 0)
        self.place(power, .984, .952, align='right')

        self.resize(self.window, rect)
        self.window.connect('size-allocate', self.resize)
        turkish = next((layout for layout in LightDM.get_layouts() if layout.get_name() == 'tr'), None)
        if turkish:
            LightDM.set_layout(turkish)
        self.update_layout()
        self.update_status()
        GLib.timeout_add_seconds(10, self.update_status)
        self.window.show_all()
        self.begin(self.username)

    def image(self, name, size):
        widget = icon(name, size)
        self.icons.append((widget, size))
        return widget

    def decorate(self, control, name, label):
        box = Gtk.Box(spacing=8)
        box.pack_start(self.image(name, 25), False, False, 0)
        box.pack_start(label, False, False, 0)
        control.add(box)

    def place(self, widget, x, y, align='center'):
        self.positions[widget] = (x, y, align)
        self.overlay.add_overlay(widget)

    def position(self, overlay, widget, rect):
        if widget == self.backdrop:
            rect.x = rect.y = 0
            rect.width, rect.height = overlay.get_allocated_width(), overlay.get_allocated_height()
            return True
        if widget not in self.positions:
            return False
        x, y, align = self.positions[widget]
        _, size = widget.get_preferred_size()
        rect.width, rect.height = size.width, size.height
        left = x * overlay.get_allocated_width()
        if align == 'center': left -= size.width / 2
        if align == 'right': left -= size.width
        if align == 'user': left -= 124 * self.scale
        rect.x = round(left)
        rect.y = round(y * overlay.get_allocated_height() - size.height / 2)
        return True

    def resize(self, window, area):
        dimensions = area.width, area.height
        if getattr(self, 'dimensions', None) != dimensions:
            self.dimensions = dimensions
            width, height = self.wallpaper.get_width(), self.wallpaper.get_height()
            ratio = min(width / area.width, height / area.height)
            crop_w, crop_h = round(area.width * ratio), round(area.height * ratio)
            crop = self.wallpaper.new_subpixbuf((width - crop_w) // 2, (height - crop_h) // 2, crop_w, crop_h)
            self.backdrop.set_from_pixbuf(crop.scale_simple(*dimensions, GdkPixbuf.InterpType.BILINEAR))
        scale = max(.55, min(area.width / 1672, area.height / 941))
        if getattr(self, 'sized', None) == scale: return
        self.scale = self.sized = scale
        px = lambda n: max(1, round(n * scale))
        self.shape.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(Path(__file__).with_name('entry.svg')), px(340), px(51), False))
        self.field.set_size_request(px(340), px(51))
        self.arrow.set_size_request(px(68), -1)
        for image, size in self.icons:
            image.set_pixel_size(px(size))
        self.provider.load_from_data(f'''
window {{ background: #010a19; color: #e1eeff; font-family: "Adwaita Sans", sans-serif; }}
#wallpaper {{ background: #020b19 url("{Path(WALLPAPER).as_uri()}") center / cover no-repeat; }}
label {{ color: #dcecff; font-size: {px(20)}px; }}
#clock {{ color: #d5e4fa; font-size: {px(103)}px; letter-spacing: {px(2)}px; font-weight: 200; }}
#date {{ color: #6bb2e9; font-size: {px(31)}px; }}
#user label {{ font-size: {px(27)}px; }}
#avatar {{ color: #37a4ee; padding: {px(10)}px; border: 1px solid #39a8f4; border-radius: 50%; }}
button, #password {{ background: transparent; border: none; border-radius: 4px; box-shadow: none; color: #d8edff; }}
button {{ padding: {px(4)}px {px(7)}px; min-width: 0; min-height: 0; }}
button:hover, button:focus {{ background: rgba(31,121,183,.20); }}
#password {{ padding: 0 {px(24)}px; font-size: {px(22)}px; caret-color: #e6f5ff; }}
#submit label {{ color: #e3f3ff; font-size: {px(31)}px; }}
#notice {{ color: #c8e5ff; font-size: {px(16)}px; }}
separator {{ background: #365475; min-width: 1px; margin: {px(5)}px; }}
menu, dialog {{ background: #07182b; color: #deedff; }}
menuitem:hover {{ background: #164568; }}
'''.encode())

    def tick(self):
        now = datetime.datetime.now()
        self.clock.set_text(now.strftime('%H:%M'))
        self.date.set_text(f'{now.day} {MONTHS[now.month-1]} {now.year}')
        return True

    def cancel_timer(self, widget, event):
        self.dm.cancel_autologin()
        return False

    def autologin(self, dm):
        self.automatic = True
        dm.authenticate_autologin()

    def pick_user(self, widget):
        users = [] if self.dm.get_hide_users_hint() else self.users.get_users()
        choose(widget, [(u.get_display_name(),u.get_name()) for u in users] + [('Diğer kullanıcı…',None)], self.begin)

    def begin(self, username):
        self.automatic = False
        self.username = username
        user = self.users.get_user_by_name(username) if username else None
        self.user_label.set_text((user.get_display_name() if user else username) or 'Kullanıcı')
        if not self.session_changed:
            preferred = user.get_session() if user else None
            self.select_session(preferred if preferred in self.sessions else self.dm.get_default_session_hint())
        self.notice.set_text('')
        self.entry.set_text('')
        self.waiting = False
        self.entry.set_sensitive(False)
        self.arrow.set_sensitive(False)
        self.dm.authenticate(username)

    def prompt(self, dm, text, kind):
        secret = kind == LightDM.PromptType.SECRET
        self.entry.set_text('')
        self.entry.set_visibility(not secret)
        self.entry.set_input_purpose(Gtk.InputPurpose.PASSWORD if secret else Gtk.InputPurpose.FREE_FORM)
        self.entry.set_placeholder_text(None if secret else text)
        self.entry.get_accessible().set_name(text)
        if secret and text.strip().lower().rstrip(':') not in ('password','parola','şifre'):
            self.notice.set_text(text)
        self.waiting = True
        self.entry.set_sensitive(True)
        self.arrow.set_sensitive(True)
        self.entry.grab_focus()

    def submit(self, unused):
        if not self.waiting or not self.dm.get_in_authentication(): return
        self.waiting = False
        response = self.entry.get_text()
        self.entry.set_text('')
        self.entry.set_sensitive(False)
        self.arrow.set_sensitive(False)
        self.dm.respond(response)

    def authenticated(self, dm):
        if dm.get_is_authenticated():
            session = self.session
            if self.automatic:
                session = dm.get_autologin_session_hint() or session
            elif not self.session_changed and self.username is None:
                account = self.users.get_user_by_name(dm.get_authentication_user())
                if account and account.get_session() in self.sessions:
                    session = account.get_session()
            try:
                if dm.start_session_sync(session): return
            except GLib.Error:
                pass
            error = 'Oturum başlatılamadı.'
        else:
            error = 'Giriş başarısız. Tekrar deneyin.'
        self.begin(self.username)
        self.notice.set_text(error)

    def pick_session(self, widget):
        def selected(key):
            self.session_changed = True
            self.select_session(key)
        choose(widget, [(name,key) for key,name in self.sessions.items()], selected)

    def select_session(self, key):
        self.session = key if key in self.sessions else next(iter(self.sessions),None)
        label = self.sessions.get(self.session,'Oturum')
        self.session_label.set_text('Xfce' if self.session == 'xfce' else label)

    def update_layout(self):
        current = LightDM.get_layout()
        self.layout_label.set_text((current.get_name().split('\t')[0].upper() if current else 'Klavye') + ' ⌄')

    def pick_layout(self, widget):
        current = LightDM.get_layout()
        names = {'tr', 'us', current.get_name() if current else 'tr'}
        layouts = [(v.get_description(),v) for v in LightDM.get_layouts() if v.get_name() in names]
        def selected(layout):
            LightDM.set_layout(layout)
            self.update_layout()
            self.entry.grab_focus()
        choose(widget, layouts, selected)

    def update_status(self):
        mute = read_status('pactl','get-sink-mute','@DEFAULT_SINK@') if shutil.which('pactl') else ''
        self.audio.set_sensitive(bool(mute))
        self.speaker.set_from_icon_name('audio-volume-high-symbolic' if mute.endswith('no') else 'audio-volume-muted-symbolic', Gtk.IconSize.BUTTON)
        self.speaker.set_pixel_size(round(23*self.scale))
        info = read_status('nmcli','-t','-f','TYPE,STATE','device') if shutil.which('nmcli') else ''
        connected = {line.split(':',1)[0] for line in info.splitlines() if line.endswith(':connected')}
        network = 'network-wireless' if 'wifi' in connected else 'network-wired' if 'ethernet' in connected else 'network-offline'
        self.network.set_from_icon_name(network+'-symbolic', Gtk.IconSize.BUTTON)
        self.network.set_pixel_size(round(24*self.scale))
        self.network.set_tooltip_text({'network-wired':'Kablolu bağlantı', 'network-offline':'Ağ bağlantısı yok',
                                      'network-wireless':'Kablosuz bağlantı'}[network])
        return True

    def toggle_sound(self, unused):
        read_status('pactl','set-sink-mute','@DEFAULT_SINK@','toggle')
        self.update_status()

    def power_action(self, label, action):
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, text=label+'?')
        dialog.add_button('Vazgeç',Gtk.ResponseType.CANCEL)
        dialog.add_button(label,Gtk.ResponseType.OK)
        approved = dialog.run() == Gtk.ResponseType.OK
        dialog.destroy()
        if approved:
            try:
                if action(): return
            except GLib.Error:
                pass
            self.notice.set_text('Güç işlemi gerçekleştirilemedi.')


if __name__ == '__main__':
    login = Login()
    Gtk.main()
