"""Host-independent tests: transaction safety, rollback, geometry, real sensor fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import assets
import install
import helper


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def test_merge_is_idempotent_and_preserves_user(self):
        text = 'export EDITOR=nano\n'
        once = install.merge_block(text, 'source theme.zsh')
        twice = install.merge_block(once, 'source theme.zsh')
        self.assertEqual(once, twice)
        self.assertIn('export EDITOR=nano', twice)
        with self.assertRaises(ValueError): install.merge_block(install.BEGIN, 'x')

    def test_transaction_restores_bytes_and_removes_only_new_files(self):
        old = self.home / '.config/test.conf'
        old.parent.mkdir(); old.write_bytes(b'original\x00bytes')
        tx = install.Transaction(self.home)
        tx.write(old, b'new')
        added = self.home / '.local/theme.txt'
        tx.write(added, b'added')
        tx.finish()
        install.restore(tx.backup, self.home, settings=False)
        self.assertEqual(old.read_bytes(), b'original\x00bytes')
        self.assertFalse(added.exists())

    def test_restore_does_not_erase_later_user_changes(self):
        tx = install.Transaction(self.home)
        target = self.home/'keep.txt'
        tx.write(target, 'installer')
        target.write_text('user change')
        self.assertEqual(install.restore(tx.backup,self.home,settings=False),['keep.txt'])
        self.assertEqual(target.read_text(),'user change')

    def test_repeated_write_rolls_back_to_first_original(self):
        target=self.home/'twice'; target.write_text('original')
        tx=install.Transaction(self.home)
        tx.write(target,'one'); tx.write(target,'two')
        install.restore(tx.backup,self.home,settings=False)
        self.assertEqual(target.read_text(),'original')

    def test_path_escape_and_wrong_home_rejected(self):
        tx=install.Transaction(self.home)
        with self.assertRaises(ValueError): tx.write(self.home/'../outside',b'bad')
        with self.assertRaises(ValueError): tx.write(self.home,b'bad')
        with self.assertRaises(ValueError): install.restore(self.home,self.home,settings=False)

    def test_symlink_not_followed(self):
        dest=self.home/'destination'; dest.mkdir()
        link=self.home/'linked'
        try: link.symlink_to(dest,target_is_directory=True)
        except OSError: self.skipTest('Host symlink privilege unavailable')
        tx=install.Transaction(self.home)
        with self.assertRaises(ValueError): tx.write(link/'test',b'bad')
        self.assertFalse((dest/'test').exists())

    def test_xfconf_journal_precedes_failed_mutation(self):
        tx=install.Transaction(self.home)
        def fake(args, check=True):
            if '-s' in args: raise RuntimeError('injected failure')
            return subprocess.CompletedProcess(args,0,'before\n','')
        with patch.object(install,'run',fake):
            with self.assertRaises(RuntimeError): tx.xf('xfwm4','/test','string','after')
        journal=json.loads((tx.backup/'backup.json').read_text())
        self.assertEqual(journal['settings'][0]['old'],'before')

    def test_panel_is_one_constant_colour_path_at_multiple_sizes(self):
        for width in [1280,1920,2560,3840]:
            root=ET.fromstring(assets.panel_svg(width))
            outlines=[n for n in root if n.get('stroke')]
            self.assertEqual(len(outlines),1)
            self.assertEqual(outlines[0].get('stroke'),'#0AA6F0')
            self.assertIn(str(width-24),outlines[0].get('d'))
            self.assertNotIn('gradient',assets.panel_svg(width).lower())

    def test_native_assets_are_valid_xpm(self):
        files=assets.xfwm_files()
        self.assertIn('close-active.xpm',files)
        for name,text in files.items():
            if not name.endswith('.xpm'): continue
            lines=[json.loads(row.rstrip(',')) for row in text.splitlines()[2:-1]]
            w,h,n,cpp=map(int,lines[0].split())
            self.assertEqual(cpp,1)
            self.assertEqual(len(lines[1+n:]),h,name)
            self.assertTrue(all(len(s)==w for s in lines[1+n:]),name)

    def test_transparency_is_local_not_whole_window(self):
        self.assertNotIn('inactive-opacity',assets.PICOM)
        self.assertNotRegex(assets.PICOM, r'(?<![\w-])opacity\s*=\s*0\.8')
        self.assertIn('opacity = 1.0',assets.PICOM)
        self.assertIn('rgba(73,174,230,0.4)',assets.TERMINAL_CSS.decode())
        self.assertNotIn('triangle',assets.TERMINAL_CSS.decode())

    def test_frame_contour_and_inactive_halo_have_separate_colours(self):
        frames = assets.xfwm_files()
        self.assertIn('"b c #3D98D7"', frames['title-1-active.xpm'])
        for state, stroke in [('active', 'bgj'), ('inactive', 'ihk')]:
            title = [json.loads(line.rstrip(',')) for line in frames[f'title-1-{state}.xpm'].splitlines()[2:-1]]
            width, _, palette, _ = map(int, title[0].split())
            self.assertEqual(title[1+palette:4+palette], [pixel*width for pixel in stroke])
        self.assertIn('shadow-color = "#0878D1"', assets.PICOM)
        self.assertIn('shadow-color = "#076CBC"', assets.PICOM)

    def test_title_buttons_fit_inside_corners(self):
        frames = assets.xfwm_files()
        for state, stroke in [('active', 'bgj'), ('inactive', 'ihk')]:
            left = assets.FRAME_DEPTH + assets.BUTTON_OFFSET
            top = (assets.TITLE_HEIGHT - assets.BUTTON_HEIGHT + 1) // 2
            for y in range(top, top + assets.BUTTON_HEIGHT):
                self.assertEqual(assets.corner(left, y, 'left', False, stroke), '.')
                self.assertEqual(assets.corner(assets.CORNER_SIZE - 1 - left, y, 'right', False, stroke), '.')
        self.assertIn(f'button_offset={assets.BUTTON_OFFSET}\n', frames['themerc'])
        for state in ('active', 'inactive', 'prelight', 'pressed'):
            self.assertNotEqual(frames[f'maximize-{state}.xpm'], frames[f'maximize-toggled-{state}.xpm'])
        self.assertIn('#4CA4D5', frames['hide-prelight.xpm'])
        self.assertIn('#AD647A', frames['close-prelight.xpm'])

    def test_panel_and_toolbar_icon_names_are_present(self):
        files = assets.icon_files()
        for name in ['apps/arch-blue-system', 'apps/arch-blue-clipboard', 'apps/org.xfce.thunar',
                     'status/audio-volume-high-symbolic', 'status/notification-symbolic',
                     'actions/go-previous', 'actions/go-home', 'actions/arch-blue-location']:
            self.assertEqual(ET.fromstring(files[f'scalable/{name}.svg']).tag,
                             '{http://www.w3.org/2000/svg}svg')

    def test_missing_sensor_is_not_fabricated_zero(self):
        root=self.home/'sys'; (root/'class').mkdir(parents=True)
        self.assertEqual(helper.hardware(root),[])
        hw=root/'class/hwmon/hwmon0'; hw.mkdir(parents=True)
        (hw/'name').write_text('cpu_sensor')
        (hw/'temp1_input').write_text('42500')
        (hw/'temp1_label').write_text('CPU package')
        self.assertEqual(helper.hardware(root),[('cpu_sensor / CPU package','42.5 °C')])

    def test_failed_feature_is_reported_not_marked_done(self):
        rows=install.feature_report()
        self.assertTrue(any(r['status']=='configured' and 'Thunar %80' in r['feature'] for r in rows))
        self.assertTrue(any(r['status']=='pending' and 'Batarya' in r['feature'] for r in rows))


if __name__=='__main__': unittest.main()
