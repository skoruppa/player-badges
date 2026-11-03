#!/usr/bin/env python3
"""
Generate vectorized SVG language badges for all app locales and audio languages.

Uses Roboto Medium as primary font with Noto Sans fallback chain for non-Latin scripts
(Arabic, Hebrew, CJK, Devanagari, Bengali, Tamil, Telugu, Malayalam, Thai, Greek).

Output: player-badges/assets/language/<locale>/vectorized/<iso3>.svg

Usage:
    python3 player-badges/scripts/generate-language-assets.py
"""

import freetype
import math
import os
import unicodedata

import uharfbuzz as hb
from babel import Locale

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "assets", "language")

FONT_SIZE = 9
Y_BASELINE = 10.5
PAD_L = 4
PAD_R = 3
SPK_ICON_W = 10
SPK_GAP = 3

SPEAKER_ICON = '''<g transform="translate({x}, 2)">
    <path d="M0.6,3.6 L0.6,6.2 L2.1,6.2 L4.3,8.2 L4.3,1.5 L2.1,3.6 Z" fill="white" stroke="white" stroke-width="0.25" stroke-linejoin="round"/>
    <path d="M6.2,3.2 A2.1,2.1 0 0 1 6.2,6.8" fill="none" stroke="white" stroke-width="1.0" stroke-linecap="round"/>
    <path d="M8.0,1.7 A3.7,3.7 0 0 1 8.0,8.3" fill="none" stroke="white" stroke-width="1.0" stroke-linecap="round"/>
  </g>'''

FONT_CHAIN = []
_HB_FONTS = {}

def _build_font_chain(bold=False):
    """Look in project fonts/ first, fall back to system paths."""
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
    candidates = [
        ("Roboto-Medium.ttf", "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf"),
        ("NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        ("NotoSansArabic-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"),
        ("NotoSansHebrew-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf"),
        ("NotoSansBengali-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"),
        ("NotoSansDevanagari-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
        ("NotoSansTamil-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf"),
        ("NotoSansTelugu-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf"),
        ("NotoSansMalayalam-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Regular.ttf"),
        ("NotoSansThai-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"),
        ("NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    chain = []
    for name, system_path in candidates:
        if bold:
            name = name.replace("-Medium", "-Bold").replace("-Regular", "-Bold")
            system_path = system_path.replace("-Medium", "-Bold").replace("-Regular", "-Bold")
        local = os.path.join(fonts_dir, name)
        path = local if os.path.exists(local) else system_path
        if os.path.exists(path):
            chain.append(path)
    return chain

APP_LOCALES = {
    "en": "en", "ar": "ar", "bg": "bg", "bn": "bn", "cs": "cs", "de": "de",
    "el": "el", "es": "es", "fr": "fr", "he": "he", "hr": "hr", "hu": "hu",
    "id": "id", "it": "it", "ja": "ja", "nb": "nb", "nl": "nl", "pl": "pl",
    "pt": "pt", "pt-br": "pt_BR", "ro": "ro", "ru": "ru", "sk": "sk",
    "ta": "ta", "te": "te", "ml": "ml", "tr": "tr", "ur": "ur", "vi": "vi",
}

AUDIO_LANGS = [
    "en", "pl", "es", "fr", "de", "it", "pt", "pt_BR", "ru", "ja", "ko", "zh", "hi", "ta", "te", "ml",
    "ar", "tr", "nl", "sv", "no", "da", "fi", "cs", "hu", "ro", "uk", "el",
    "he", "th", "vi", "id", "ms", "hr", "sr", "bg", "sk", "sl",
]

AUDIO_TO_ISO3 = {
    "en": "eng", "pl": "pol", "es": "spa", "fr": "fra", "de": "deu", "it": "ita",
    "pt": "por", "pt_BR": "por-br", "ru": "rus", "ja": "jpn", "ko": "kor", "zh": "zho",
    "hi": "hin", "ta": "tam", "te": "tel", "ml": "mal", "ar": "ara", "tr": "tur", "nl": "nld", "sv": "swe", "no": "nor",
    "da": "dan", "fi": "fin", "cs": "ces", "hu": "hun", "ro": "ron", "uk": "ukr",
    "el": "ell", "he": "heb", "th": "tha", "vi": "vie", "id": "ind", "ms": "msa",
    "hr": "hrv", "sr": "srp", "bg": "bul", "sk": "slk", "sl": "slv",
}


def _load_faces(bold=False):
    chain = _build_font_chain(bold)
    faces = []
    for path in chain:
        if os.path.exists(path):
            f = freetype.Face(path)
            f.set_char_size(0, FONT_SIZE * 64, 72, 72)
            f.source_path = path
            faces.append(f)
    return faces


def _find_face(faces, ch):
    for face in faces:
        if face.get_char_index(ord(ch)) != 0:
            return face
    return faces[0]


def _outline_path(outline, ox, parts):
    """Append SVG path commands for a loaded glyph outline, with its origin at x=ox."""
    pts, tgs, ctrs = outline.points, outline.tags, outline.contours
    s = 0
    for ce in ctrs:
        cp = pts[s : ce + 1]
        ct = tgs[s : ce + 1]
        n = len(cp)
        if n == 0:
            s = ce + 1
            continue

        def tx(p):
            return (ox + p[0] / 64.0, Y_BASELINE - p[1] / 64.0)

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
                    parts.append(f"Q{pt[0]:.2f},{pt[1]:.2f} {npt[0]:.2f},{npt[1]:.2f}")
                    i += 2
                else:
                    mid = ((pt[0] + npt[0]) / 2, (pt[1] + npt[1]) / 2)
                    parts.append(f"Q{pt[0]:.2f},{pt[1]:.2f} {mid[0]:.2f},{mid[1]:.2f}")
                    i += 1
        parts.append("Z")
        s = ce + 1


def _text_runs(faces, text):
    """Split text into same-font runs; spaces and punctuation stay in the current run."""
    runs = []
    for ch in text:
        face = _find_face(faces, ch)
        if runs and (face is runs[-1][0] or not ch.isalpha()):
            runs[-1][1] += ch
        else:
            runs.append([face, ch])
    return runs


def _shaped_font(face):
    key = face.source_path
    if key not in _HB_FONTS:
        font = hb.Font(hb.Face(hb.Blob.from_file_path(key)))
        font.scale = (FONT_SIZE * 64, FONT_SIZE * 64)
        _HB_FONTS[key] = font
    return _HB_FONTS[key]


def _draw_plain(face, text, px, parts):
    for ch in text:
        face.set_char_size(0, FONT_SIZE * 64, 72, 72)
        face.load_char(ch, freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
        _outline_path(face.glyph.outline, px, parts)
        px += face.glyph.advance.x / 64.0
    return px


def _draw_shaped(face, text, px, parts):
    """Shape with HarfBuzz: joins Arabic letters, orders RTL runs, builds Indic clusters."""
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(_shaped_font(face), buf)
    face.set_char_size(0, FONT_SIZE * 64, 72, 72)
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        face.load_glyph(info.codepoint, freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
        _outline_path(face.glyph.outline, px + pos.x_offset / 64.0, parts)
        px += pos.x_advance / 64.0
    return px


def _path_text(faces, text, x0=0):
    runs = _text_runs(faces, text)
    if any(unicodedata.bidirectional(ch) in ("R", "AL") for ch in text):
        runs.reverse()
    parts = []
    px = x0
    for face, run in runs:
        draw = _draw_plain if face is faces[0] else _draw_shaped
        px = draw(face, run, px, parts)
    return " ".join(parts), px - x0


def _even_ceil(v):
    v = math.ceil(v)
    return v + 1 if v % 2 else v


def _make_svg(faces, label):
    """Badge with speaker icon + text (for player context)."""
    ix = PAD_L
    tx = ix + SPK_ICON_W + SPK_GAP
    icon = SPEAKER_ICON.format(x=ix)
    d, adv = _path_text(faces, label, tx)
    w = _even_ceil(tx + adv + PAD_R)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f"  {icon}\n"
        f'  <path d="{d}" fill="white"/>\n'
        f"</svg>\n"
    )


def _make_text_svg(faces, label):
    """Badge with text only, no icon (for source context)."""
    d, adv = _path_text(faces, label, PAD_L)
    w = _even_ceil(PAD_L + adv + PAD_R)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="14" viewBox="0 0 {w} 14">\n'
        f'  <path d="{d}" fill="white"/>\n'
        f"</svg>\n"
    )


# Overrides for language names where Babel doesn't distinguish pt from pt-BR correctly.
# Babel 2.17 unified on Brazilian forms; European Portuguese uses different names.
LABEL_OVERRIDES = {
    "pt": {
        "pl": "Polaco",     # Babel gives "Polonês" (Brazilian)
        "cs": "Checo",      # Babel gives "Tcheco" (Brazilian)
    },
}

# Short label overrides for Brazilian Portuguese — adjective form per locale
PT_BR_LABELS = {
    "en": "Brazilian",
    "pl": "Brazylijski",
    "de": "Brasilianisch",
    "es": "Brasileño",
    "fr": "Brésilien",
    "it": "Brasiliano",
    "pt": "Brasileiro",
    "pt_BR": "Brasileiro",
    "ru": "Бразильский",
    "tr": "Brezilya",
    "nl": "Braziliaans",
    "hu": "Brazil",
    "cs": "Brazilský",
    "hr": "Brazilski",
    "ro": "Brazilian",
    "sk": "Brazílsky",
    "vi": "Brazil",
    "id": "Brasil",
    "bg": "Бразилски",
    "ja": "ブラジル",
    "ar": "برازيلي",
    "el": "Βραζιλιάνικα",
    "he": "ברזילאי",
    "bn": "ব্রাজিলীয়",
    "ur": "برازیلی",
    "nb": "Brasiliansk",
    "sv": "Brasiliansk",
    "da": "Brasiliansk",
    "fi": "Brasilian",
    "ta": "பிரேசிலியன்",
    "te": "బ్రెజిలియన్",
    "ml": "ബ്രസീലിയൻ",
}


def _get_label(audio_lang, app_locale):
    # Check manual overrides first
    for locale_key, overrides in LABEL_OVERRIDES.items():
        if app_locale == locale_key and audio_lang in overrides:
            return overrides[audio_lang]
    # Short labels for Brazilian Portuguese
    if audio_lang == "pt_BR" and app_locale in PT_BR_LABELS:
        return PT_BR_LABELS[app_locale]
    try:
        audio_loc = Locale.parse(audio_lang)
        app_loc = Locale.parse(app_locale)
        label = audio_loc.get_display_name(app_loc)
        if not label or label == audio_lang:
            label = audio_loc.get_language_name(app_loc) or audio_lang.upper()
    except Exception:
        label = audio_lang.upper()
    return label[0].upper() + label[1:] if label else audio_lang.upper()


def main():
    total = 0
    for faces, suffix in [(_load_faces(), ""), (_load_faces(bold=True), "-bold")]:
        total += _generate(faces, suffix)

    print(f"Generated {total} vectorized language SVGs")
    print(f"  Locales: {len(APP_LOCALES) + 1} (including ISO)")
    print(f"  Languages per locale: {len(AUDIO_LANGS)}")
    print(f"  Output: {OUTPUT_DIR}")


def _generate(faces, suffix):
    total = 0

    for app_dir, babel_str in sorted(APP_LOCALES.items()):
        # With speaker icon (player context)
        vec_dir = os.path.join(OUTPUT_DIR, app_dir, f"vectorized{suffix}")
        os.makedirs(vec_dir, exist_ok=True)

        # Text only (source context, compact player)
        text_dir = os.path.join(OUTPUT_DIR, app_dir, f"text-only{suffix}")
        os.makedirs(text_dir, exist_ok=True)

        for audio_lang in AUDIO_LANGS:
            iso3 = AUDIO_TO_ISO3[audio_lang]
            label = _get_label(audio_lang, babel_str)

            with open(os.path.join(vec_dir, f"{iso3}.svg"), "w") as f:
                f.write(_make_svg(faces, label))

            with open(os.path.join(text_dir, f"{iso3}.svg"), "w") as f:
                f.write(_make_text_svg(faces, label))

            total += 2

    # ISO variant
    for subdir, make_fn in [("vectorized", _make_svg), ("text-only", _make_text_svg)]:
        iso_dir = os.path.join(OUTPUT_DIR, "iso", f"{subdir}{suffix}")
        os.makedirs(iso_dir, exist_ok=True)
        for audio_lang in AUDIO_LANGS:
            iso3 = AUDIO_TO_ISO3[audio_lang]
            svg = make_fn(faces, iso3.upper())
            with open(os.path.join(iso_dir, f"{iso3}.svg"), "w") as f:
                f.write(svg)
            total += 1

    return total


if __name__ == "__main__":
    main()
