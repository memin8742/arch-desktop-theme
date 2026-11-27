"""Hand-drawn Arch Blue glyphs for the native panel and Thunar controls."""

ICE = '#EDF6FE'
CYAN = '#00DAF1'
SYMBOLIC = '#bebebe'


def outline(body, colour=ICE, width=1.55):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
<g fill="none" stroke="{colour}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">
{body}
</g></svg>
'''


def symbolic(body):
    # GTK recolours symbolic fills. Cutouts remain open under that recolouring.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
<g fill="{SYMBOLIC}" fill-rule="evenodd">{body}</g>
</svg>
'''


GEAR = '''<path d="M10 2.7h4l.6 2.6 1.2.5 2.2-1.4 2.8 2.8-1.4 2.2.5 1.2 2.4.6v3.6l-2.4.6-.5 1.2 1.4 2.2-2.8 2.8-2.2-1.4-1.2.5-.6 2.4h-4l-.6-2.4-1.2-.5L6 21.8 3.2 19l1.4-2.2-.5-1.2-2.4-.6v-3.6l2.4-.6.5-1.2-1.4-2.2L6 4.6l2.2 1.4 1.2-.5z" transform="translate(1 0) scale(.91)"/>
<circle cx="12" cy="12" r="3.1"/>'''
CLIPBOARD = '''<path d="M9 5H6a2 2 0 0 0-2 2v13a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7a2 2 0 0 0-2-2h-3"/>
<path d="M9 3.5h6v4H9zm-1 12.5 2.5 2.2L17 12"/>'''
BELL = '''<path d="M12 2a7 7 0 0 1 7 7v4.3l2.4 3.9v1.3H2.6v-1.3L5 13.3V9a7 7 0 0 1 7-7zm0 1.6A5.4 5.4 0 0 0 6.6 9v4.8l-1.9 3.1h14.6l-1.9-3.1V9A5.4 5.4 0 0 0 12 3.6z"/>
<path d="M8.9 19.4h1.6a1.5 1.5 0 0 0 3 0h1.6a3.1 3.1 0 0 1-6.2 0z"/>'''
SPEAKER = '<path d="M1.8 8.4h4l5.8-4.8v16.8l-5.8-4.8h-4zm1.5 1.5v4.2h3l3.8 3.1V6.8L6.3 9.9z"/>'
WAVE_NEAR = '<path d="m13.6 8.6 1-1a6.3 6.3 0 0 1 0 8.8l-1-1a4.9 4.9 0 0 0 0-6.8z"/>'
WAVE_MIDDLE = '<path d="m15.8 6.5 1-1a9.4 9.4 0 0 1 0 13l-1-1a8 8 0 0 0 0-11z"/>'
WAVE_FAR = '<path d="m18 4.4 1-1a12.4 12.4 0 0 1 0 17.2l-1-1a11 11 0 0 0 0-15.2z"/>'
SOUND_WAVES = (
    '<path d="m14 9 2.3 2.3L18.6 9l1 1-2.3 2.3 2.3 2.3-1 1-2.3-2.3L14 15.6l-1-1 2.3-2.3L13 10z"/>',
    WAVE_NEAR,
    WAVE_NEAR + WAVE_MIDDLE,
    WAVE_NEAR + WAVE_MIDDLE + WAVE_FAR,
)
HOME = '<path d="m3 11 9-8 9 8m-16-1v10h5v-6h4v6h5V10"/>'
SEARCH = '<circle cx="10.7" cy="10.7" r="5.3"/><path d="m14.8 14.8 4.4 4.4"/>'
FOLDER = '<path d="M3 6h6l2 2h9a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>'


def files(folder_icon):
    panel = {
        'arch-blue-system': outline(GEAR, CYAN),
        'arch-blue-clipboard': outline(CLIPBOARD),
        'arch-blue-wired': outline(
            '<path d="M4 5h16v11h-3l-2 3H9l-2-3H4zM8 5v4m4-4v4m4-4v4"/>'),
        'arch-blue-wifi': outline(
            '<path d="M3 8a14 14 0 0 1 18 0m-15 3a9.4 9.4 0 0 1 12 0m-9 3a4.8 4.8 0 0 1 6 0"/><circle cx="12" cy="17.5" r=".65"/>'),
    }
    status = {}
    for plural in ('notification', 'notifications'):
        for variant in ('', '-new', '-disabled', '-new-disabled', '-disabled-new'):
            glyph = BELL
            if 'disabled' in variant:
                glyph += '<path d="m3.1 4.1 1-1 16.8 16.8-1 1z"/>'
            if 'new' in variant:
                glyph += '<circle cx="20" cy="4" r="1.5"/>'
            status[f'{plural}{variant}-symbolic'] = symbolic(glyph)
    for level, waves in zip(('muted', 'low', 'medium', 'high'), SOUND_WAVES):
        status[f'audio-volume-{level}-symbolic'] = symbolic(SPEAKER + waves)

    toolbar = {
        'go-previous': '<path d="M20 12H4m7-7-7 7 7 7"/>',
        'go-next': '<path d="M4 12h16m-7-7 7 7-7 7"/>',
        'go-up': '<path d="M12 20V4M5 11l7-7 7 7"/>',
        'go-home': HOME,
        'edit-find': SEARCH,
        'arch-blue-location': FOLDER,
    }
    actions = {}
    for name, glyph in toolbar.items():
        actions[name] = outline(glyph, CYAN if name in ('go-home', 'arch-blue-location') else ICE, 1.3)
        if not name.startswith('arch-blue-'):
            actions[name + '-symbolic'] = outline(glyph, SYMBOLIC, 1.4)
    return {
        **{f'scalable/apps/{name}.svg': svg for name, svg in panel.items()},
        'scalable/apps/org.xfce.thunar.svg': folder_icon,
        **{f'scalable/status/{name}.svg': svg for name, svg in status.items()},
        **{f'scalable/actions/{name}.svg': svg for name, svg in actions.items()},
    }
