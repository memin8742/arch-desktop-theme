"""Native Xfwm XPM / GTK CSS assets; no preview screenshot is used as UI."""
import json
import math

BLUE = '#0AA6F0'
NAVY = '#041321'
PROMPT = '#49AEE6'


def panel_svg(width):
    width = max(320, int(width))
    # One path, one stroke, one colour, no gradient, independent of DPI.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="38" viewBox="0 0 {width} 38">
<path d="M0 0H{width}V14L{width-24} 37H24L0 14Z" fill="#041321" fill-opacity="0.98"/>
<path d="M0 14L24 37H{width-24}L{width} 14" fill="none" stroke="{BLUE}" stroke-width="1" stroke-linejoin="round"/>
</svg>'''


def css(panel_path):
    uri = panel_path.as_uri()
    return f'''/* Arch Theme: colours apply to backgrounds, never widget opacity. */
.xfce4-panel {{ background-color: transparent; background-image: url("{uri}"); background-size: 100% 100%; border: none; box-shadow: none; }}
.xfce4-panel button {{ color: #FFFFFF; background: transparent; border: 1px solid transparent; box-shadow: none; padding: 2px 6px; }}
.xfce4-panel button:checked {{ background: #073154; border-color: {BLUE}; border-radius: 5px; }}
.xfce4-panel .tasklist {{ -XfceTasklist-min-button-length: 32; -XfceTasklist-max-button-length: 36; }}
.thunar, .thunar window, .thunar .standard-view, .thunar treeview, .thunar scrolledwindow, .thunar viewport {{ background-color: {NAVY}; color: #FFFFFF; }}
.thunar menubar, .thunar toolbar, .thunar statusbar {{ background: {NAVY}; border-color: #125279; }}
.thunar :selected {{ background-color: #0A4166; color: #FFFFFF; }}
.thunar entry {{ background: #061C2C; border: 1px solid #125279; color: #FFFFFF; }}
'''


TERMINAL_CSS = b'''
window.arch-terminal, .arch-root, .arch-terminal notebook, .arch-terminal notebook > stack,
.arch-terminal paned, .arch-terminal box { background-color: transparent; background-image: none; }
.arch-terminal paned > separator { min-width: 2px; min-height: 2px; background: rgba(73,174,230,0.4); margin: 0; padding: 0; border: none; box-shadow: none; }
.arch-terminal notebook header, .arch-terminal .search-bar { background: #041321; color: white; }
.arch-terminal notebook tab { background: #041321; color: #49AEE6; padding: 4px 10px; }
'''


PICOM = '''backend = "glx";
vsync = true;
shadow = true;
shadow-radius = 12;
shadow-opacity = 0.65;
shadow-offset-x = -12;
shadow-offset-y = -12;
shadow-color = "#0878D1";
fading = false;
rules = (
  { match = "window_type = 'normal' || window_type = 'dialog'"; corner-radius = 16; opacity = 1.0; blur-background = false; },
  { match = "window_type = 'dock' || window_type = 'desktop' || window_type *= 'menu'"; shadow = false; corner-radius = 0; },
  { match = "fullscreen"; shadow = false; corner-radius = 0; }
);
'''


def xpm(width, height, pixel):
    colours = {' ': 'None', '.': NAVY, 'b': BLUE, 'i': '#0997DC', 'w': '#FFFFFF'}
    rows = [''.join(pixel(x, y) for x in range(width)) for y in range(height)]
    lines = [f'{width} {height} {len(colours)} 1'] + [f'{k} c {v}' for k, v in colours.items()] + rows
    return '/* XPM */\nstatic char * frame[] = {\n' + ',\n'.join(json.dumps(s) for s in lines) + '\n};\n'


def xfwm_files():
    files = {}
    for state in ['active', 'inactive']:
        ink = 'b' if state == 'active' else 'i'
        for n in range(1, 6):
            files[f'title-{n}-{state}.xpm'] = xpm(4, 32, lambda x, y: ink if y == 0 else '.')
        for side in ['left', 'right']:
            files[f'{side}-{state}.xpm'] = xpm(1, 4, lambda x, y: ink)
            files[f'top-{side}-{state}.xpm'] = xpm(16, 32, lambda x, y, side=side: corner(x, y, side, False, ink))
            files[f'bottom-{side}-{state}.xpm'] = xpm(16, 16, lambda x, y, side=side: corner(x, y, side, True, ink))
        files[f'bottom-{state}.xpm'] = xpm(4, 16, lambda x, y: ink if y == 15 else '.')
    for name in ['hide', 'maximize', 'close', 'menu', 'stick', 'shade']:
        for state in ['active', 'inactive', 'prelight', 'pressed', 'toggled-active', 'toggled-inactive']:
            def pix(x, y, name=name, state=state):
                if name == 'close' and 8 <= x <= 20 and (y == x-1 or y == 27-x): return 'w'
                if name == 'hide' and 8 <= x <= 20 and y == 17: return 'w'
                if name == 'maximize' and ((x in [8, 20] and 9 <= y <= 21) or (y in [9, 21] and 8 <= x <= 20)): return 'w'
                if name == 'menu' and 10 <= x <= 18 and y == 13 + abs(x-14): return 'w'
                return ('i' if 'inactive' in state else 'b') if y == 0 else '.'
            files[f'{name}-{state}.xpm'] = xpm(28, 32, pix)
    files['themerc'] = '''active_text_color=#FFFFFF
inactive_text_color=#FFFFFF
title_shadow_active=false
title_shadow_inactive=false
title_alignment=left
title_horizontal_offset=8
title_vertical_offset_active=0
title_vertical_offset_inactive=0
button_spacing=2
button_offset=0
button_layout=O|HMC
show_app_icon=true
full_width_title=true
frame_border_top=1
'''
    return files


def corner(x, y, side, bottom, ink):
    x = x if side == 'left' else 15-x
    y = 15-y if bottom else y
    if y >= 16: return ink if x == 0 else '.'
    distance = math.hypot(x-15, y-15)
    if distance > 16: return ' '
    return ink if distance >= 15 else '.'
