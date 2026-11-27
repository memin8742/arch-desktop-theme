#!/usr/bin/env python3
"""GTK3/VTE terminal: independent PTYs, native alpha, tabs, split panes and search."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from urllib.parse import unquote, urlparse

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkX11', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gdk, GdkX11, Gio, GLib, Gtk, Pango, Vte

from frame_separators import FrameSeparators

DATA = Path(__file__).resolve().parent
DESIGN = json.loads((DATA / 'design.json').read_text(encoding='utf-8'))


def colour(value, alpha=1):
    result = Gdk.RGBA()
    result.parse(value)
    result.alpha = alpha
    return result


def cwd_for(term):
    uri = term.get_current_directory_uri() if term else None
    if uri:
        parsed = urlparse(uri)
        if parsed.scheme == 'file' and parsed.netloc in ['', 'localhost', os.uname().nodename]:
            candidate = Path(unquote(parsed.path))
            if candidate.is_dir(): return str(candidate)
    return str(Path.home())


class TerminalWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Uçbirim — Zsh')
        self.set_wmclass('arch-terminal', 'ArchTerminal')
        self.set_icon_name('arch-terminal-mark')
        display = self.get_display()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        area = monitor.get_workarea()
        self.set_default_size(max(370, int(area.width * .58)), max(280, int(area.height * .77)))
        self.get_style_context().add_class('arch-terminal')
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual: self.set_visual(visual)
        self.set_app_paintable(True)
        self.current = None
        self.terms = []
        self.frame_separators = FrameSeparators() if isinstance(display, GdkX11.X11Display) else None
        self.separator_update = None
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.get_style_context().add_class('arch-root')
        self.add(root)
        self.search = Gtk.Box(spacing=6)
        self.search.get_style_context().add_class('search-bar')
        self.entry = Gtk.SearchEntry(placeholder_text='Terminal çıktısında ara…')
        self.search.pack_start(self.entry, True, True, 6)
        for label, fn in [('Önceki', self.previous), ('Sonraki', self.next), ('Kapat', self.hide_search)]:
            button = Gtk.Button(label=label)
            button.connect('clicked', lambda _, fn=fn: fn())
            self.search.pack_start(button, False, False, 0)
        self.entry.connect('search-changed', self.search_changed)
        self.entry.connect('activate', lambda _: self.next())
        root.pack_start(self.search, False, False, 0)
        self.book = Gtk.Notebook(scrollable=True)
        self.book.set_show_border(False)
        self.book.connect('switch-page', self.page_changed)
        root.pack_start(self.book, True, True, 0)
        self.connect('map-event', self.schedule_separators)
        self.connect('window-state-event', self.schedule_separators)
        self.connect('size-allocate', self.schedule_separators)
        self.connect('key-press-event', self.key)
        self.connect('delete-event', self.close_requested)
        self.connect('destroy', self.stop)
        self.new_tab(str(Path.cwd()))
        self.show_all()
        self.search.hide()
        self.book.set_show_tabs(False)

    def make_term(self, cwd):
        term = Vte.Terminal()
        appearance = Gtk.CssProvider()
        appearance.load_from_data(b'vte-terminal, VteTerminal { padding: 15px 22px; }')
        term.get_style_context().add_provider(appearance, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        term.set_font(Pango.FontDescription('Fira Code 10'))
        if self.get_allocated_width() >= 600 or self.get_default_size()[0] >= 600:
            term.set_font_scale(1.15)
        background = DESIGN['terminal']['zemin_saydamligi']
        term.set_colors(colour('#FFFFFF'), colour(background['renk'], background['opaklik']),
                        [colour(c) for c in DESIGN['terminal']['ansi_0_15']])
        term.set_color_bold(colour('#FFFFFF'))
        term.set_color_cursor(colour('#FFFFFF'))
        term.set_color_cursor_foreground(colour(background['renk']))
        term.set_cursor_blink_mode(Vte.CursorBlinkMode.OFF)
        term.set_color_highlight(colour('#125279'))
        term.set_color_highlight_foreground(colour('#FFFFFF'))
        term.set_allow_bold(True)
        term.set_bold_is_bright(False)
        term.set_audible_bell(False)
        term.set_scrollback_lines(20000)
        term.set_scroll_on_output(False)
        term.set_scroll_on_keystroke(True)
        term.set_search_wrap_around(True) if hasattr(term, 'set_search_wrap_around') else term.search_set_wrap_around(True)
        term.set_mouse_autohide(True)
        term.shell_pid = None
        term.spawn_cancellable = Gio.Cancellable()
        term.arch_search_text = None
        term.connect('focus-in-event', self.focus_term)
        term.connect('window-title-changed', self.title_changed)
        term.connect('child-exited', self.exited)
        term.connect('button-press-event', self.context_menu)
        env = dict(os.environ, ARCH_THEME_TERMINAL='1', ARCH_THEME_WINDOW_PID=str(os.getpid()), TERM='xterm-256color', COLORTERM='truecolor')
        env['PATH'] = str(Path.home()/'.local/bin') + os.pathsep + env.get('PATH','/usr/bin:/bin')
        # Inherit environment (including DBus) but no commands from preview screenshots.
        self.terms.append(term)
        term.spawn_async(Vte.PtyFlags.DEFAULT, cwd, ['/bin/zsh', '-i'],
            [k+'='+v for k,v in env.items()], GLib.SpawnFlags.DEFAULT,
            None, None, -1, term.spawn_cancellable, self.spawned, None)
        return term

    def spawned(self, term, pid, error, *unused):
        if term is None: return
        if term not in self.terms:
            if pid > 0:
                try: os.kill(pid, signal.SIGHUP)
                except ProcessLookupError: pass
            return
        if error:
            term.feed(('Zsh başlatılamadı: '+str(error)+'\r\n').encode())
        else: term.shell_pid = pid

    def at_prompt(self, term):
        try:
            return term.shell_pid and os.tcgetpgrp(term.get_pty().get_fd()) == term.shell_pid
        except (OSError, AttributeError): return False

    def new_tab(self, cwd=None):
        term = self.make_term(cwd or cwd_for(self.current))
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.pack_start(term, True, True, 0)
        label = Gtk.Box(spacing=4)
        label.pack_start(Gtk.Label(label='Zsh'), True, True, 0)
        close = Gtk.Button.new_from_icon_name('window-close-symbolic', Gtk.IconSize.MENU)
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.set_tooltip_text('Sekmeyi kapat')
        close.connect('clicked', lambda _: self.close_page(page))
        label.pack_end(close, False, False, 0)
        self.book.append_page(page, label)
        self.book.set_tab_reorderable(page, True)
        page.show_all(); label.show_all()
        self.book.set_show_tabs(self.book.get_n_pages() > 1)
        self.book.set_current_page(self.book.page_num(page))
        self.current = term
        term.grab_focus()

    def split(self, orientation):
        old = self.current
        if old is None: return
        parent = old.get_parent()
        # Keep the original pane slot when splitting an already split tree.
        is_first = isinstance(parent, Gtk.Paned) and parent.get_child1() == old
        parent.remove(old)
        pane = Gtk.Paned(orientation=orientation)
        pane.connect('size-allocate', self.schedule_separators)
        if isinstance(parent, Gtk.Paned):
            (parent.pack1 if is_first else parent.pack2)(pane, True, False)
        else: parent.pack_start(pane, True, True, 0)
        new = self.make_term(cwd_for(old))
        pane.pack1(old, True, False); pane.pack2(new, True, False)
        pane.show_all()
        def balance():
            if pane.get_parent() is None: return False
            size = pane.get_allocated_width() if orientation == Gtk.Orientation.HORIZONTAL else pane.get_allocated_height()
            pane.set_position(max(1, size//2)); return False
        GLib.idle_add(balance)
        self.current = new; new.grab_focus()

    def schedule_separators(self, *unused):
        if self.frame_separators and self.separator_update is None:
            self.separator_update = GLib.idle_add(self.sync_separators)
        return False

    def sync_separators(self):
        self.separator_update = None
        if not self.get_mapped(): return False
        page = self.book.get_nth_page(self.book.get_current_page())
        end = page.translate_coordinates(self, 0, page.get_allocated_height()) if page else None
        separators = list(self.bottom_separators(page, end[1])) if end else []
        self.frame_separators.sync(self.get_window().get_xid(), separators)
        return False

    def bottom_separators(self, widget, bottom):
        if isinstance(widget, Gtk.Paned) and widget.get_orientation() == Gtk.Orientation.HORIZONTAL:
            first, second = widget.get_child1(), widget.get_child2()
            if first and second:
                end = first.translate_coordinates(self, first.get_allocated_width(), first.get_allocated_height())
                start = second.translate_coordinates(self, 0, 0)
                if end and start and end[1] == bottom and start[0] > end[0]:
                    yield end[0], end[1], start[0] - end[0]
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                yield from self.bottom_separators(child, bottom)

    def close_last_split(self):
        page = self.book.get_nth_page(self.book.get_current_page())
        terms = self.descendants(page)
        if len(terms) < 2: return
        last = next(term for term in reversed(self.terms) if term in terms)
        if last.shell_pid and not self.at_prompt(last):
            if not self.confirm('Son bölmede çalışan bir iş var. Bölme kapatılsın mı?'): return
        if last in self.terms:
            self.remove_term(last)

    def focus_term(self, term, event):
        self.current = term
        self.title_changed(term)
        return False

    def title_changed(self, term):
        if term == self.current:
            directory = cwd_for(term).replace(str(Path.home()), '~', 1)
            self.set_title('zsh '+directory)

    def page_changed(self, book, page, number):
        self.schedule_separators()
        terms = self.descendants(page)
        if terms:
            term = terms[0]
            self.current = term
            def focus_current():
                if self.current == term and book.get_nth_page(book.get_current_page()) == page:
                    term.grab_focus()
                return False
            GLib.idle_add(focus_current)

    def descendants(self, widget):
        if isinstance(widget, Vte.Terminal): return [widget]
        result = []
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children(): result += self.descendants(child)
        return result

    def confirm(self, text):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL, text=text)
        response = dialog.run(); dialog.destroy()
        return response == Gtk.ResponseType.OK

    def close_requested(self, *unused):
        return not self.confirm('Terminal penceresi kapatılsın mı? İçindeki açık işler sonlanır.')

    def close_page(self, page):
        if not self.confirm('Bu sekme ve içindeki işler kapatılsın mı?'): return
        for term in self.descendants(page): self.stop_term(term)
        self.book.remove_page(self.book.page_num(page))
        self.book.set_show_tabs(self.book.get_n_pages() > 1)
        if not self.book.get_n_pages(): self.destroy()

    def stop_term(self, term):
        if term in self.terms: self.terms.remove(term)
        term.spawn_cancellable.cancel()
        try:
            if term.shell_pid: os.kill(term.shell_pid, signal.SIGHUP)
        except ProcessLookupError: pass

    def stop(self, *unused):
        if self.separator_update is not None:
            GLib.source_remove(self.separator_update)
            self.separator_update = None
        if self.frame_separators:
            self.frame_separators.close()
            self.frame_separators = None
        for term in list(self.terms):
            self.stop_term(term)

    def exited(self, term, status):
        term.shell_pid = None
        if term in self.terms:
            self.remove_term(term)

    def remove_term(self, term):
        had_focus = term == self.current
        if had_focus: self.current = None
        self.stop_term(term)
        parent = term.get_parent()
        if isinstance(parent, Gtk.Paned):
            sibling = parent.get_child2() if parent.get_child1() == term else parent.get_child1()
            outer = parent.get_parent()
            is_first = isinstance(outer, Gtk.Paned) and outer.get_child1() == parent
            parent.remove(sibling); outer.remove(parent)
            parent.destroy()
            if isinstance(outer, Gtk.Paned): (outer.pack1 if is_first else outer.pack2)(sibling, True, False)
            else: outer.pack_start(sibling, True, True, 0)
            sibling.show_all()
            candidates = self.descendants(sibling)
            if had_focus:
                self.current = candidates[0]
            if self.current in candidates:
                self.current.grab_focus()
        else:
            self.book.remove_page(self.book.page_num(parent))
            self.book.set_show_tabs(self.book.get_n_pages() > 1)
        self.schedule_separators()
        if not self.terms: self.destroy()

    def search_changed(self, *unused):
        if not self.current: return
        text = self.entry.get_text()
        if self.current.arch_search_text == text: return
        regex = Vte.Regex.new_for_search(re.escape(text), -1, 0x00000400) if text else None  # PCRE2_MULTILINE
        self.current.search_set_regex(regex, 0)
        self.current.arch_search_text = text

    def next(self):
        if self.current: self.search_changed(); self.current.search_find_next()

    def previous(self):
        if self.current: self.search_changed(); self.current.search_find_previous()

    def hide_search(self):
        self.search.hide()
        if self.current:
            self.current.search_set_regex(None, 0)
            self.current.arch_search_text = None
            self.current.unselect_all()
            self.current.grab_focus()

    def context_menu(self, term, event):
        if event.button != 3: return False
        self.current = term
        menu = Gtk.Menu()
        actions = [('Kopyala', lambda: self.copy(term)), ('Yapıştır', term.paste_clipboard),
                   ('Yeni sekme', self.new_tab), ('Yan yana böl', lambda: self.split(Gtk.Orientation.HORIZONTAL)),
                   ('Üst üste böl', lambda: self.split(Gtk.Orientation.VERTICAL)),
                   ('Çıktıda ara', lambda: (self.search.show_all(), self.entry.grab_focus()))]
        for label, fn in actions:
            item = Gtk.MenuItem(label=label); item.connect('activate',lambda _,fn=fn:fn()); menu.append(item)
        menu.show_all(); menu.popup_at_pointer(event)
        return True

    def copy(self, term):
        if term.get_has_selection(): term.copy_clipboard_format(Vte.Format.TEXT)
        elif self.at_prompt(term): term.feed_child(b'\x1b[99;5u')  # ZLE selection → system clipboard.
        # Without a selection, Ctrl+C never sends SIGINT to foreground jobs.

    def key(self, window, event):
        mask = Gtk.accelerator_get_default_mod_mask()
        state = event.state & mask
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        alt = bool(state & Gdk.ModifierType.MOD1_MASK)
        key = Gdk.keyval_name(event.keyval).lower()
        term = self.current
        if key == 'escape' and self.search.get_visible(): self.hide_search(); return True
        # Do not steal entry editing shortcuts from the search box.
        if self.entry.has_focus(): return False
        if not term: return False
        if alt and not ctrl and key == 't': GLib.idle_add(self.new_tab); return True
        if ctrl and key == 'c':
            if shift: term.feed_child(b'\x03')
            else: self.copy(term)
            return True
        if ctrl and key == 'v':
            if shift: term.feed_child(b'\x16')
            else: term.paste_clipboard()
            return True
        if ctrl and shift and key == 'f': self.search.show_all(); self.entry.grab_focus(); return True
        if ctrl and shift and key in ['r','d']:
            GLib.idle_add(self.split, Gtk.Orientation.HORIZONTAL if key == 'r' else Gtk.Orientation.VERTICAL)
            return True
        if ctrl and shift and not alt and key == 'b':
            GLib.idle_add(self.close_last_split)
            return True
        if shift and key in ['left','right','up','down'] and self.at_prompt(term):
            code = {'up':'A','down':'B','right':'C','left':'D'}[key]
            term.feed_child(('\x1b[1;'+('6' if ctrl else '2')+code).encode()); return True
        return False


class Application(Gtk.Application):
    def __init__(self):
        # One process per invocation/window: no accidental reuse of the previous terminal.
        super().__init__(application_id='io.github.memin8742.ArchTerminal', flags=Gio.ApplicationFlags.NON_UNIQUE)

    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_path(str(DATA/'terminal.css'))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        TerminalWindow(self).present()


if __name__ == '__main__':
    if '--self-check' in sys.argv:
        assert len(DESIGN['terminal']['ansi_0_15']) == 16
        assert (DATA/'terminal.css').is_file()
        print('GTK3, VTE, Zsh tasarım dosyası ve CSS bulundu.'); sys.exit(0)
    Application().run([sys.argv[0]])
