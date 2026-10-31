#!/usr/bin/env python3
"""
Generate a badge manifest (catalog of all available filters) and per-element JSON fragments.

The manifest is used by the web editor to show available badges.
Per-element fragments are used by the dynamic API to assemble custom JSONs.

Output:
  output/manifest.json        - catalog of all filters with metadata (no base64)
  output/fragments/           - per-filter JSON with base64 imageURL
  output/fragments/groups.json - all group definitions

Usage:
    python3 player-badges/scripts/generate-manifest.py
"""

import base64
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FRAGMENTS_DIR = os.path.join(OUTPUT_DIR, "fragments")

# ── Groups ──────────────────────────────────────────────────────────────────

GROUPS = [
    {"id": "res",  "name": "Resolution",   "isExpanded": True},
    {"id": "hdr",  "name": "HDR / Vision", "isExpanded": True},
    {"id": "aud",  "name": "Audio Format", "isExpanded": True},
    {"id": "ch",   "name": "Channels",     "isExpanded": True},
    {"id": "src",  "name": "Source",        "isExpanded": True},
    {"id": "spc",  "name": "Special",       "isExpanded": True},
    {"id": "lang", "name": "Language",      "isExpanded": True},
]

BADGE_STYLE = {
    "isEnabled": True,
    "tagColor": "#00000000",
    "tagStyle": "filled",
    "textColor": "#FFFFFF",
    "borderColor": "#FFFFFFFF",
}

# ── Filter definitions ──────────────────────────────────────────────────────
# (id, groupId, name, pattern, asset_path relative to assets/)

FILTERS = [
    # Resolution
    ("p-8k",    "res", "8K",    r"(?i)\b(4320p|8k)\b",  "resolution/8k.svg"),
    ("p-4k",    "res", "4K",    r"(?i)\b(2160p|4k)\b",  "resolution/4k.svg"),
    ("p-1440p", "res", "1440p", r"(?i)\b1440p\b",       "resolution/1440p.svg"),
    ("p-1080p", "res", "1080p", r"(?i)\b1080p\b",       "resolution/1080p.svg"),
    ("p-720p",  "res", "720p",  r"(?i)\b720p\b",        "resolution/720p.svg"),
    ("p-480p",  "res", "480p",  r"(?i)\b480p\b",        "resolution/480p.svg"),
    # HDR
    ("p-dv",     "hdr", "Dolby Vision", r"(?i)\b(DV|DoVi|Dolby[\s.]?Vision)\b", "hdr/dolby-vision.svg"),
    ("p-hdr10p", "hdr", "HDR10+",       r"(?i)^(?!.*\b(DV|DoVi|Dolby[\s.]?Vision)\b).*\bHDR10\+", "hdr/hdr10plus.svg"),
    ("p-hdr10",  "hdr", "HDR10",        r"(?i)^(?!.*\b(DV|DoVi|Dolby[\s.]?Vision)\b)(?!.*HDR10\+).*\bHDR10\b", "hdr/hdr10.svg"),
    ("p-hlg",    "hdr", "HLG",          r"(?i)^(?!.*\b(DV|DoVi|Dolby[\s.]?Vision)\b).*\bHLG\b", "hdr/hlg.svg"),
    ("p-hdr",    "hdr", "HDR",          r"(?i)^(?!.*\b(DV|DoVi|Dolby[\s.]?Vision)\b)(?!.*HDR10)(?!.*HLG).*\bHDR\b", "hdr/hdr.svg"),
    # Audio
    ("p-atmos",   "aud", "Dolby Atmos",   r"(?i)\bAtmos\b", "audio/dolby-atmos.svg"),
    ("p-truehd",  "aud", "Dolby TrueHD",  r"(?i)^(?!.*\bAtmos\b).*\bTrueHD\b", "audio/dolby-truehd.svg"),
    ("p-ddp",     "aud", "Dolby Digital+", r"(?i)^(?!.*\bAtmos\b)(?!.*\bTrueHD\b).*\b(DD\+|DDP|EAC3)\b", "audio/dolby-digital-plus.svg"),
    ("p-dd",      "aud", "Dolby Digital",  r"(?i)^(?!.*\bAtmos\b)(?!.*\bTrueHD\b)(?!.*\b(DD\+|DDP|EAC3)\b).*\b(DD|AC3)\b", "audio/dolby-digital.svg"),
    ("p-dtsx",    "aud", "DTS:X",          r"(?i)\bDTS:X\b", "audio/dtsx.svg"),
    ("p-dtshdma", "aud", "DTS-HD MA",      r"(?i)^(?!.*\bDTS:X\b).*\bDTS-HD MA\b", "audio/dts-hd-ma.svg"),
    ("p-dtshd",   "aud", "DTS-HD",         r"(?i)^(?!.*\bDTS:X\b)(?!.*\bDTS-HD MA\b).*\bDTS-HD\b", "audio/dts-hd.svg"),
    ("p-dts",     "aud", "DTS",            r"(?i)^(?!.*\bDTS[-:])\b.*\bDTS\b", "audio/dts.svg"),
    ("p-flac",    "aud", "FLAC",           r"(?i)\bFLAC\b", "audio/flac.svg"),
    ("p-opus",    "aud", "Opus",           r"(?i)\bOpus\b", "audio/opus.svg"),
    ("p-aac",     "aud", "AAC",            r"(?i)\bAAC\b", "audio/aac.svg"),
    ("p-ac4",     "aud", "AC-4",           r"(?i)\b(AC-?4|AC4)\b", "audio/ac4.svg"),
    # Channels
    ("p-71", "ch", "7.1", r"(?i)\b7\.1\b", "channels/7.1.svg"),
    ("p-51", "ch", "5.1", r"(?i)\b5\.1\b", "channels/5.1.svg"),
    ("p-20", "ch", "2.0", r"(?i)\b2\.0\b", "channels/2.0.svg"),
    ("p-10", "ch", "1.0", r"(?i)\b1\.0\b", "channels/1.0.svg"),
    # Source
    ("p-remux",  "src", "Remux",  r"(?i)\b(?:bd|uhd)?remux\b", "source/remux.svg"),
    ("p-bluray", "src", "BluRay", r"(?i)^(?=.*(?:bluray|blu-ray|\bb[dr][-_. ]?rip\b|\bbd(?:25|50|r|mv)?\b))(?!.*\b(?:bd|uhd)?remux\b)", "source/bluray.svg"),
    ("p-webdl",  "src", "WebDL",  r"(?i)\b(?:web[-_. ]?dl|webdl|web(?![-_. ]?rip)\b)", "source/webdl.svg"),
    ("p-webrip", "src", "WebRip", r"(?i)^(?=.*\brip\b|.*\bweb[-_. ]?rip\b|.*\bhd[-_. ]?rip\b)(?!.*\b(?:bd|br)[-_. ]?rip\b)(?!.*\bdvd[-_. ]?rip\b)(?!.*\b(?:hd[-_. ]?)?tc[-_. ]?rip\b)(?!.*\b(?:hd[-_. ]?)?ts[-_. ]?rip\b)(?!.*\b(?:hd[-_. ]?)?cam[-_. ]?rip\b)", "source/webrip.svg"),
    ("p-hdtv",   "src", "HDTV",   r"(?i)\b(?:hdtv|pdtv|sdtv|dsr)\b", "source/hdtv.svg"),
    ("p-dvdrip", "src", "DVDRip", r"(?i)^(?=.*\bdvd[\s._-]?rip\b)(?!.*\bdvd[\s._-]?scr)", "source/dvdrip.svg"),
    ("p-dvdscr", "src", "DVDScr", r"(?i)\bdvd[\s._-]?scr(?:eener)?\b", "source/dvdscr.svg"),
    ("p-cam",    "src", "CAM",    r"(?i)^(?=.*(?:\b(?:hd[-_. ]?)?cam(?:[-_. ]?rip)?\b|\b(?:hd[-_. ]?)?ts(?:[-_. ]?rip)?\b|\btelesync\b|\bp(?:re[\s._-]?)?dvd(?:rip)?\b|\b(?:hd[-_. ]?)?tc(?:[-_. ]?rip)?\b|\btelecine\b|(?<!dvd)(?<!dvd[._-])\bscr(?:eener)?\b))(?!.*\bdvd[\s._-]?scr)", "source/cam.svg"),
    ("p-r5",     "src", "R5",     r"(?i)\br5\b", "source/r5.svg"),
    # Special
    ("p-imax-e", "spc", "IMAX Enhanced", r"(?i)\bimax[\s._-]?enhanced\b", "special/imax-enhanced.svg"),
    ("p-imax",   "spc", "IMAX",   r"(?i)^(?=.*\bIMAX\b)(?!.*enhanced)", "special/imax.svg"),
    ("p-seadex", "spc", "SeaDex", r"(?i)\b(?:seadex|best[\s._-]?release|alt[\s._-]?(?:best[\s._-]?)?release)\b|\u200b\u200c\u200d", "special/seadex.svg"),
]

# Language filters use locale-dependent SVGs
# Player context: speaker icon, matches playbackMatchText tokens (space-bounded)
LANGUAGE_DEFS = [
    ("p-eng", "English",    "eng", r"(?i)(?:^| )(en|eng|english)(?= |$)"),
    ("p-pol", "Polish",     "pol", r"(?i)(?:^| )(pl|pol|polish)(?= |$)"),
    ("p-spa", "Spanish",    "spa", r"(?i)(?:^| )(es|spa|spanish)(?= |$)"),
    ("p-fre", "French",     "fra", r"(?i)(?:^| )(fr|fra|fre|french)(?= |$)"),
    ("p-ger", "German",     "deu", r"(?i)(?:^| )(de|deu|ger|german)(?= |$)"),
    ("p-ita", "Italian",    "ita", r"(?i)(?:^| )(it|ita|italian)(?= |$)"),
    ("p-por", "Portuguese", "por", r"(?i)(?:^| )(pt|por|portuguese)(?= |$)(?!.*\bpt-br\b)"),
    ("p-por-br", "Brazilian",  "por-br", r"(?i)(?:^| )(pt-br|pob|portuguese[\s(]+brazil)"),
    ("p-rus", "Russian",    "rus", r"(?i)(?:^| )(ru|rus|russian)(?= |$)"),
    ("p-jpn", "Japanese",   "jpn", r"(?i)(?:^| )(ja|jpn|japanese)(?= |$)"),
    ("p-kor", "Korean",     "kor", r"(?i)(?:^| )(ko|kor|korean)(?= |$)"),
    ("p-zho", "Chinese",    "zho", r"(?i)(?:^| )(zh|chi|zho|chinese)(?= |$)"),
    ("p-hin", "Hindi",      "hin", r"(?i)(?:^| )(hi|hin|hindi)(?= |$)"),
    ("p-ara", "Arabic",     "ara", r"(?i)(?:^| )(ar|ara|arabic)(?= |$)"),
    ("p-tur", "Turkish",    "tur", r"(?i)(?:^| )(tr|tur|turkish)(?= |$)"),
    ("p-dut", "Dutch",      "nld", r"(?i)(?:^| )(nl|nld|dut|dutch)(?= |$)"),
    ("p-swe", "Swedish",    "swe", r"(?i)(?:^| )(sv|swe|swedish)(?= |$)"),
    ("p-nor", "Norwegian",  "nor", r"(?i)(?:^| )(no|nor|norwegian)(?= |$)"),
    ("p-dan", "Danish",     "dan", r"(?i)(?:^| )(da|dan|danish)(?= |$)"),
    ("p-fin", "Finnish",    "fin", r"(?i)(?:^| )(fi|fin|finnish)(?= |$)"),
    ("p-ces", "Czech",      "ces", r"(?i)(?:^| )(cs|ces|cze|czech)(?= |$)"),
    ("p-hun", "Hungarian",  "hun", r"(?i)(?:^| )(hu|hun|hungarian)(?= |$)"),
    ("p-ron", "Romanian",   "ron", r"(?i)(?:^| )(ro|ron|rum|romanian)(?= |$)"),
    ("p-ukr", "Ukrainian",  "ukr", r"(?i)(?:^| )(uk|ukr|ukrainian)(?= |$)"),
    ("p-ell", "Greek",      "ell", r"(?i)(?:^| )(el|ell|gre|greek)(?= |$)"),
    ("p-heb", "Hebrew",     "heb", r"(?i)(?:^| )(he|heb|hebrew)(?= |$)"),
    ("p-tha", "Thai",       "tha", r"(?i)(?:^| )(th|tha|thai)(?= |$)"),
    ("p-vie", "Vietnamese", "vie", r"(?i)(?:^| )(vi|vie|vietnamese)(?= |$)"),
    ("p-ind", "Indonesian", "ind", r"(?i)(?:^| )(id|ind|indonesian)(?= |$)"),
    ("p-msa", "Malay",      "msa", r"(?i)(?:^| )(ms|msa|may|malay)(?= |$)"),
    ("p-hrv", "Croatian",   "hrv", r"(?i)(?:^| )(hr|hrv|croatian)(?= |$)"),
    ("p-srp", "Serbian",    "srp", r"(?i)(?:^| )(sr|srp|serbian)(?= |$)"),
    ("p-bul", "Bulgarian",  "bul", r"(?i)(?:^| )(bg|bul|bulgarian)(?= |$)"),
    ("p-slk", "Slovak",     "slk", r"(?i)(?:^| )(sk|slk|slo|slovak)(?= |$)"),
    ("p-slv", "Slovenian",  "slv", r"(?i)(?:^| )(sl|slv|slovenian)(?= |$)"),
]

# Source context: text-only (no speaker icon), matches filename (word-boundary + script detection + emoji flags)
SOURCE_LANGUAGE_DEFS = [
    ("s-eng", "English",    "eng", r"(?i)\benglish\b|\beng\b|\ben\b|\U0001F1EC\U0001F1E7|\U0001F1FA\U0001F1F8"),
    ("s-pol", "Polish",     "pol", r"(?i)\bpolish\b|\bpol\b|\bpl\b|\U0001F1F5\U0001F1F1"),
    ("s-spa", "Spanish",    "spa", r"(?i)\bspanish\b|\bspa\b|\bes\b|\U0001F1EA\U0001F1F8"),
    ("s-fre", "French",     "fra", r"(?i)\bfrench\b|\bfra\b|\bfr\b|\bvff\b|\bvfq\b|\U0001F1EB\U0001F1F7"),
    ("s-ger", "German",     "deu", r"(?i)\bgerman\b|\bdeu\b|\bde\b|\U0001F1E9\U0001F1EA"),
    ("s-ita", "Italian",    "ita", r"(?i)\bitalian\b|\bita\b|\bit\b|\U0001F1EE\U0001F1F9"),
    ("s-por", "Portuguese", "por", r"(?i)\bportuguese\b(?![\s._-]?brazil)|\bpor\b|\bpt\b(?![\s._-]?br)|\U0001F1F5\U0001F1F9"),
    ("s-por-br", "Brazilian", "por-br", r"(?i)\bportuguese[\s._-]?brazil\b|\bpt[\s._-]?br\b|\bbrazilian\b|\U0001F1E7\U0001F1F7"),
    ("s-rus", "Russian",    "rus", r"(?i)\brussian\b|\brus\b|\bru\b|[\u0400-\u04FF]{3,}|\U0001F1F7\U0001F1FA"),
    ("s-jpn", "Japanese",   "jpn", r"(?i)\bjapanese\b|\bjpn\b|\bja\b|[\u3040-\u309F\u30A0-\u30FF]{3,}|\U0001F1EF\U0001F1F5"),
    ("s-kor", "Korean",     "kor", r"(?i)\bkorean\b|\bkor\b|\bko\b|[\uAC00-\uD7AF]{3,}|\U0001F1F0\U0001F1F7"),
    ("s-zho", "Chinese",    "zho", r"(?i)\bchinese\b|\bchi\b|\bzh\b|[\u4E00-\u9FFF]{3,}|\U0001F1E8\U0001F1F3"),
    ("s-hin", "Hindi",      "hin", r"(?i)\bhindi\b|\bhin\b|\bhi\b|[\u0900-\u097F]{3,}|\U0001F1EE\U0001F1F3"),
    ("s-ara", "Arabic",     "ara", r"(?i)\barabic\b|\bara\b|\bar\b|[\u0600-\u06FF]{3,}|\U0001F1F8\U0001F1E6"),
    ("s-tur", "Turkish",    "tur", r"(?i)\bturkish\b|\btur\b|\btr\b|\U0001F1F9\U0001F1F7"),
    ("s-dut", "Dutch",      "nld", r"(?i)\bdutch\b|\bnld\b|\bnl\b|\U0001F1F3\U0001F1F1"),
    ("s-swe", "Swedish",    "swe", r"(?i)\bswedish\b|\bswe\b|\bsv\b|\U0001F1F8\U0001F1EA"),
    ("s-nor", "Norwegian",  "nor", r"(?i)\bnorwegian\b|\bnor\b|\bno\b|\U0001F1F3\U0001F1F4"),
    ("s-dan", "Danish",     "dan", r"(?i)\bdanish\b|\bdan\b|\bda\b|\U0001F1E9\U0001F1F0"),
    ("s-fin", "Finnish",    "fin", r"(?i)\bfinnish\b|\bfin\b|\bfi\b|\U0001F1EB\U0001F1EE"),
    ("s-ces", "Czech",      "ces", r"(?i)\bczech\b|\bces\b|\bcze\b|\bcs\b|\U0001F1E8\U0001F1FF"),
    ("s-hun", "Hungarian",  "hun", r"(?i)\bhungarian\b|\bhun\b|\bhu\b|\U0001F1ED\U0001F1FA"),
    ("s-ron", "Romanian",   "ron", r"(?i)\bromanian\b|\bron\b|\brum\b|\bro\b|\U0001F1F7\U0001F1F4"),
    ("s-ukr", "Ukrainian",  "ukr", r"(?i)\bukrainian\b|\bukr\b|\buk\b|\U0001F1FA\U0001F1E6"),
    ("s-ell", "Greek",      "ell", r"(?i)\bgreek\b|\bell\b|\bgre\b|\bel\b|[\u0370-\u03FF]{3,}|\U0001F1EC\U0001F1F7"),
    ("s-heb", "Hebrew",     "heb", r"(?i)\bhebrew\b|\bheb\b|\bhe\b|[\u0590-\u05FF]{3,}|\U0001F1EE\U0001F1F1"),
    ("s-tha", "Thai",       "tha", r"(?i)\bthai\b|\btha\b|\bth\b|[\u0E00-\u0E7F]{3,}|\U0001F1F9\U0001F1ED"),
    ("s-vie", "Vietnamese", "vie", r"(?i)\bvietnamese\b|\bvie\b|\bvi\b|\U0001F1FB\U0001F1F3"),
    ("s-ind", "Indonesian", "ind", r"(?i)\bindonesian\b|\bind\b|\bid\b|\U0001F1EE\U0001F1E9"),
    ("s-msa", "Malay",      "msa", r"(?i)\bmalay\b|\bmsa\b|\bmay\b|\bms\b|\U0001F1F2\U0001F1FE"),
    ("s-hrv", "Croatian",   "hrv", r"(?i)\bcroatian\b|\bhrv\b|\bhr\b|\U0001F1ED\U0001F1F7"),
    ("s-srp", "Serbian",    "srp", r"(?i)\bserbian\b|\bsrp\b|\bsr\b|\U0001F1F7\U0001F1F8"),
    ("s-bul", "Bulgarian",  "bul", r"(?i)\bbulgarian\b|\bbul\b|\bbg\b|\U0001F1E7\U0001F1EC"),
    ("s-slk", "Slovak",     "slk", r"(?i)\bslovak\b|\bslk\b|\bslo\b|\bsk\b|\U0001F1F8\U0001F1F0"),
    ("s-slv", "Slovenian",  "slv", r"(?i)\bslovenian\b|\bslv\b|\bsl\b|\U0001F1F8\U0001F1EE"),
]

AVAILABLE_LOCALES = [
    "en", "ar", "bg", "bn", "cs", "de", "el", "es", "fr", "he", "hr", "hu",
    "id", "it", "ja", "nb", "nl", "pl", "pt", "pt-br", "ro", "ru", "sk",
    "tr", "ur", "vi", "iso",
]


def _svg_to_data_uri(svg_path):
    with open(svg_path, "rb") as f:
        return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()


def _svg_str_to_data_uri(svg_str):
    return "data:image/svg+xml;base64," + base64.b64encode(svg_str.encode()).decode()


def main():
    os.makedirs(FRAGMENTS_DIR, exist_ok=True)

    # Import vectorizer for static badge generation (font-independent SVGs)
    from badge_vec import vectorize_badge

    # ── Groups fragment ──
    with open(os.path.join(FRAGMENTS_DIR, "groups.json"), "w") as f:
        json.dump(GROUPS, f, indent=2)

    # ── Non-language filter fragments (vectorized) ──
    manifest_filters = []

    for fid, gid, name, pattern, asset_path in FILTERS:
        # Use vectorizer to produce font-independent SVG (<path> instead of <text>)
        svg_content = vectorize_badge(fid)
        if svg_content is None:
            # Fallback to raw file if vectorizer doesn't know this badge
            full_path = os.path.join(ASSETS_DIR, asset_path)
            if not os.path.exists(full_path):
                print(f"  WARN: missing {asset_path}")
                continue
            image_url = _svg_to_data_uri(full_path)
        else:
            image_url = _svg_str_to_data_uri(svg_content)

        fragment = {
            "id": fid, "groupId": gid, "name": name,
            "pattern": pattern,
            "imageURL": image_url,
            **BADGE_STYLE,
        }
        with open(os.path.join(FRAGMENTS_DIR, f"{fid}.json"), "w") as f:
            json.dump(fragment, f, indent=2)

        # Manifest entry (no base64, just metadata)
        manifest_filters.append({
            "id": fid,
            "groupId": gid,
            "name": name,
            "pattern": pattern,
            "assetPath": asset_path,
            "type": "static",
        })

    # ── Language filter fragments (per locale) ──
    lang_dir = os.path.join(FRAGMENTS_DIR, "lang")
    os.makedirs(lang_dir, exist_ok=True)

    for locale in AVAILABLE_LOCALES:
        locale_dir = os.path.join(lang_dir, locale)
        os.makedirs(locale_dir, exist_ok=True)

        for lid, en_name, iso3, pattern in LANGUAGE_DEFS:
            svg_path = os.path.join(ASSETS_DIR, "language", locale, "vectorized", f"{iso3}.svg")
            if not os.path.exists(svg_path):
                continue

            fragment = {
                "id": lid, "groupId": "lang", "name": en_name,
                "pattern": pattern,
                "imageURL": _svg_to_data_uri(svg_path),
                **BADGE_STYLE,
            }
            with open(os.path.join(locale_dir, f"{lid}.json"), "w") as f:
                json.dump(fragment, f, indent=2)

    # Language manifest entries
    for lid, en_name, iso3, pattern in LANGUAGE_DEFS:
        manifest_filters.append({
            "id": lid,
            "groupId": "lang",
            "name": en_name,
            "iso3": iso3,
            "pattern": pattern,
            "assetPath": f"language/{{locale}}/vectorized/{iso3}.svg",
            "type": "localized",
            "context": "player",
            "availableLocales": [
                loc for loc in AVAILABLE_LOCALES
                if os.path.exists(os.path.join(ASSETS_DIR, "language", loc, "vectorized", f"{iso3}.svg"))
            ],
        })

    # ── Source language filter fragments (text-only, per locale) ──
    for locale in AVAILABLE_LOCALES:
        locale_dir = os.path.join(lang_dir, locale)
        os.makedirs(locale_dir, exist_ok=True)

        for sid, en_name, iso3, pattern in SOURCE_LANGUAGE_DEFS:
            svg_path = os.path.join(ASSETS_DIR, "language", locale, "text-only", f"{iso3}.svg")
            if not os.path.exists(svg_path):
                continue

            fragment = {
                "id": sid, "groupId": "lang", "name": en_name,
                "pattern": pattern,
                "imageURL": _svg_to_data_uri(svg_path),
                **BADGE_STYLE,
            }
            with open(os.path.join(locale_dir, f"{sid}.json"), "w") as f:
                json.dump(fragment, f, indent=2)

    # Source language manifest entries
    for sid, en_name, iso3, pattern in SOURCE_LANGUAGE_DEFS:
        manifest_filters.append({
            "id": sid,
            "groupId": "lang",
            "name": en_name,
            "iso3": iso3,
            "pattern": pattern,
            "assetPath": f"language/{{locale}}/text-only/{iso3}.svg",
            "type": "localized",
            "context": "source",
            "availableLocales": [
                loc for loc in AVAILABLE_LOCALES
                if os.path.exists(os.path.join(ASSETS_DIR, "language", loc, "text-only", f"{iso3}.svg"))
            ],
        })

    # ── Write manifest ──
    manifest = {
        "version": 1,
        "groups": GROUPS,
        "filters": manifest_filters,
        "availableLocales": AVAILABLE_LOCALES,
        "style": BADGE_STYLE,
    }

    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Stats
    static_count = len([f for f in manifest_filters if f.get("type") == "static"])
    lang_count = len([f for f in manifest_filters if f.get("type") == "localized"])
    frag_files = sum(1 for _, _, files in os.walk(FRAGMENTS_DIR) for _ in files)

    # ── Generate bundles (one file per locale+context, for fast editor loading) ──
    bundles_dir = os.path.join(OUTPUT_DIR, "bundles")
    os.makedirs(bundles_dir, exist_ok=True)

    # Collect static fragments (same for all locales)
    static_fragments = {}
    for fid, gid, name, pattern, asset_path in FILTERS:
        frag_path = os.path.join(FRAGMENTS_DIR, f"{fid}.json")
        if os.path.exists(frag_path):
            with open(frag_path) as f:
                static_fragments[fid] = json.load(f)

    for locale in AVAILABLE_LOCALES:
        for ctx, prefix, lang_defs in [("player", "p-", LANGUAGE_DEFS), ("source", "s-", SOURCE_LANGUAGE_DEFS)]:
            bundle = dict(static_fragments)  # shallow copy
            for lid_or_sid, en_name, iso3, pattern in lang_defs:
                frag_path = os.path.join(FRAGMENTS_DIR, "lang", locale, f"{lid_or_sid}.json")
                if os.path.exists(frag_path):
                    with open(frag_path) as f:
                        bundle[lid_or_sid] = json.load(f)
            bundle_path = os.path.join(bundles_dir, f"{ctx}-{locale}.json")
            with open(bundle_path, "w") as f:
                json.dump(bundle, f, separators=(",", ":"), ensure_ascii=False)

    bundle_count = len(os.listdir(bundles_dir))

    print(f"Generated manifest: {manifest_path}")
    print(f"  {static_count} static filters + {lang_count} localized language filters")
    print(f"  {frag_files} fragment files in {FRAGMENTS_DIR}")
    print(f"  {bundle_count} bundles in {bundles_dir}")
    print(f"  {len(AVAILABLE_LOCALES)} locales available")


if __name__ == "__main__":
    main()
