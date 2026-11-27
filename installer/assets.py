"""Native Xfwm XPM / GTK CSS assets; no preview screenshot is used as UI."""
import json
import math
from pathlib import Path

import icons

BLUE = '#0AA6F0'
FRAME_BLUE = '#3D98D7'
NAVY = '#041321'
HALO = '#0878D1'
CORNER_SIZE = 20
FRAME_DEPTH = 3
TITLE_HEIGHT = 35
BUTTON_WIDTH = 26
BUTTON_HEIGHT = 23
BUTTON_OFFSET = 8


def mix(foreground, background, amount):
    foreground = bytes.fromhex(foreground[1:])
    background = bytes.fromhex(background[1:])
    result = bytes(round(a * amount + b * (1 - amount)) for a, b in zip(foreground, background))
    return '#' + result.hex().upper()


def panel_svg(width):
    width = max(320, int(width))
    # The low-opacity halo and single solid contour share the same shape.
    edge = f'M1 13.5 L24 37.5 H{width-24} L{width-1} 13.5'
    glow = ''.join(
        f'<path d="{edge}" stroke-width="{size}" opacity="{opacity}"/>'
        for size, opacity in [(8, .045), (5, .08), (2.5, .15)]
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="38" viewBox="0 0 {width} 38" preserveAspectRatio="none">
<path d="M0 0H{width}V13.5L{width-24} 37.5H24L0 13.5Z" fill="#041321" fill-opacity=".94"/>
<g fill="none" style="stroke:#0878D1;stroke-linecap:round;stroke-linejoin:round">{glow}</g>
<path d="{edge}" fill="none" stroke="{BLUE}" stroke-width="1" stroke-linejoin="round" stroke-linecap="round"/>
</svg>'''


def css(panel_path, roles):
    stylesheet = (Path(__file__).with_name('runtime') / 'theme.css').read_text(encoding='utf-8')
    location_icon = panel_path.parents[1] / 'icons/Arch-Blue/scalable/actions/arch-blue-location.svg'
    for key, value in {'PANEL_SVG': panel_path.as_uri(), 'LEFT': roles['left-edge'],
                       'RIGHT': roles['right-edge'], 'MENU_SEPARATOR': roles['menu-separator'],
                       'PAGER': roles['workspaces'], 'CLOCK': roles['clock'],
                       'LOCATION_ICON': location_icon.as_uri()}.items():
        stylesheet = stylesheet.replace(f'@{key}@', str(value))
    return stylesheet


TERMINAL_CSS = (Path(__file__).with_name('runtime') / 'terminal.css').read_bytes()


PICOM = f'''backend = "xrender";
vsync = false;
shadow = true;
shadow-radius = 12;
shadow-opacity = 0.80;
shadow-offset-x = -12;
shadow-offset-y = -12;
shadow-color = "{HALO}";
fading = false;
rules = (
  {{ match = "window_type = 'normal' || window_type = 'dialog'"; corner-radius = 20; opacity = 1.0; blur-background = false; full-shadow = false; }},
  {{ match = "class_g = 'ArchTerminal' || class_g = 'Thunar'"; corner-radius = 0; }},
  {{ match = "!focused && (window_type = 'normal' || window_type = 'dialog')"; shadow-color = "{mix(HALO, '#000000', .9)}"; }},
  {{ match = "window_type = 'dock' || window_type = 'desktop' || window_type *= 'menu'"; shadow = false; corner-radius = 0; }},
  {{ match = "fullscreen"; shadow = false; corner-radius = 0; }}
);
'''


def xpm(width, height, pixel):
    colours = {
        ' ': 'None', '.': NAVY, 'w': '#F1F8FF', 's': '#214764',
        'b': FRAME_BLUE, 'g': mix(HALO, NAVY, .42), 'j': mix(HALO, NAVY, .19),
        'i': mix(FRAME_BLUE, NAVY, .9), 'h': mix(HALO, NAVY, .378), 'k': mix(HALO, NAVY, .171),
    }
    rows = [''.join(pixel(x, y) for x in range(width)) for y in range(height)]
    lines = [f'{width} {height} {len(colours)} 1'] + [f'{k} c {v}' for k, v in colours.items()] + rows
    return '/* XPM */\nstatic char * frame[] = {\n' + ',\n'.join(json.dumps(s) for s in lines) + '\n};\n'


def xfwm_files():
    files = {}
    for state in ['active', 'inactive']:
        stroke = 'bgj' if state == 'active' else 'ihk'
        for n in range(1, 6):
            files[f'title-{n}-{state}.xpm'] = xpm(4, TITLE_HEIGHT, lambda x, y: title_pixel(y, stroke))
        for side in ['left', 'right']:
            files[f'{side}-{state}.xpm'] = xpm(FRAME_DEPTH, 4, lambda x, y: stroke[x if side == 'left' else FRAME_DEPTH-1-x])
            files[f'top-{side}-{state}.xpm'] = xpm(CORNER_SIZE, TITLE_HEIGHT, lambda x, y: corner(x, y, side, False, stroke))
            files[f'bottom-{side}-{state}.xpm'] = xpm(CORNER_SIZE, CORNER_SIZE, lambda x, y: corner(x, y, side, True, stroke))
        files[f'bottom-{state}.xpm'] = xpm(4, CORNER_SIZE, lambda x, y: edge_pixel(CORNER_SIZE-1-y, stroke))
    for name in ['hide', 'maximize', 'close', 'menu', 'stick', 'shade']:
        for state in ['active', 'inactive', 'prelight', 'pressed', 'toggled-active', 'toggled-inactive']:
            def pix(x, y, name=name):
                x += (28 - BUTTON_WIDTH) // 2
                y += (TITLE_HEIGHT - BUTTON_HEIGHT) // 2
                if name == 'close' and 8 <= x <= 20 and (y == x-1 or y == 27-x): return 'w'
                if name == 'hide' and 8 <= x <= 20 and y == 17: return 'w'
                if name == 'maximize' and ((x in [8, 20] and 9 <= y <= 21) or (y in [9, 21] and 8 <= x <= 20)): return 'w'
                if name == 'menu' and 10 <= x <= 18 and y == 13 + abs(x-14): return 'w'
                return '.'
            files[f'{name}-{state}.xpm'] = xpm(BUTTON_WIDTH, BUTTON_HEIGHT, pix)
    files['themerc'] = f'''active_text_color=#FFFFFF
inactive_text_color=#FFFFFF
title_shadow_active=false
title_shadow_inactive=false
title_alignment=left
title_horizontal_offset=9
title_vertical_offset_active=0
title_vertical_offset_inactive=0
button_spacing=2
button_offset={BUTTON_OFFSET}
maximized_offset={BUTTON_OFFSET}
button_layout=O|HMC
show_app_icon=true
full_width_title=true
frame_border_top=1
'''
    return files


def edge_pixel(depth, stroke):
    if depth < 0:
        return ' '
    return stroke[int(depth)] if depth < len(stroke) else '.'


def title_pixel(y, stroke):
    return 's' if y == TITLE_HEIGHT-1 else edge_pixel(y, stroke)


def corner(x, y, side, bottom, stroke):
    centre = CORNER_SIZE - 1
    x = x if side == 'left' else centre-x
    y = centre-y if bottom else y
    if y >= CORNER_SIZE:
        return 's' if y == TITLE_HEIGHT-1 and x >= FRAME_DEPTH else edge_pixel(x, stroke)
    depth = centre + .5 - math.hypot(x-centre, y-centre)
    return edge_pixel(depth, stroke)


def icon_files():
    base = """[Icon Theme]
Name=Arch Blue
Comment=Arch Blue directory icons
Inherits=Papirus-Dark,hicolor
Directories=scalable/places,scalable/apps,scalable/status,scalable/actions

[scalable/places]
Size=48
MinSize=8
MaxSize=512
Type=Scalable
Context=Places

[scalable/apps]
Size=24
MinSize=8
MaxSize=512
Type=Scalable
Context=Applications

[scalable/status]
Size=24
MinSize=8
MaxSize=512
Type=Scalable
Context=Status

[scalable/actions]
Size=24
MinSize=8
MaxSize=512
Type=Scalable
Context=Actions
"""
    folder = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="body" x1="0" x2="0" y1="0" y2="1" gradientUnits="objectBoundingBox"><stop stop-color="#00b6fa"/><stop offset="1" stop-color="#0066c8"/></linearGradient></defs>
<path d="M8 10h17l7 7h24c3 0 5 2 5 5v29c0 3-2 5-5 5H8c-3 0-5-2-5-5V15c0-3 2-5 5-5Z" fill="#70daff"/>
<path d="M4 25c0-2 2-4 4-4h48c3 0 5 2 5 5v25c0 3-2 5-5 5H8c-3 0-5-2-5-5Z" fill="url(#body)"/>
<path d="M8 21h48" stroke="#a5ecff" stroke-opacity=".75" stroke-width="1.1"/>
<g fill="none" stroke="#e6fbff" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">GLYPH</g>
</svg>"""
    glyphs = {
        'folder': '',
        'folder-open': '',
        'folder-documents': '<path d="M26 30h9l4 4v13H26Zm9 0v5h4m-10 3h7m-7 4h7"/>',
        'folder-download': '<path d="M32 29v14m-6-6 6 6 6-6m-14 9v3h16v-3"/>',
        'folder-music': '<path d="M30 43V33l11-3v13m-11-5 11-3"/><ellipse cx="27" cy="44" rx="3" ry="2.5"/><ellipse cx="38" cy="44" rx="3" ry="2.5"/>',
        'folder-pictures': '<rect x="23" y="31" width="19" height="15" rx="2"/><path d="m24 44 5-5 4 3 3-5 5 6"/><circle cx="29" cy="35" r="1.25"/>',
        'folder-videos': '<path d="M28 30v17l13-8.5Z"/>',
        'folder-development': '<path d="m28 33-6 6 6 6m8-12 6 6-6 6m-2-13-4 14"/>',
        'user-desktop': '<rect x="22" y="31" width="20" height="13" rx="1"/><path d="M32 44v4m-6 0h12"/>',
        'user-home': '<path d="m23 38 9-8 9 8m-16-2v11h14V36m-9 11v-6h4v6"/>',
    }
    aliases = {'folder-downloads': 'folder-download', 'folder-video': 'folder-videos',
               'folder-desktop': 'user-desktop', 'folder-projects': 'folder-development'}
    glyphs.update({name: glyphs[target] for name, target in aliases.items()})
    return {'index.theme': base, **icons.files(folder.replace('GLYPH', '')), **{
        f'scalable/places/{name}.svg': folder.replace('GLYPH', shape) for name, shape in glyphs.items()}}
