#!/usr/bin/env python3
"""
Generate player-badge.json with vectorized SVGs (text converted to Bézier paths).

SVG files on disk use <text font-family="Roboto"> for easy preview.
The JSON embeds vectorized <path> versions so rendering is font-independent.

Requirements: freetype-py  (pip install freetype-py)
              Roboto fonts in /usr/share/fonts/truetype/roboto/

Usage:
    python3 player-badges/generate-badge-json.py
"""

import base64
import json
import math
import os
import tempfile
import shutil

import freetype

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # player-badges/
OUTPUT = os.path.join(BASE_DIR, "output", "player-badge.json")

# ── Fonts ───────────────────────────────────────────────────────────────────
ROBOTO_MEDIUM = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf"
ROBOTO_LIGHT = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Light.ttf"

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

# ── Badge style ─────────────────────────────────────────────────────────────
BADGE_STYLE = {
    "isEnabled": True,
    "tagColor": "#00000000",
    "tagStyle": "filled",
    "textColor": "#FFFFFF",
    "borderColor": "#FFFFFFFF",
}

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

# Disc icon for Remux/BluRay
DISC_ICON_W = 10
DISC_ICON = '''<g transform="translate({x}, 2)">
    <circle cx="5" cy="5" r="4.2" fill="none" stroke="white" stroke-width="1.0"/>
    <circle cx="5" cy="5" r="1.2" fill="white"/>
  </g>'''

# Globe icon for WebDL/WebRip
GLOBE_ICON_W = 10
GLOBE_ICON = '''<g transform="translate({x}, 2)">
    <circle cx="5" cy="5" r="4.0" fill="none" stroke="white" stroke-width="0.9"/>
    <ellipse cx="5" cy="5" rx="2.0" ry="4.0" fill="none" stroke="white" stroke-width="0.7"/>
    <line x1="1" y1="5" x2="9" y2="5" stroke="white" stroke-width="0.7"/>
  </g>'''

# TV icon for HDTV
TV_ICON_W = 10
TV_ICON = '''<g transform="translate({x}, 2)">
    <rect x="0.8" y="1" width="8.4" height="6" rx="0.8" fill="none" stroke="white" stroke-width="0.9"/>
    <line x1="3.5" y1="8.5" x2="6.5" y2="8.5" stroke="white" stroke-width="0.9" stroke-linecap="round"/>
    <line x1="5" y1="7" x2="5" y2="8.5" stroke="white" stroke-width="0.9" stroke-linecap="round"/>
  </g>'''

# IMAX logo (pre-scaled, read from icons/imax.svg)
IMAX_ICON_W = 42
IMAX_ICON = None  # loaded from file at runtime

# DVD disc icon for DVDScr/DVDRip
DVD_ICON_W = 10
DVD_ICON = '''<g transform="translate({x}, 2)">
    <circle cx="5" cy="5" r="4.2" fill="none" stroke="white" stroke-width="0.8"/>
    <circle cx="5" cy="5" r="2.2" fill="none" stroke="white" stroke-width="0.6"/>
    <circle cx="5" cy="5" r="0.8" fill="white"/>
  </g>'''

# Camera icon for CAM
CAMERA_ICON_W = 10
CAMERA_ICON = '''<g transform="translate({x}, 2)">
    <rect x="1" y="3" width="8" height="5.5" rx="0.8" fill="none" stroke="white" stroke-width="0.9"/>
    <circle cx="5" cy="5.8" r="1.5" fill="none" stroke="white" stroke-width="0.8"/>
    <rect x="3.5" y="1.8" width="3" height="1.5" rx="0.5" fill="none" stroke="white" stroke-width="0.7"/>
  </g>'''


# ── FreeType helpers ────────────────────────────────────────────────────────

def _ft_advance(ttf_path, text):
    face = freetype.Face(ttf_path)
    face.set_char_size(0, FONT_SIZE * 64, 72, 72)
    w = 0
    for ch in text:
        face.load_char(ch, freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
        w += face.glyph.advance.x / 64.0
    return w


def _ft_to_path_d(ttf_path, text, x_offset=0):
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


def _even_ceil(v):
    v = math.ceil(v)
    return v + 1 if v % 2 else v


# ── Preview SVG builders (text-based, Roboto font-family) ──────────────────

def _preview_text_only(label):
    adv = _ft_advance(ROBOTO_MEDIUM, label)
    w = _even_ceil(PAD_L + adv + PAD_R)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  <text x="{PAD_L}" y="{Y_BASELINE}" fill="white" font-family="Roboto, sans-serif" '
        f'font-size="{FONT_SIZE}" font-weight="500">{label}</text>\n'
        f'</svg>\n'
    )


def _preview_dolby(medium_text, light_text=None):
    ix = PAD_L
    tx = ix + DD_ICON_W + DD_GAP
    m_adv = _ft_advance(ROBOTO_MEDIUM, medium_text)
    icon = DD_ICON.format(x=ix)
    if light_text:
        lx = tx + m_adv + 3
        l_adv = _ft_advance(ROBOTO_LIGHT, light_text)
        w = _even_ceil(lx + l_adv + PAD_R)
        texts = (
            f'<text x="{tx}" y="{Y_BASELINE}" fill="white" font-family="Roboto, sans-serif" '
            f'font-size="{FONT_SIZE}" font-weight="500">{medium_text}</text>\n'
            f'  <text x="{lx:.1f}" y="{Y_BASELINE}" fill="white" fill-opacity="0.92" '
            f'font-family="Roboto, sans-serif" font-size="{FONT_SIZE}" font-weight="300">{light_text}</text>'
        )
    else:
        w = _even_ceil(tx + m_adv + PAD_R)
        texts = (
            f'<text x="{tx}" y="{Y_BASELINE}" fill="white" font-family="Roboto, sans-serif" '
            f'font-size="{FONT_SIZE}" font-weight="500">{medium_text}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n  {texts}\n</svg>\n'
    )


def _preview_speaker(label):
    ix = PAD_L
    tx = ix + SPK_ICON_W + SPK_GAP
    adv = _ft_advance(ROBOTO_MEDIUM, label)
    w = _even_ceil(tx + adv + PAD_R)
    icon = SPEAKER_ICON.format(x=ix)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n'
        f'  <text x="{tx}" y="{Y_BASELINE}" fill="white" font-family="Roboto, sans-serif" '
        f'font-size="{FONT_SIZE}" font-weight="500">{label}</text>\n'
        f'</svg>\n'
    )


def _preview_icon_text(label, icon_tpl, icon_w, gap=3):
    ix = PAD_L
    tx = ix + icon_w + gap
    adv = _ft_advance(ROBOTO_MEDIUM, label)
    w = _even_ceil(tx + adv + PAD_R)
    icon = icon_tpl.format(x=ix)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n'
        f'  <text x="{tx}" y="{Y_BASELINE}" fill="white" font-family="Roboto, sans-serif" '
        f'font-size="{FONT_SIZE}" font-weight="500">{label}</text>\n'
        f'</svg>\n'
    )


def _preview_imax():
    """IMAX badge uses the pre-scaled logo SVG, centered vertically in 14px."""
    imax_svg = open(os.path.join(BASE_DIR, "icons", "imax.svg")).read()
    # Extract just the paths from the IMAX SVG
    import re
    paths = re.findall(r'<(?:polygon|path)[^>]+/>', imax_svg)
    inner = "\n    ".join(paths)
    w = _even_ceil(PAD_L + IMAX_ICON_W + PAD_R)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  <g transform="translate({PAD_L}, 3) scale({IMAX_ICON_W / 978.0},{8.0 / 189.0})" fill-rule="evenodd">\n'
        f'    {inner}\n'
        f'  </g>\n'
        f'</svg>\n'
    )


# ── Vectorized SVG builders (path-based, for JSON) ─────────────────────────

def _vec_text_only(label):
    d, adv = _ft_to_path_d(ROBOTO_MEDIUM, label, PAD_L)
    w = _even_ceil(PAD_L + adv + PAD_R)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  <path d="{d}" fill="white"/>\n</svg>\n'
    )


def _vec_dolby(medium_text, light_text=None):
    ix = PAD_L
    tx = ix + DD_ICON_W + DD_GAP
    md, m_adv = _ft_to_path_d(ROBOTO_MEDIUM, medium_text, tx)
    icon = DD_ICON.format(x=ix)
    if light_text:
        lx = tx + m_adv + 3
        ld, l_adv = _ft_to_path_d(ROBOTO_LIGHT, light_text, lx)
        w = _even_ceil(lx + l_adv + PAD_R)
        paths = f'<path d="{md}" fill="white"/>\n  <path d="{ld}" fill="white" fill-opacity="0.92"/>'
    else:
        w = _even_ceil(tx + m_adv + PAD_R)
        paths = f'<path d="{md}" fill="white"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n  {paths}\n</svg>\n'
    )


def _vec_speaker(label):
    ix = PAD_L
    tx = ix + SPK_ICON_W + SPK_GAP
    d, adv = _ft_to_path_d(ROBOTO_MEDIUM, label, tx)
    w = _even_ceil(tx + adv + PAD_R)
    icon = SPEAKER_ICON.format(x=ix)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n  <path d="{d}" fill="white"/>\n</svg>\n'
    )


def _vec_icon_text(label, icon_tpl, icon_w, gap=3):
    ix = PAD_L
    tx = ix + icon_w + gap
    d, adv = _ft_to_path_d(ROBOTO_MEDIUM, label, tx)
    w = _even_ceil(tx + adv + PAD_R)
    icon = icon_tpl.format(x=ix)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  {icon}\n  <path d="{d}" fill="white"/>\n</svg>\n'
    )


def _vec_imax():
    """IMAX badge - logo only, no text."""
    import re
    imax_svg = open(os.path.join(BASE_DIR, "icons", "imax.svg")).read()
    paths = re.findall(r'<(?:polygon|path)[^>]+/>', imax_svg)
    inner = "\n    ".join(paths)
    w = _even_ceil(PAD_L + IMAX_ICON_W + PAD_R)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  <g transform="translate({PAD_L}, 3) scale({IMAX_ICON_W / 978.0},{8.0 / 189.0})" fill-rule="evenodd">\n'
        f'    {inner}\n'
        f'  </g>\n'
        f'</svg>\n'
    )


# ── Badge definitions ───────────────────────────────────────────────────────

RESOLUTIONS = ["8K", "4K", "1440p", "1080p", "720p", "480p"]

HDR_DOLBY = [("Dolby", "Vision", "dolby-vision")]
HDR_TEXT = [("HDR10+", "hdr10plus"), ("HDR10", "hdr10"), ("HLG", "hlg"), ("HDR", "hdr")]

AUDIO_DOLBY = [
    ("Dolby", "Atmos", "dolby-atmos"),
    ("Dolby TrueHD", None, "dolby-truehd"),
    ("Dolby Digital+", None, "dolby-digital-plus"),
    ("Dolby Digital", None, "dolby-digital"),
]
AUDIO_TEXT = [
    ("DTS:X", "dtsx"), ("DTS-HD MA", "dts-hd-ma"), ("DTS-HD", "dts-hd"),
    ("DTS", "dts"), ("FLAC", "flac"), ("Opus", "opus"), ("AAC", "aac"), ("AC-4", "ac4"),
]

CHANNELS = ["7.1", "5.1", "2.0", "1.0"]

# Source type badges (icon + text, matched against filename)
SOURCE_DISC = [  # disc icon
    ("Remux", "remux"),
    ("BluRay", "bluray"),
]
SOURCE_WEB = [  # globe icon
    ("WebDL", "webdl"),
    ("WebRip", "webrip"),
]
SOURCE_TV = [  # tv icon
    ("HDTV", "hdtv"),
]
# IMAX uses its own logo
# SeaDex is text only

LANGUAGES = [
    # Patterns require ISO code + space + letter, which only appears in playbackMatchText
    # (e.g. "eng English") and never in filenames (e.g. ".ENG-GRP" or ".ENG.").
    ("p-eng", "English",    "english",    r"(?i)\b(en|eng) [A-Za-z]"),
    ("p-pol", "Polish",     "polish",     r"(?i)\b(pl|pol) [A-Za-z]"),
    ("p-spa", "Spanish",    "spanish",    r"(?i)\b(es|spa) [A-Za-z]"),
    ("p-fre", "French",     "french",     r"(?i)\b(fr|fra|fre) [A-Za-z]"),
    ("p-ger", "German",     "german",     r"(?i)\b(de|deu|ger) [A-Za-z]"),
    ("p-ita", "Italian",    "italian",    r"(?i)\b(it|ita) [A-Za-z]"),
    ("p-por", "Portuguese", "portuguese", r"(?i)\b(por|pt) [A-Za-z]"),
    ("p-rus", "Russian",    "russian",    r"(?i)\b(ru|rus) [A-Za-z]"),
    ("p-jpn", "Japanese",   "japanese",   r"(?i)\b(ja|jpn) [A-Za-z]"),
    ("p-kor", "Korean",     "korean",     r"(?i)\b(ko|kor) [A-Za-z]"),
    ("p-zho", "Chinese",    "chinese",    r"(?i)\b(chi|zh|zho) [A-Za-z]"),
    ("p-hin", "Hindi",      "hindi",      r"(?i)\b(hi|hin) [A-Za-z]"),
    ("p-ara", "Arabic",     "arabic",     r"(?i)\b(ar|ara) [A-Za-z]"),
    ("p-tur", "Turkish",    "turkish",    r"(?i)\b(tr|tur) [A-Za-z]"),
    ("p-dut", "Dutch",      "dutch",      r"(?i)\b(dut|nl|nld) [A-Za-z]"),
    ("p-swe", "Swedish",    "swedish",    r"(?i)\b(sv|swe) [A-Za-z]"),
    ("p-nor", "Norwegian",  "norwegian",  r"(?i)\b(no|nor) [A-Za-z]"),
    ("p-dan", "Danish",     "danish",     r"(?i)\b(da|dan) [A-Za-z]"),
    ("p-fin", "Finnish",    "finnish",    r"(?i)\b(fi|fin) [A-Za-z]"),
    ("p-ces", "Czech",      "czech",      r"(?i)\b(ces|cs|cze) [A-Za-z]"),
    ("p-hun", "Hungarian",  "hungarian",  r"(?i)\b(hu|hun) [A-Za-z]"),
    ("p-ron", "Romanian",   "romanian",   r"(?i)\b(ro|ron|rum) [A-Za-z]"),
    ("p-ukr", "Ukrainian",  "ukrainian",  r"(?i)\b(uk|ukr) [A-Za-z]"),
    ("p-ell", "Greek",      "greek",      r"(?i)\b(el|ell|gre) [A-Za-z]"),
    ("p-heb", "Hebrew",     "hebrew",     r"(?i)\b(he|heb) [A-Za-z]"),
    ("p-tha", "Thai",       "thai",       r"(?i)\b(th|tha) [A-Za-z]"),
    ("p-vie", "Vietnamese", "vietnamese", r"(?i)\b(vi|vie) [A-Za-z]"),
    ("p-ind", "Indonesian", "indonesian", r"(?i)\b(id|ind) [A-Za-z]"),
    ("p-msa", "Malay",      "malay",      r"(?i)\b(may|ms|msa) [A-Za-z]"),
    ("p-hrv", "Croatian",   "croatian",   r"(?i)\b(hr|hrv) [A-Za-z]"),
    ("p-srp", "Serbian",    "serbian",    r"(?i)\b(sr|srp) [A-Za-z]"),
    ("p-bul", "Bulgarian",  "bulgarian",  r"(?i)\b(bg|bul) [A-Za-z]"),
    ("p-slk", "Slovak",     "slovak",     r"(?i)\b(sk|slk|slo) [A-Za-z]"),
    ("p-slv", "Slovenian",  "slovenian",  r"(?i)\b(sl|slv) [A-Za-z]"),
]

# ── Filter patterns (mutually exclusive within groups) ──────────────────────

FILTER_DEFS = [
    # Resolution
    ("p-8k",    "res", "8K",    r"(?i)\b(4320p|8k)\b",  "resolution/8k"),
    ("p-4k",    "res", "4K",    r"(?i)\b(2160p|4k)\b",  "resolution/4k"),
    ("p-1440p", "res", "1440p", r"(?i)\b1440p\b",       "resolution/1440p"),
    ("p-1080p", "res", "1080p", r"(?i)\b1080p\b",       "resolution/1080p"),
    ("p-720p",  "res", "720p",  r"(?i)\b720p\b",        "resolution/720p"),
    ("p-480p",  "res", "480p",  r"(?i)\b480p\b",        "resolution/480p"),
    # HDR — mutually exclusive: DV > HDR10+ > HDR10 > HLG > HDR
    ("p-dv",     "hdr", "Dolby Vision", r"(?i)\b(DV|DoVi|Dolby[\s.]?Vision)\b",                                "hdr/dolby-vision"),
    ("p-hdr10p", "hdr", "HDR10+",       r"(?i)^(?!.*\b(DV|DoVi|Dolby[\s.]?Vision)\b).*\bHDR10\+",             "hdr/hdr10plus"),
    ("p-hdr10",  "hdr", "HDR10",        r"(?i)^(?!.*\b(DV|DoVi|Dolby[\s.]?Vision)\b)(?!.*HDR10\+).*\bHDR10\b","hdr/hdr10"),
    ("p-hlg",    "hdr", "HLG",          r"(?i)^(?!.*\b(DV|DoVi|Dolby[\s.]?Vision)\b).*\bHLG\b",               "hdr/hlg"),
    ("p-hdr",    "hdr", "HDR",          r"(?i)^(?!.*\b(DV|DoVi|Dolby[\s.]?Vision)\b)(?!.*HDR10)(?!.*HLG).*\bHDR\b", "hdr/hdr"),
    # Audio — mutually exclusive: Atmos > TrueHD > DD+ > DD, DTS:X > DTS-HD MA > DTS-HD > DTS
    ("p-atmos",   "aud", "Dolby Atmos",   r"(?i)\bAtmos\b",                                                     "audio/dolby-atmos"),
    ("p-truehd",  "aud", "Dolby TrueHD",  r"(?i)^(?!.*\bAtmos\b).*\bTrueHD\b",                                 "audio/dolby-truehd"),
    ("p-ddp",     "aud", "Dolby Digital+", r"(?i)^(?!.*\bAtmos\b)(?!.*\bTrueHD\b).*\b(DD\+|DDP|EAC3)\b",       "audio/dolby-digital-plus"),
    ("p-dd",      "aud", "Dolby Digital",  r"(?i)^(?!.*\bAtmos\b)(?!.*\bTrueHD\b)(?!.*\b(DD\+|DDP|EAC3)\b).*\b(DD|AC3)\b", "audio/dolby-digital"),
    ("p-dtsx",    "aud", "DTS:X",          r"(?i)\bDTS:X\b",                                                    "audio/dtsx"),
    ("p-dtshdma", "aud", "DTS-HD MA",      r"(?i)^(?!.*\bDTS:X\b).*\bDTS-HD MA\b",                              "audio/dts-hd-ma"),
    ("p-dtshd",   "aud", "DTS-HD",         r"(?i)^(?!.*\bDTS:X\b)(?!.*\bDTS-HD MA\b).*\bDTS-HD\b",             "audio/dts-hd"),
    ("p-dts",     "aud", "DTS",            r"(?i)^(?!.*\bDTS[-:])\b.*\bDTS\b",                                  "audio/dts"),
    ("p-flac",    "aud", "FLAC",           r"(?i)\bFLAC\b",                                                     "audio/flac"),
    ("p-opus",    "aud", "Opus",           r"(?i)\bOpus\b",                                                     "audio/opus"),
    ("p-aac",     "aud", "AAC",            r"(?i)\bAAC\b",                                                      "audio/aac"),
    ("p-ac4",     "aud", "AC-4",           r"(?i)\b(AC-?4|AC4)\b",                                             "audio/ac4"),
    # Channels
    ("p-71", "ch", "7.1", r"(?i)\b7\.1\b", "channels/7.1"),
    ("p-51", "ch", "5.1", r"(?i)\b5\.1\b", "channels/5.1"),
    ("p-20", "ch", "2.0", r"(?i)\b2\.0\b", "channels/2.0"),
    ("p-10", "ch", "1.0", r"(?i)\b1\.0\b", "channels/1.0"),
    # Source (matched against filename) - patterns from nuvio-minimalist-badges
    ("p-remux",  "src", "Remux",  r"(?i)\b(?:bd|uhd)?remux\b",                            "source/remux"),
    ("p-bluray", "src", "BluRay", r"(?i)^(?=.*(?:bluray|blu-ray|\bb[dr][-_. ]?rip\b|\bbd(?:25|50|r|mv)?\b))(?!.*\b(?:bd|uhd)?remux\b)",  "source/bluray"),
    ("p-webdl",  "src", "WebDL",  r"(?i)\b(?:web[-_. ]?dl|webdl|web(?![-_. ]?rip)\b)",    "source/webdl"),
    ("p-webrip", "src", "WebRip", r"(?i)^(?=.*\brip\b|.*\bweb[-_. ]?rip\b|.*\bhd[-_. ]?rip\b)(?!.*\b(?:bd|br)[-_. ]?rip\b)(?!.*\bdvd[-_. ]?rip\b)(?!.*\b(?:hd[-_. ]?)?tc[-_. ]?rip\b)(?!.*\b(?:hd[-_. ]?)?ts[-_. ]?rip\b)(?!.*\b(?:hd[-_. ]?)?cam[-_. ]?rip\b)", "source/webrip"),
    ("p-hdtv",   "src", "HDTV",   r"(?i)\b(?:hdtv|pdtv|sdtv|dsr)\b",                     "source/hdtv"),
    ("p-dvdscr", "src", "DVDScr", r"(?i)\bdvd[\s._-]?scr(?:eener)?\b",                    "source/dvdscr"),
    ("p-dvdrip", "src", "DVDRip", r"(?i)^(?=.*\bdvd[\s._-]?rip\b)(?!.*\bdvd[\s._-]?scr)", "source/dvdrip"),
    ("p-cam",    "src", "CAM",    r"(?i)^(?=.*(?:\b(?:hd[-_. ]?)?cam(?:[-_. ]?rip)?\b|\b(?:hd[-_. ]?)?ts(?:[-_. ]?rip)?\b|\btelesync\b|\bp(?:re[\s._-]?)?dvd(?:rip)?\b|\b(?:hd[-_. ]?)?tc(?:[-_. ]?rip)?\b|\btelecine\b|(?<!dvd)(?<!dvd[._-])\bscr(?:eener)?\b))(?!.*\bdvd[\s._-]?scr)", "source/cam"),
    ("p-r5",     "src", "R5",     r"(?i)\br5\b",                                          "source/r5"),
    # Special
    ("p-imax-e", "spc", "IMAX Enhanced", r"(?i)\bimax[\s._-]?enhanced\b",                 "special/imax-enhanced"),
    ("p-imax",   "spc", "IMAX",   r"(?i)^(?=.*\bIMAX\b)(?!.*enhanced)",                   "special/imax"),
    ("p-seadex", "spc", "SeaDex", r"(?i)\b(?:seadex|best[\s._-]?release|alt[\s._-]?(?:best[\s._-]?)?release)\b|\u200b\u200c\u200d", "special/seadex"),
]


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    vec_dir = tempfile.mkdtemp()

    def _write(rel, content):
        full = os.path.join(BASE_DIR, "assets", rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    def _write_vec(rel, content):
        full = os.path.join(vec_dir, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    # ── Write preview SVGs + vectorized SVGs ──

    # Resolution
    for name in RESOLUTIONS:
        fn = f"resolution/{name.lower()}.svg"
        _write(fn, _preview_text_only(name))
        _write_vec(fn, _vec_text_only(name))

    # HDR Dolby
    for bold, light, fname in HDR_DOLBY:
        fn = f"hdr/{fname}.svg"
        _write(fn, _preview_dolby(bold, light))
        _write_vec(fn, _vec_dolby(bold, light))

    # HDR text
    for name, fname in HDR_TEXT:
        fn = f"hdr/{fname}.svg"
        _write(fn, _preview_text_only(name))
        _write_vec(fn, _vec_text_only(name))

    # Audio Dolby
    for bold, light, fname in AUDIO_DOLBY:
        fn = f"audio/{fname}.svg"
        _write(fn, _preview_dolby(bold, light))
        _write_vec(fn, _vec_dolby(bold, light))

    # Audio text
    for name, fname in AUDIO_TEXT:
        fn = f"audio/{fname}.svg"
        _write(fn, _preview_text_only(name))
        _write_vec(fn, _vec_text_only(name))

    # Channels
    for name in CHANNELS:
        fn = f"channels/{name}.svg"
        _write(fn, _preview_text_only(name))
        _write_vec(fn, _vec_text_only(name))

    # Languages
    for _, name, fname, _ in LANGUAGES:
        fn = f"language/{fname}.svg"
        _write(fn, _preview_speaker(name))
        _write_vec(fn, _vec_speaker(name))

    # Source - disc icon (Remux, BluRay)
    for name, fname in SOURCE_DISC:
        fn = f"source/{fname}.svg"
        _write(fn, _preview_icon_text(name, DISC_ICON, DISC_ICON_W))
        _write_vec(fn, _vec_icon_text(name, DISC_ICON, DISC_ICON_W))

    # Source - globe icon (WebDL, WebRip)
    for name, fname in SOURCE_WEB:
        fn = f"source/{fname}.svg"
        _write(fn, _preview_icon_text(name, GLOBE_ICON, GLOBE_ICON_W))
        _write_vec(fn, _vec_icon_text(name, GLOBE_ICON, GLOBE_ICON_W))

    # Source - TV icon (HDTV)
    for name, fname in SOURCE_TV:
        fn = f"source/{fname}.svg"
        _write(fn, _preview_icon_text(name, TV_ICON, TV_ICON_W))
        _write_vec(fn, _vec_icon_text(name, TV_ICON, TV_ICON_W))

    # Source - text only (DVDScr, DVDRip, CAM, R5)
    for name, fname in [("DVDScr", "dvdscr"), ("DVDRip", "dvdrip")]:
        fn = f"source/{fname}.svg"
        _write(fn, _preview_icon_text(name, DVD_ICON, DVD_ICON_W))
        _write_vec(fn, _vec_icon_text(name, DVD_ICON, DVD_ICON_W))
    fn = "source/cam.svg"
    _write(fn, _preview_icon_text("CAM", CAMERA_ICON, CAMERA_ICON_W))
    _write_vec(fn, _vec_icon_text("CAM", CAMERA_ICON, CAMERA_ICON_W))
    fn = "source/r5.svg"
    _write(fn, _preview_text_only("R5"))
    _write_vec(fn, _vec_text_only("R5"))

    # Special - IMAX Enhanced (read from manually edited file)
    imax_enh_src = os.path.join(BASE_DIR, "assets", "special", "imax-enhanced.svg")
    if os.path.exists(imax_enh_src):
        with open(imax_enh_src) as f:
            imax_enh_content = f.read()
        _write_vec("special/imax-enhanced.svg", imax_enh_content)
    else:
        _write("special/imax-enhanced.svg", _preview_text_only("IMAX Enhanced"))
        _write_vec("special/imax-enhanced.svg", _vec_text_only("IMAX Enhanced"))

    # Special - IMAX (logo only)
    _write("special/imax.svg", _preview_imax())
    _write_vec("special/imax.svg", _vec_imax())

    # Special - SeaDex (text only)
    _write("special/seadex.svg", _preview_text_only("SeaDex"))
    _write_vec("special/seadex.svg", _vec_text_only("SeaDex"))

    # ── Build JSON from vectorized SVGs ──

    def _svg_uri(rel):
        with open(os.path.join(vec_dir, rel), "rb") as f:
            return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()

    def _badge(fid, group, name, pattern, svg_rel):
        return {
            "id": fid, "groupId": group, "name": name,
            "pattern": pattern, "imageURL": _svg_uri(svg_rel + ".svg"),
            **BADGE_STYLE,
        }

    filters = [_badge(*fd) for fd in FILTER_DEFS]
    for lid, lname, lfname, lpat in LANGUAGES:
        filters.append(_badge(lid, "lang", lname, lpat, f"language/{lfname}"))

    data = {
        "groups": [
            {"id": "res",  "name": "Resolution",   "isExpanded": True},
            {"id": "hdr",  "name": "HDR / Vision",  "isExpanded": True},
            {"id": "aud",  "name": "Audio Format",  "isExpanded": True},
            {"id": "ch",   "name": "Channels",      "isExpanded": True},
            {"id": "src",  "name": "Source",         "isExpanded": True},
            {"id": "spc",  "name": "Special",        "isExpanded": True},
            {"id": "lang", "name": "Language",       "isExpanded": True},
        ],
        "filters": filters,
    }

    with open(OUTPUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    shutil.rmtree(vec_dir)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"Generated {OUTPUT}")
    print(f"  {len(filters)} filters, {size_kb:.1f} KB")
    print(f"  SVGs on disk: <text> with Roboto (for preview)")
    print(f"  JSON imageURL: vectorized <path> (font-independent)")


if __name__ == "__main__":
    main()
