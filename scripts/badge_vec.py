"""
Shared SVG vectorization helpers for badge scripts.

Converts <text> SVG elements to <path> Bézier curves using FreeType,
so rendered badges are font-independent.

Requirements: freetype-py  (pip install freetype-py)
              Roboto fonts in /usr/share/fonts/truetype/roboto/
"""

import math
import os

import freetype

# ── Fonts ───────────────────────────────────────────────────────────────────
# Look in project fonts/ first, fall back to system paths
_FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

def _font(name, system_path):
    local = os.path.join(_FONTS_DIR, name)
    return local if os.path.exists(local) else system_path

ROBOTO_MEDIUM = _font("Roboto-Medium.ttf", "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf")
ROBOTO_LIGHT = _font("Roboto-Light.ttf", "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Light.ttf")

# ── Layout constants ────────────────────────────────────────────────────────
PAD_L = 4
PAD_R = 3
DD_ICON_W = 11
DD_GAP = 3
SPK_ICON_W = 10
SPK_GAP = 3
FONT_SIZE = 9
SVG_H = 14
Y_BASELINE = 10.5

# ── SVG icon templates ──────────────────────────────────────────────────────

DD_ICON = '''<g transform="translate({x}, 3)">
    <path d="M0,0 L2.2,0 A3.0,4.0 0 0 1 2.2,8 L0,8 Z" fill="white"/>
    <path d="M11,0 L8.8,0 A3.0,4.0 0 0 0 8.8,8 L11,8 Z" fill="white"/>
  </g>'''

SPEAKER_ICON = '''<g transform="translate({x}, 2)">
    <path d="M0.6,3.6 L0.6,6.2 L2.1,6.2 L4.3,8.2 L4.3,1.5 L2.1,3.6 Z" fill="white" stroke="white" stroke-width="0.25" stroke-linejoin="round"/>
    <path d="M6.2,3.2 A2.1,2.1 0 0 1 6.2,6.8" fill="none" stroke="white" stroke-width="1.0" stroke-linecap="round"/>
    <path d="M8.0,1.7 A3.7,3.7 0 0 1 8.0,8.3" fill="none" stroke="white" stroke-width="1.0" stroke-linecap="round"/>
  </g>'''

DISC_ICON_W = 10
DISC_ICON = '''<g transform="translate({x}, 2)">
    <circle cx="5" cy="5" r="4.2" fill="none" stroke="white" stroke-width="1.0"/>
    <circle cx="5" cy="5" r="1.2" fill="white"/>
  </g>'''

GLOBE_ICON_W = 10
GLOBE_ICON = '''<g transform="translate({x}, 2)">
    <circle cx="5" cy="5" r="4.0" fill="none" stroke="white" stroke-width="0.9"/>
    <ellipse cx="5" cy="5" rx="2.0" ry="4.0" fill="none" stroke="white" stroke-width="0.7"/>
    <line x1="1" y1="5" x2="9" y2="5" stroke="white" stroke-width="0.7"/>
  </g>'''

TV_ICON_W = 10
TV_ICON = '''<g transform="translate({x}, 2)">
    <rect x="0.8" y="1" width="8.4" height="6" rx="0.8" fill="none" stroke="white" stroke-width="0.9"/>
    <line x1="3.5" y1="8.5" x2="6.5" y2="8.5" stroke="white" stroke-width="0.9" stroke-linecap="round"/>
    <line x1="5" y1="7" x2="5" y2="8.5" stroke="white" stroke-width="0.9" stroke-linecap="round"/>
  </g>'''

DVD_ICON_W = 10
DVD_ICON = '''<g transform="translate({x}, 2)">
    <circle cx="5" cy="5" r="4.2" fill="none" stroke="white" stroke-width="0.8"/>
    <circle cx="5" cy="5" r="2.2" fill="none" stroke="white" stroke-width="0.6"/>
    <circle cx="5" cy="5" r="0.8" fill="white"/>
  </g>'''

CAMERA_ICON_W = 10
CAMERA_ICON = '''<g transform="translate({x}, 2)">
    <rect x="1" y="3" width="8" height="5.5" rx="0.8" fill="none" stroke="white" stroke-width="0.9"/>
    <circle cx="5" cy="5.8" r="1.5" fill="none" stroke="white" stroke-width="0.8"/>
    <rect x="3.5" y="1.8" width="3" height="1.5" rx="0.5" fill="none" stroke="white" stroke-width="0.7"/>
  </g>'''

IMAX_ICON_W = 42


# ── FreeType helpers ────────────────────────────────────────────────────────

def ft_advance(ttf_path, text):
    face = freetype.Face(ttf_path)
    face.set_char_size(0, FONT_SIZE * 64, 72, 72)
    w = 0
    for ch in text:
        face.load_char(ch, freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
        w += face.glyph.advance.x / 64.0
    return w


def ft_to_path_d(ttf_path, text, x_offset=0):
    """Convert text to SVG path `d` attribute using FreeType glyph outlines."""
    face = freetype.Face(ttf_path)
    face.set_char_size(0, FONT_SIZE * 64, 72, 72)
    parts = []
    pen_x = x_offset
    for ch in text:
        face.load_char(ch, freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
        outline = face.glyph.outline
        points, tags, contours = outline.points, outline.tags, outline.contours
        start = 0
        for ce in contours:
            cp = points[start : ce + 1]
            ct = tags[start : ce + 1]
            n = len(cp)
            if n == 0:
                start = ce + 1
                continue

            def tx(p):
                return (pen_x + p[0] / 64.0, Y_BASELINE - p[1] / 64.0)

            fo = next((i for i in range(n) if ct[i] & 1), None)
            if fo is None:
                p0, p1 = tx(cp[0]), tx(cp[1])
                parts.append(f"M{(p0[0]+p1[0])/2:.2f},{(p0[1]+p1[1])/2:.2f}")
                fo = -1
            else:
                p = tx(cp[fo])
                parts.append(f"M{p[0]:.2f},{p[1]:.2f}")
            i = 0
            while i < n:
                ci = (fo + 1 + i) % n if fo >= 0 else i % n
                pt = tx(cp[ci])
                tag = ct[ci]
                if tag & 1:
                    parts.append(f"L{pt[0]:.2f},{pt[1]:.2f}")
                    i += 1
                else:
                    ni = (ci + 1) % n
                    npt = tx(cp[ni])
                    ntag = ct[ni]
                    if ntag & 1:
                        parts.append(
                            f"Q{pt[0]:.2f},{pt[1]:.2f} {npt[0]:.2f},{npt[1]:.2f}"
                        )
                        i += 2
                    else:
                        mid = ((pt[0] + npt[0]) / 2, (pt[1] + npt[1]) / 2)
                        parts.append(
                            f"Q{pt[0]:.2f},{pt[1]:.2f} {mid[0]:.2f},{mid[1]:.2f}"
                        )
                        i += 1
            parts.append("Z")
            start = ce + 1
        pen_x += face.glyph.advance.x / 64.0
    return " ".join(parts), pen_x - x_offset


def even_ceil(v):
    v = math.ceil(v)
    return v + 1 if v % 2 else v


# ── Vectorized SVG builders ────────────────────────────────────────────────

def vec_text_only(label):
    d, adv = ft_to_path_d(ROBOTO_MEDIUM, label, PAD_L)
    w = even_ceil(PAD_L + adv + PAD_R)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  <path d="{d}" fill="white"/>\n</svg>\n'
    )


def vec_dolby(medium_text, light_text=None):
    ix = PAD_L
    tx = ix + DD_ICON_W + DD_GAP
    md, m_adv = ft_to_path_d(ROBOTO_MEDIUM, medium_text, tx)
    icon = DD_ICON.format(x=ix)
    if light_text:
        lx = tx + m_adv + 3
        ld, l_adv = ft_to_path_d(ROBOTO_LIGHT, light_text, lx)
        w = even_ceil(lx + l_adv + PAD_R)
        paths = f'<path d="{md}" fill="white"/>\n  <path d="{ld}" fill="white" fill-opacity="0.92"/>'
    else:
        w = even_ceil(tx + m_adv + PAD_R)
        paths = f'<path d="{md}" fill="white"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n  {paths}\n</svg>\n'
    )


def vec_speaker(label):
    ix = PAD_L
    tx = ix + SPK_ICON_W + SPK_GAP
    d, adv = ft_to_path_d(ROBOTO_MEDIUM, label, tx)
    w = even_ceil(tx + adv + PAD_R)
    icon = SPEAKER_ICON.format(x=ix)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n  <path d="{d}" fill="white"/>\n</svg>\n'
    )


def vec_icon_text(label, icon_tpl, icon_w, gap=3):
    ix = PAD_L
    tx = ix + icon_w + gap
    d, adv = ft_to_path_d(ROBOTO_MEDIUM, label, tx)
    w = even_ceil(tx + adv + PAD_R)
    icon = icon_tpl.format(x=ix)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n  <path d="{d}" fill="white"/>\n</svg>\n'
    )


def vec_imax(base_dir):
    """IMAX badge - logo only, no text."""
    import re
    imax_svg = open(os.path.join(base_dir, "icons", "imax.svg")).read()
    paths = re.findall(r'<(?:polygon|path)[^>]+/>', imax_svg)
    inner = "\n    ".join(paths)
    w = even_ceil(PAD_L + IMAX_ICON_W + PAD_R)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  <g transform="translate({PAD_L}, 3) scale({IMAX_ICON_W / 978.0},{8.0 / 189.0})" fill-rule="evenodd">\n'
        f'    {inner}\n'
        f'  </g>\n'
        f'</svg>\n'
    )

# ── Static badge definitions ────────────────────────────────────────────────
# Each entry: (asset_path, vectorizer_type, vectorizer_args)

STATIC_BADGES = {
    "p-8k":    ("resolution/8k.svg",    "text", ("8K",)),
    "p-4k":    ("resolution/4k.svg",    "text", ("4K",)),
    "p-1440p": ("resolution/1440p.svg", "text", ("1440p",)),
    "p-1080p": ("resolution/1080p.svg", "text", ("1080p",)),
    "p-720p":  ("resolution/720p.svg",  "text", ("720p",)),
    "p-480p":  ("resolution/480p.svg",  "text", ("480p",)),

    "p-dv":     ("hdr/dolby-vision.svg", "dolby", ("Dolby", "Vision")),
    "p-hdr10p": ("hdr/hdr10plus.svg",   "text",  ("HDR10+",)),
    "p-hdr10":  ("hdr/hdr10.svg",       "text",  ("HDR10",)),
    "p-hlg":    ("hdr/hlg.svg",         "text",  ("HLG",)),
    "p-hdr":    ("hdr/hdr.svg",         "text",  ("HDR",)),

    "p-atmos":   ("audio/dolby-atmos.svg",       "dolby", ("Dolby", "Atmos")),
    "p-truehd":  ("audio/dolby-truehd.svg",      "dolby", ("Dolby TrueHD", None)),
    "p-ddp":     ("audio/dolby-digital-plus.svg", "dolby", ("Dolby Digital+", None)),
    "p-dd":      ("audio/dolby-digital.svg",     "dolby", ("Dolby Digital", None)),
    "p-dtsx":    ("audio/dtsx.svg",    "text", ("DTS:X",)),
    "p-dtshdma": ("audio/dts-hd-ma.svg", "text", ("DTS-HD MA",)),
    "p-dtshd":   ("audio/dts-hd.svg",  "text", ("DTS-HD",)),
    "p-dts":     ("audio/dts.svg",     "text", ("DTS",)),
    "p-flac":    ("audio/flac.svg",    "text", ("FLAC",)),
    "p-opus":    ("audio/opus.svg",    "text", ("Opus",)),
    "p-aac":     ("audio/aac.svg",     "text", ("AAC",)),
    "p-ac4":     ("audio/ac4.svg",     "text", ("AC-4",)),

    "p-71": ("channels/7.1.svg", "text", ("7.1",)),
    "p-51": ("channels/5.1.svg", "text", ("5.1",)),
    "p-20": ("channels/2.0.svg", "text", ("2.0",)),
    "p-10": ("channels/1.0.svg", "text", ("1.0",)),

    "p-remux":  ("source/remux.svg",  "icon_text", ("Remux",  "disc")),
    "p-bluray": ("source/bluray.svg", "icon_text", ("BluRay", "disc")),
    "p-webdl":  ("source/webdl.svg",  "icon_text", ("WebDL",  "globe")),
    "p-webrip": ("source/webrip.svg", "icon_text", ("WebRip", "globe")),
    "p-hdtv":   ("source/hdtv.svg",   "icon_text", ("HDTV",   "tv")),
    "p-dvdscr": ("source/dvdscr.svg", "icon_text", ("DVDScr", "dvd")),
    "p-dvdrip": ("source/dvdrip.svg", "icon_text", ("DVDRip", "dvd")),
    "p-cam":    ("source/cam.svg",    "icon_text", ("CAM",    "camera")),
    "p-r5":     ("source/r5.svg",     "text",      ("R5",)),

    "p-imax-e": ("special/imax-enhanced.svg", "raw", ()),
    "p-imax":   ("special/imax.svg",          "imax", ()),
    "p-seadex": ("special/seadex.svg",        "text", ("SeaDex",)),
}

ICON_MAP = {
    "disc":   (DISC_ICON, DISC_ICON_W),
    "globe":  (GLOBE_ICON, GLOBE_ICON_W),
    "tv":     (TV_ICON, TV_ICON_W),
    "dvd":    (DVD_ICON, DVD_ICON_W),
    "camera": (CAMERA_ICON, CAMERA_ICON_W),
}


def vectorize_badge(badge_id, base_dir=None):
    """Generate vectorized SVG content for a static badge. Returns SVG string or None."""
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

    if badge_id not in STATIC_BADGES:
        return None

    asset_path, vec_type, vec_args = STATIC_BADGES[badge_id]

    if vec_type == "raw":
        full_path = os.path.join(base_dir, "assets", asset_path)
        with open(full_path, "r") as f:
            return f.read()
    elif vec_type == "text":
        return vec_text_only(vec_args[0])
    elif vec_type == "dolby":
        return vec_dolby(vec_args[0], vec_args[1] if len(vec_args) > 1 else None)
    elif vec_type == "icon_text":
        label, icon_type = vec_args
        icon_tpl, icon_w = ICON_MAP[icon_type]
        return vec_icon_text(label, icon_tpl, icon_w)
    elif vec_type == "imax":
        return vec_imax(base_dir)
    return None
