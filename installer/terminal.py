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
gi.require_version('Vte', '2.91')
from gi.repository import Gdk, Gio, GLib, Gtk, Pango, Vte

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
        self.set_icon_name('utilities-terminal')
        self.set_default_size(920, 700)
        self.get_style_context().add_class('arch-terminal')
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual: self.set_visual(visual)
        self.set_app_paintable(True)
        self.current = None
        self.terms = []
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
        self.connect('key-press-event', self.key)
        self.connect('delete-event', self.close_requested)
        self.connect('destroy', lambda _: [self.stop_term(t) for t in list(self.terms)])
        self.new_tab(str(Path.cwd()))
        self.show_all()
        self.search.hide()
        self.book.set_show_tabs(False)

    def make_term(self, cwd):
        term = Vte.Terminal()
        term.set_font(Pango.FontDescription('Fira Code 10'))
        term.set_colors(colour('#FFFFFF'), colour('#041321', .8),
                        [colour(c) for c in DESIGN['terminal']['ansi_0_15']])
        term.set_color_bold(colour('#FFFFFF'))
        term.set_color_cursor(colour('#49AEE6'))
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
        term.connect('focus-in-event', self.focus_term)
        term.connect('window-title-changed', self.title_changed)
        term.connect('child-exited', self.exited)
        term.connect('button-press-event', self.context_menu)
        env = dict(os.environ, ARCH_THEME_TERMINAL='1', ARCH_THEME_WINDOW_PID=str(os.getpid()), TERM='xterm-256color', COLORTERM='truecolor')
        env['PATH'] = str(Path.home()/'.local/bin') + os.pathsep + env.get('PATH','/usr/bin:/bin')
        # Inherit environment (including DBus) but no commands from preview screenshots.
        term.spawn_async(Vte.PtyFlags.DEFAULT, cwd, ['/bin/zsh', '-i'],
            [k+'='+v for k,v in env.items()], GLib.SpawnFlags.DEFAULT,
            None, None, -1, None, self.spawned, None)
        self.terms.append(term)
        return term

    def spawned(self, term, pid, error, *unused):
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
        self.book.set_current_page(self.book.page_num(page))
        self.book.set_show_tabs(self.book.get_n_pages() > 1)
        page.show_all(); label.show_all()
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
        if isinstance(parent, Gtk.Paned):
            (parent.pack1 if is_first else parent.pack2)(pane, True, False)
        else: parent.pack_start(pane, True, True, 0)
        new = self.make_term(cwd_for(old))
        pane.pack1(old, True, False); pane.pack2(new, True, False)
        pane.show_all()
        def balance():
            size = pane.get_allocated_width() if orientation == Gtk.Orientation.HORIZONTAL else pane.get_allocated_height()
            pane.set_position(max(1, size//2)); return False
        GLib.idle_add(balance)
        self.current = new; new.grab_focus()

    def focus_term(self, term, event):
        self.current = term
        self.title_changed(term)
        return False

    def title_changed(self, term):
        if term == self.current:
            directory = cwd_for(term).replace(str(Path.home()), '~', 1)
            self.set_title('Zsh: '+directory)

    def page_changed(self, book, page, number):
        terms = self.descendants(page)
        if terms:
            self.current = terms[0]
            GLib.idle_add(self.current.grab_focus)

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
        try:
            if term.shell_pid: os.kill(term.shell_pid, signal.SIGHUP)
        except ProcessLookupError: pass

    def exited(self, term, status):
        term.shell_pid = None
        if term not in self.terms: return
        self.terms.remove(term)
        parent = term.get_parent()
        if isinstance(parent, Gtk.Paned):
            sibling = parent.get_child2() if parent.get_child1() == term else parent.get_child1()
            outer = parent.get_parent()
            is_first = isinstance(outer, Gtk.Paned) and outer.get_child1() == parent
            parent.remove(sibling); outer.remove(parent)
            if isinstance(outer, Gtk.Paned): (outer.pack1 if is_first else outer.pack2)(sibling, True, False)
            else: outer.pack_start(sibling, True, True, 0)
            sibling.show_all()
            candidates = self.descendants(sibling)
            if candidates: self.current = candidates[0]; self.current.grab_focus()
        else:
            self.book.remove_page(self.book.page_num(parent))
            self.book.set_show_tabs(self.book.get_n_pages() > 1)
        if not self.terms: self.destroy()

    def search_changed(self, *unused):
        if not self.current: return
        text = self.entry.get_text()
        regex = Vte.Regex.new_for_search(re.escape(text), -1, 0x00000400) if text else None  # PCRE2_MULTILINE
        self.current.search_set_regex(regex, 0)

    def next(self):
        if self.current: self.search_changed(); self.current.search_find_next()

    def previous(self):
        if self.current: self.search_changed(); self.current.search_find_previous()

    def hide_search(self):
        self.search.hide()
        if self.current: self.current.grab_focus()

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
        if alt and not ctrl and key == 't': self.new_tab(); return True
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
            self.split(Gtk.Orientation.HORIZONTAL if key == 'r' else Gtk.Orientation.VERTICAL); return True
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
