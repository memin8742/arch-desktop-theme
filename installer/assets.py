"""Native Xfwm XPM / GTK CSS assets; no preview screenshot is used as UI."""
import json
import math
from pathlib import Path

import icons

BLUE = '#0AA6F0'
FRAME_BLUE = '#30C4F6'
FRAME_TOP_BLUE = '#23A5E0'
FRAME_RIGHT_BLUE = '#47C7FB'
FRAME_BOTTOM_BLUE = '#46BEFC'
TITLE_DIVIDER = '#147EC1'
NAVY = '#041321'
HALO = '#0878D1'
CORNER_SIZE = 20
FRAME_DEPTH = 3
TITLE_HEIGHT = 35
BUTTON_WIDTH = 50
BUTTON_HEIGHT = 25
BUTTON_OFFSET = 10
MENU_WIDTH = 26


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


def xpm(width, height, pixel, colours):
    rows = [''.join(pixel(x, y) for x in range(width)) for y in range(height)]
    lines = [f'{width} {height} {len(colours)} 1'] + [f'{k} c {v}' for k, v in colours.items()] + rows
    return '/* XPM */\nstatic char * frame[] = {\n' + ',\n'.join(json.dumps(s) for s in lines) + '\n};\n'


def button_colours(state):
    return {
        'active': ('#041B30', FRAME_TOP_BLUE, '#EDF9FF'),
        'inactive': ('#041827', mix(FRAME_TOP_BLUE, NAVY, .9), '#BCD5E5'),
        'prelight': ('#0A2945', FRAME_RIGHT_BLUE, '#F5FCFF'),
        'pressed': ('#103754', mix('#FFFFFF', FRAME_RIGHT_BLUE, .22), '#FFFFFF'),
    }[state.removeprefix('toggled-')]


def title_button(name, state):
    restore = name == 'maximize' and state.startswith('toggled-')
    fill, edge, glyph = button_colours(state)
    colours = {' ': 'None', 'f': fill, 'e': edge, 'w': glyph,
               'r': mix(edge, NAVY, .5), 'a': mix('#239DEA', fill, .68)}
    centre_x, centre_y = (BUTTON_WIDTH - 1) / 2, (BUTTON_HEIGHT - 1) / 2

    def pixel(x, y):
        # Shear the rounded face while keeping the glyph upright.
        dx, dy = x - centre_x, y - centre_y
        distance = math.hypot(max(abs(dx + .55 * dy) - 13.5, 0), max(abs(dy) - 6, 0))
        if distance > 6: return ' '
        if distance > 5.1: return 'r'
        if distance > 4: return 'e'
        if name == 'close' and max(abs(dx), abs(dy)) <= 5.5:
            diagonal = abs(abs(dx) - abs(dy))
            if diagonal <= .5: return 'w'
            if diagonal <= 1.5: return 'a'
        elif name == 'hide' and abs(dx) <= 5.5:
            if dy == 0: return 'w'
            if abs(dy) == 1: return 'a'
        elif restore:
            if 19 <= x <= 27 and 11 <= y <= 18 and (x in (19, 27) or y in (11, 18)):
                return 'w'
            if (y == 7 and 23 <= x <= 30) or (x == 30 and 7 <= y <= 14):
                return 'w'
        elif name == 'maximize':
            edge_distance = max(abs(dx), abs(dy))
            if 4 <= edge_distance <= 5: return 'w'
            if 3.5 <= edge_distance <= 6: return 'a'
        return 'f'

    return xpm(BUTTON_WIDTH, BUTTON_HEIGHT, pixel, colours)


def title_button_svg(name, state):
    fill, edge, glyph = button_colours(state)
    restore = name == 'maximize' and state.startswith('toggled-')
    symbol = {
        'hide': 'M19.5 13h11',
        'maximize': 'M20.6 8.1h8.8q.8 0 .8.8v7.2q0 .8-.8.8h-8.8q-.8 0-.8-.8V8.9q0-.8.8-.8Z',
        'restore': 'M22.8 9V7.5h7.7v7h-1.7 M19.6 10.4h7.6v7h-7.6Z',
        'close': 'M21.2 8.7l7.6 7.6m0-7.6-7.6 7.6',
    }['restore' if restore else name]
    face = ('M15.4 2.7H43.8Q48.1 2.7 46.1 6.5L38.8 20Q37.5 22.3 34.6 22.3'
            'H6.2Q1.9 22.3 3.9 18.5L11.2 5Q12.5 2.7 15.4 2.7Z')
    pressed = state.endswith('pressed')
    face_top = mix(edge, fill, .09 if pressed else .17)
    face_bottom = mix(NAVY, fill, .35)
    rim_bottom = mix(edge, fill, .38)
    # Xfwm composites this tile over its XPM fallback. Cover the fallback so the
    # antialiased diagonal edges blend with the surrounding title bar only once.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{BUTTON_WIDTH}" height="{BUTTON_HEIGHT}" viewBox="0 0 50 25">
<defs>
  <linearGradient id="face" x2="0" y2="1" gradientUnits="objectBoundingBox">
    <stop stop-color="{face_top}"/><stop offset=".55" stop-color="{fill}"/><stop offset="1" stop-color="{face_bottom}"/>
  </linearGradient>
  <linearGradient id="rim" x1=".15" y1="0" x2=".85" y2="1" gradientUnits="objectBoundingBox">
    <stop stop-color="{edge}"/><stop offset=".5" stop-color="{mix(edge, fill, .66)}"/><stop offset="1" stop-color="{rim_bottom}"/>
  </linearGradient>
</defs>
<rect width="50" height="25" fill="{NAVY}"/>
<path d="{face}" transform="translate(0 1)" fill="none" stroke="#010b18" stroke-width="2"/>
<path d="{face}" fill="url(#face)" stroke="url(#rim)" stroke-width="1.15"/>
<path d="M15.6 4.3h26.7" fill="none" stroke="{edge}" stroke-opacity=".20" stroke-linecap="round"/>
<g transform="translate(0 {1 if pressed else 0})" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <path d="{symbol}" transform="translate(0 .6)" stroke="#010c18" stroke-width="2.45"/>
  <path d="{symbol}" stroke="{glyph}" stroke-width="1.6"/>
</g></svg>'''


def frame_stroke(contour, strength):
    return {key: mix(colour, NAVY, amount * strength)
            for key, colour, amount in [('b', contour, 1), ('g', HALO, .42), ('j', HALO, .19)]}


def title_pixel(y, raised=False):
    if y == TITLE_HEIGHT - 1:
        return 's'
    if y < FRAME_DEPTH:
        return 'bgj'[y]
    if raised:
        if y <= 5: return 't'
        if y <= 9: return 'u'
        return 'n'
    return '.'


def title_accent_pixel(x, y):
    if y < FRAME_DEPTH or y == TITLE_HEIGHT - 1:
        return title_pixel(y)
    offset = x - (49 + .61 * (TITLE_HEIGHT - 2 - y))
    if abs(offset) <= .9: return 'm'
    if abs(offset) <= 2.2: return 'a'
    if abs(offset) <= 5: return 'q'
    return title_pixel(y, raised=offset < 0)


def xfwm_files():
    files = {}
    base = {' ': 'None', '.': NAVY, 'w': '#F1F8FF'}
    title_palettes = {}
    for state, strength in [('active', 1), ('inactive', .9)]:
        top_stroke = frame_stroke(FRAME_TOP_BLUE, strength)
        bottom_stroke = frame_stroke(FRAME_BOTTOM_BLUE, strength)
        title = {**base, **top_stroke, 's': mix(TITLE_DIVIDER, NAVY, strength)}
        accents = {'t': '#063C60', 'u': '#062948', 'n': '#041B2E',
                   'm': '#0EEBFC', 'a': '#087FAD', 'q': '#063452'}
        title.update({key: mix(colour, NAVY, strength) for key, colour in accents.items()})
        title_palettes[state] = title
        for n in range(1, 6):
            pixel = title_accent_pixel if n == 4 else lambda x, y: title_pixel(y, raised=n < 4)
            files[f'title-{n}-{state}.xpm'] = xpm(76 if n == 4 else 4, TITLE_HEIGHT, pixel, title)
        for side, contour in [('left', FRAME_BLUE), ('right', FRAME_RIGHT_BLUE)]:
            side_stroke = frame_stroke(contour, strength)
            files[f'{side}-{state}.xpm'] = xpm(FRAME_DEPTH, 4, lambda x, y: 'bgj'[x if side == 'left' else FRAME_DEPTH-1-x],
                                               {**base, **side_stroke})
            caps = [(False, TITLE_HEIGHT, title), (True, CORNER_SIZE, {**base, **bottom_stroke})]
            for bottom, height, palette in caps:
                cap = 'bottom' if bottom else 'top'
                palette = {**palette, **{key.upper(): colour for key, colour in side_stroke.items()}}
                files[f'{cap}-{side}-{state}.xpm'] = xpm(
                    CORNER_SIZE, height, lambda x, y: corner_pixel(x, y, side, bottom), palette)
        files[f'bottom-{state}.xpm'] = xpm(4, CORNER_SIZE, lambda x, y: edge_pixel(CORNER_SIZE-1-y, 'bgj'),
                                          {**base, **bottom_stroke})
    for name in ['hide', 'maximize', 'close', 'menu', 'stick', 'shade']:
        states = ['active', 'inactive', 'prelight', 'pressed', 'toggled-active', 'toggled-inactive']
        if name == 'maximize': states += ['toggled-prelight', 'toggled-pressed']
        for state in states:
            if name in ('hide', 'maximize', 'close'):
                files[f'{name}-{state}.xpm'] = title_button(name, state)
                files[f'{name}-{state}.svg'] = title_button_svg(name, state)
                continue
            def pix(x, y, name=name):
                x += (28 - MENU_WIDTH) // 2
                y += (TITLE_HEIGHT - BUTTON_HEIGHT) // 2
                if name == 'menu':
                    if 10 <= x <= 18 and y == 13 + abs(x-14): return 'w'
                    # Xfwm's application icon is clipped by the menu pixmap's mask.
                    return title_pixel(y, raised=True)
                return ' '
            palette = title_palettes['inactive' if state.endswith('inactive') else 'active']
            files[f'{name}-{state}.xpm'] = xpm(MENU_WIDTH, BUTTON_HEIGHT, pix, palette)
    files['themerc'] = f'''active_text_color=#FFFFFF
inactive_text_color=#FFFFFF
title_shadow_active=false
title_shadow_inactive=false
title_alignment=left
title_horizontal_offset=9
title_vertical_offset_active=0
title_vertical_offset_inactive=0
button_spacing=3
button_offset={BUTTON_OFFSET}
maximized_offset={BUTTON_OFFSET}
button_layout=O|HMC
show_app_icon=true
full_width_title=false
frame_border_top=1
'''
    return files


def edge_pixel(depth, stroke):
    if depth < 0:
        return ' '
    return stroke[int(depth)] if depth < len(stroke) else '.'


def corner(x, y, side, bottom, stroke):
    centre = CORNER_SIZE - 1
    x = x if side == 'left' else centre-x
    y = centre-y if bottom else y
    if y >= CORNER_SIZE:
        return 's' if y == TITLE_HEIGHT-1 and x >= FRAME_DEPTH else edge_pixel(x, stroke)
    depth = centre + .5 - math.hypot(x-centre, y-centre)
    return edge_pixel(depth, stroke)


def corner_pixel(x, y, side, bottom):
    pixel = corner(x, y, side, bottom, 'bgj')
    inset_x = x if side == 'left' else CORNER_SIZE - 1 - x
    inset_y = CORNER_SIZE - 1 - y if bottom else y
    if pixel in 'bgj' and inset_x < inset_y:
        return pixel.upper()
    if pixel == '.' and not bottom and side == 'left':
        return title_pixel(y, raised=True)
    return pixel


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
