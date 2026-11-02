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
    {"id": "rat",  "name": "Star Rating",   "isExpanded": True},
]

# Opt-in groups: left out of the API default and unselected in the editor
HIDDEN_GROUPS = ["rat"]

# Default display order per context (mirrors GROUP_ORDER in worker/index.js)
GROUP_ORDER = {
    "player": ["res", "hdr", "aud", "ch", "lang", "src", "spc", "rat"],
    "source": ["res", "src", "hdr", "aud", "ch", "spc", "lang", "rat"],
}

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
    ("p-ddp",     "aud", "Dolby Digital+", r"(?i)^(?!.*\bAtmos\b)(?!.*\bTrueHD\b).*(?:\bDD\+|\b(?:DDP|EAC3)\b)", "audio/dolby-digital-plus.svg"),
    ("p-dd",      "aud", "Dolby Digital",  r"(?i)^(?!.*\bAtmos\b)(?!.*\bTrueHD\b)(?!.*(?:\bDD\+|\b(?:DDP|EAC3)\b)).*\b(DD|AC3)\b", "audio/dolby-digital.svg"),
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
    ("p-61", "ch", "6.1", r"(?i)\b6\.1\b", "channels/6.1.svg"),
    ("p-51", "ch", "5.1", r"(?i)\b5\.1\b", "channels/5.1.svg"),
    ("p-20", "ch", "2.0", r"(?i)\b2\.0\b", "channels/2.0.svg"),
    ("p-10", "ch", "1.0", r"(?i)\b1\.0\b", "channels/1.0.svg"),
    # Source
    ("p-remux",  "src", "Remux",  r"(?i)\b(?:bd|uhd)?remux\b", "source/remux.svg"),
    ("p-bluray", "src", "BluRay", r"(?i)^(?=.*(?:blu[-_. ]?ray|\bb[dr][-_. ]?rip\b|\bbd(?:25|50|r|mv)?\b))(?!.*\b(?:bd|uhd)?remux\b)", "source/bluray.svg"),
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
    ("p-seadex", "spc", "SeaDex", r"(?i)\b(?:seadex|best[\s._-]?release|alt[\s._-]?(?:best[\s._-]?)?release)\b|\u200b\u200c\u200d|ᴀʟᴛ\s+ʀᴇʟᴇᴀsᴇ|ʙᴇsᴛ\s+ʀᴇʟᴇᴀsᴇ", "special/seadex.svg"),
]



def _star_pattern(rating):
    """AIOStreams ::star gives full stars plus one half star, and templates often turn the half
    into a single ☆. ::pstar pads with ☆, so two or more trailing ☆ are empty stars."""
    full = int(rating)
    tail = r"(?:⯪☆*|☆)" if rating != full else r"(?:☆☆+)?"
    return rf"(?<![★⯪☆])★{{{full}}}{tail}(?![★⯪☆])"


FILTERS += [
    (f"p-star{int(rating * 10):02d}", "rat", f"{rating} Stars", _star_pattern(rating), f"rating/{rating}.svg")
    for rating in (5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5)
]

# Source context overrides: filenames can list several formats at once, so every tag found
# gets its own badge. Lookarounds only tell apart tokens sharing a prefix (DTS vs DTS-HD),
# they never exclude another format. Codec tags use (?<![a-z0-9])...(?![a-z]) instead of \b
# because channels are often glued on (DDP5.1, AAC2.0).
# Filters not listed here use the same pattern in both contexts.
SOURCE_PATTERNS = {
    # Resolution: UHD alone says nothing about pixels (1080p UHD BluRay exists)
    "p-4k":      r"(?i)\b(?:2160p?|4k)\b|^(?!.*\b(?:1080|720)p?\b).*\b(?:uhd|ultra[ ._-]?hd)\b",
    "p-1080p":   r"(?i)\b(?:1080p?|fhd|full[ ._-]?hd)\b",
    "p-720p":    r"(?i)\b720p?\b",
    # HDR: "10bit" after HDR is bit depth, not HDR10
    "p-dv":      r"(?i)\b(DV|DoVi|Dolby[\s._-]?Vision)\b",
    "p-hdr10p":  r"(?i)\bHDR[\s._-]?10(?:\+|P(?![a-z0-9])|[\s._-]?plus\b)",
    "p-hdr10":   r"(?i)\bHDR[\s._-]?10(?![a-z0-9+]|[\s._-]?(?:plus|bit)\b)",
    "p-hlg":     r"(?i)\bHLG\b",
    "p-hdr":     r"(?i)\bHDR\b(?![\s._-]?10(?:P|plus)?(?![a-z0-9]|[\s._-]?bit\b))",
    # Audio
    "p-atmos":   r"(?i)\bAtmos\b|(?<![a-z0-9])DDPA(?![a-z])",
    "p-truehd":  r"(?i)(?<![a-z0-9])True[\s._-]?HD(?![a-z])",
    "p-ddp":     r"(?i)(?<![a-z0-9])(?:DD\+|DDPA?|E-?AC-?3|Dolby[\s._-]?Digital[\s._-]?Plus)(?![a-z])",
    "p-dd":      r"(?i)(?<![a-z0-9])(?:DD(?![a-z+])|(?<!E-)AC-?3(?![a-z])|Dolby[\s._-]?Digital(?![\s._-]?Plus)(?![a-z]))",
    "p-dtsx":    r"(?i)(?<![a-z0-9])DTS[\s._:-]?X(?![a-z0-9])",
    "p-dtshdma": r"(?i)(?<![a-z0-9])DTS[\s._-]?HD[\s._-]?(?:MA(?![a-z])|Master\b)",
    "p-dtshd":   r"(?i)(?<![a-z0-9])DTS[\s._-]?HD(?![a-z]|[\s._-]?(?:MA(?![a-z])|Master\b))",
    "p-dts":     r"(?i)(?<![a-z0-9])DTS(?![a-z]|[\s._:-]?(?:HD|X(?![a-z0-9])))",
    "p-flac":    r"(?i)(?<![a-z0-9])FLAC(?![a-z])",
    "p-opus":    r"(?i)(?<![a-z0-9])Opus(?![a-z])",
    "p-aac":     r"(?i)(?<![a-z0-9])AAC(?![a-z])",
    "p-ac4":     r"(?i)(?<![a-z0-9])AC-?4(?![a-z0-9])",
    # Channels: no \b (DDP5.1), and skip file sizes and bitrates from descriptions (5.1 GB)
    "p-71":      r"(?i)(?<!\d)7\.1(?!\d|\s*[kmgt]i?b)",
    "p-61":      r"(?i)(?<!\d)6\.1(?!\d|\s*[kmgt]i?b)",
    "p-51":      r"(?i)(?<!\d)5\.1(?!\d|\s*[kmgt]i?b)",
    "p-20":      r"(?i)(?<!\d)2\.0(?!\d|\s*[kmgt]i?b)",
    "p-10":      r"(?i)(?<!\d)1\.0(?!\d|\s*[kmgt]i?b)",
    # Source: Remux stays exclusive with BluRay, a remux is one source type, not two tags
    "p-webrip": r"(?i)\b(?:web|hd)[-_. ]?rip\b|(?<!bd[-_. ])(?<!br[-_. ])(?<!dvd[-_. ])(?<!tc[-_. ])(?<!ts[-_. ])(?<!cam[-_. ])\brip\b",
    "p-dvdrip":  r"(?i)\bdvd[\s._-]?rip\b",
    "p-cam":     r"(?i)\b(?:hd[-_. ]?)?cam(?:[-_. ]?rip)?\b|\b(?:hd[-_. ]?)?ts(?:[-_. ]?rip)?\b|\btelesync\b|\bp(?:re[\s._-]?)?dvd(?:rip)?\b|\b(?:hd[-_. ]?)?tc(?:[-_. ]?rip)?\b|\btelecine\b|(?<!dvd)(?<!dvd[-_. ])\bscr(?:eener)?\b",
    # Special
    "p-imax":    r"(?i)\bIMAX\b(?![\s._-]?enhanced)",
}

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
    ("s-eng", "English",    "eng", r"(?i)\benglish\b|\beng\b|\ben\b|🇬🇧|🇺🇸"),
    ("s-pol", "Polish",     "pol", r"(?i)\bpolish\b|\bpol\b|\bpl\b|🇵🇱"),
    ("s-spa", "Spanish",    "spa", r"(?i)\bspanish\b|\bspa\b|\bes\b|🇪🇸"),
    ("s-fre", "French",     "fra", r"(?i)\bfrench\b|\bfra\b|\bfr\b|\bvff\b|\bvfq\b|🇫🇷"),
    ("s-ger", "German",     "deu", r"(?i)\bgerman\b|\bdeu\b|\bde\b|🇩🇪"),
    ("s-ita", "Italian",    "ita", r"(?i)\bitalian\b|\bita\b|\bit\b|🇮🇹"),
    ("s-por", "Portuguese", "por", r"(?i)\bportuguese\b(?![\s._-]?brazil)|\bpor\b|\bpt\b(?![\s._-]?br)|🇵🇹"),
    ("s-por-br", "Brazilian", "por-br", r"(?i)\bportuguese[\s._-]?brazil\b|\bpt[\s._-]?br\b|\bbrazilian\b|🇧🇷"),
    ("s-rus", "Russian",    "rus", r"(?i)\brussian\b|\brus\b|\bru\b|[\u0400-\u04FF]{3,}|🇷🇺"),
    ("s-jpn", "Japanese",   "jpn", r"(?i)\bjapanese\b|\bjpn\b|\bja\b|[\u3040-\u309F\u30A0-\u30FF]{3,}|🇯🇵"),
    ("s-kor", "Korean",     "kor", r"(?i)\bkorean\b|\bkor\b|\bko\b|[\uAC00-\uD7AF]{3,}|🇰🇷"),
    ("s-zho", "Chinese",    "zho", r"(?i)\bchinese\b|\bchi\b|\bzh\b|[\u4E00-\u9FFF]{3,}|🇨🇳"),
    ("s-hin", "Hindi",      "hin", r"(?i)\bhindi\b|\bhin\b|\bhi\b|[\u0900-\u097F]{3,}|🇮🇳"),
    ("s-ara", "Arabic",     "ara", r"(?i)\barabic\b|\bara\b|\bar\b|[\u0600-\u06FF]{3,}|🇸🇦"),
    ("s-tur", "Turkish",    "tur", r"(?i)\bturkish\b|\btur\b|\btr\b|🇹🇷"),
    ("s-dut", "Dutch",      "nld", r"(?i)\bdutch\b|\bnld\b|\bnl\b|🇳🇱"),
    ("s-swe", "Swedish",    "swe", r"(?i)\bswedish\b|\bswe\b|\bsv\b|🇸🇪"),
    ("s-nor", "Norwegian",  "nor", r"(?i)\bnorwegian\b|\bnor\b|\bno\b|🇳🇴"),
    ("s-dan", "Danish",     "dan", r"(?i)\bdanish\b|\bdan\b|\bda\b|🇩🇰"),
    ("s-fin", "Finnish",    "fin", r"(?i)\bfinnish\b|\bfin\b|\bfi\b|🇫🇮"),
    ("s-ces", "Czech",      "ces", r"(?i)\bczech\b|\bces\b|\bcze\b|\bcs\b|🇨🇿"),
    ("s-hun", "Hungarian",  "hun", r"(?i)\bhungarian\b|\bhun\b|\bhu\b|🇭🇺"),
    ("s-ron", "Romanian",   "ron", r"(?i)\bromanian\b|\bron\b|\brum\b|\bro\b|🇷🇴"),
    ("s-ukr", "Ukrainian",  "ukr", r"(?i)\bukrainian\b|\bukr\b|\buk\b|🇺🇦"),
    ("s-ell", "Greek",      "ell", r"(?i)\bgreek\b|\bell\b|\bgre\b|\bel\b|[\u0370-\u03FF]{3,}|🇬🇷"),
    ("s-heb", "Hebrew",     "heb", r"(?i)\bhebrew\b|\bheb\b|\bhe\b|[\u0590-\u05FF]{3,}|🇮🇱"),
    ("s-tha", "Thai",       "tha", r"(?i)\bthai\b|\btha\b|\bth\b|[\u0E00-\u0E7F]{3,}|🇹🇭"),
    ("s-vie", "Vietnamese", "vie", r"(?i)\bvietnamese\b|\bvie\b|\bvi\b|🇻🇳"),
    ("s-ind", "Indonesian", "ind", r"(?i)\bindonesian\b|\bind\b|\bid\b|🇮🇩"),
    ("s-msa", "Malay",      "msa", r"(?i)\bmalay\b|\bmsa\b|\bmay\b|\bms\b|🇲🇾"),
    ("s-hrv", "Croatian",   "hrv", r"(?i)\bcroatian\b|\bhrv\b|\bhr\b|🇭🇷"),
    ("s-srp", "Serbian",    "srp", r"(?i)\bserbian\b|\bsrp\b|\bsr\b|🇷🇸"),
    ("s-bul", "Bulgarian",  "bul", r"(?i)\bbulgarian\b|\bbul\b|\bbg\b|🇧🇬"),
    ("s-slk", "Slovak",     "slk", r"(?i)\bslovak\b|\bslk\b|\bslo\b|\bsk\b|🇸🇰"),
    ("s-slv", "Slovenian",  "slv", r"(?i)\bslovenian\b|\bslv\b|\bsl\b|🇸🇮"),
]

# AIOStreams formatters print language codes through ::smallcaps ("ᴊᴀ · ᴇɴ"), which plain regexes
# cannot see. Subtitle codes share the format but sit in brackets, so those are skipped.
SMALL_CAPS = dict(zip(
    "abcdefghijklmnopqrstuvwxyz",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
))

SOURCE_LANGUAGE_CODES = {
    "s-eng": "en", "s-pol": "pl", "s-spa": "es", "s-fre": "fr", "s-ger": "de", "s-ita": "it",
    "s-por": "pt", "s-por-br": "pt-br", "s-rus": "ru", "s-jpn": "ja", "s-kor": "ko", "s-zho": "zh",
    "s-hin": "hi", "s-ara": "ar", "s-tur": "tr", "s-dut": "nl", "s-swe": "sv", "s-nor": "no",
    "s-dan": "da", "s-fin": "fi", "s-ces": "cs", "s-hun": "hu", "s-ron": "ro", "s-ukr": "uk",
    "s-ell": "el", "s-heb": "he", "s-tha": "th", "s-vie": "vi", "s-ind": "id", "s-msa": "ms",
    "s-hrv": "hr", "s-srp": "sr", "s-bul": "bg", "s-slk": "sk", "s-slv": "sl",
}


def _small_code(code):
    # Templates often swap ꜱ back to a plain s
    return "".join("[sꜱ]" if c == "s" else SMALL_CAPS.get(c, c) for c in code)


def _small_language_pattern(sid):
    code = _small_code(SOURCE_LANGUAGE_CODES[sid])
    if sid == "s-spa":
        code += "(?:-" + _small_code("mx") + ")?"
    return rf"(?:^|(?<=[\s·,/|]))" + code + rf"(?=$|[\s·,/|])(?![^()]*\))"


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


def _image_variants(base, bold, compact, bold_compact):
    """Variant images that differ from the base; the worker falls back to imageURL."""
    variants = {"bold": bold, "compact": compact, "boldCompact": bold_compact}
    return {key: uri for key, uri in variants.items() if uri != base}


def _lang_image(locale, subdir, iso3):
    return _svg_to_data_uri(os.path.join(ASSETS_DIR, "language", locale, subdir, f"{iso3}.svg"))


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
        if fid in SOURCE_PATTERNS:
            fragment["sourcePattern"] = SOURCE_PATTERNS[fid]
        if svg_content is not None:
            images = _image_variants(
                image_url,
                _svg_str_to_data_uri(vectorize_badge(fid, bold=True)),
                _svg_str_to_data_uri(vectorize_badge(fid, compact=True)),
                _svg_str_to_data_uri(vectorize_badge(fid, bold=True, compact=True)),
            )
            if images:
                fragment["images"] = images
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
                "images": _image_variants(
                    _svg_to_data_uri(svg_path),
                    _lang_image(locale, "vectorized-bold", iso3),
                    _lang_image(locale, "text-only", iso3),
                    _lang_image(locale, "text-only-bold", iso3),
                ),
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
            pattern = f"{pattern}|{_small_language_pattern(sid)}"
            svg_path = os.path.join(ASSETS_DIR, "language", locale, "text-only", f"{iso3}.svg")
            if not os.path.exists(svg_path):
                continue

            fragment = {
                "id": sid, "groupId": "lang", "name": en_name,
                "pattern": pattern,
                "imageURL": _svg_to_data_uri(svg_path),
                **BADGE_STYLE,
                "images": _image_variants(
                    _svg_to_data_uri(svg_path),
                    _lang_image(locale, "text-only-bold", iso3),
                    _lang_image(locale, "text-only", iso3),
                    _lang_image(locale, "text-only-bold", iso3),
                ),
            }
            with open(os.path.join(locale_dir, f"{sid}.json"), "w") as f:
                json.dump(fragment, f, indent=2)

    # Source language manifest entries
    for sid, en_name, iso3, pattern in SOURCE_LANGUAGE_DEFS:
        pattern = f"{pattern}|{_small_language_pattern(sid)}"
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
        "groupOrder": GROUP_ORDER,
        "hiddenGroups": HIDDEN_GROUPS,
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
