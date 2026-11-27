#!/usr/bin/env python3
import subprocess
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk

window = Gtk.Window(title='Ağ bağlantıları')
window.set_default_size(420, 250)
window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
window.connect('destroy', Gtk.main_quit)
area = Gtk.ScrolledWindow()
window.add(area)
label = Gtk.Label(xalign=0, yalign=0, selectable=True, margin=15)
result = subprocess.run(
    ['nmcli', '-f', 'GENERAL.DEVICE,GENERAL.TYPE,GENERAL.STATE,IP4.ADDRESS,IP6.ADDRESS', 'device', 'show'],
    capture_output=True, text=True, check=False,
)
label.set_text(result.stdout.strip() or result.stderr.strip() or 'Ağ bağlantısı bilgisi bulunamadı.')
area.add(label)
window.show_all()
Gtk.main()
