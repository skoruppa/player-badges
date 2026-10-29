#!/usr/bin/env python3
"""
Update output JSONs after manually editing an SVG asset.

For badges with <text> elements: re-vectorizes text to <path> using FreeType.
For badges without <text> (e.g. IMAX Enhanced): encodes the SVG as-is.

Usage:
    python3 player-badges/scripts/update-badge-svg.py p-imax-e
    python3 player-badges/scripts/update-badge-svg.py p-4k p-1080p p-dv
    python3 player-badges/scripts/update-badge-svg.py --all

Requirements: freetype-py (only if updating badges that have <text> in their SVG)
"""

import argparse
import base64
import glob
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FRAGMENTS_DIR = os.path.join(OUTPUT_DIR, "fragments")

from badge_vec import STATIC_BADGES, vectorize_badge


# Language badges: ID → ISO 639-3 code
LANG_BADGES = {
    "p-eng": "eng", "p-pol": "pol", "p-spa": "spa", "p-fre": "fra",
    "p-ger": "deu", "p-ita": "ita", "p-por": "por", "p-rus": "rus",
    "p-jpn": "jpn", "p-kor": "kor", "p-zho": "zho", "p-hin": "hin",
    "p-ara": "ara", "p-tur": "tur", "p-dut": "nld", "p-swe": "swe",
    "p-nor": "nor", "p-dan": "dan", "p-fin": "fin", "p-ces": "ces",
    "p-hun": "hun", "p-ron": "ron", "p-ukr": "ukr", "p-ell": "ell",
    "p-heb": "heb", "p-tha": "tha", "p-vie": "vie", "p-ind": "ind",
    "p-msa": "msa", "p-hrv": "hrv", "p-srp": "srp", "p-bul": "bul",
    "p-slk": "slk", "p-slv": "slv",
}


def svg_to_data_uri(svg_content):
    """Encode SVG string as base64 data URI."""
    return "data:image/svg+xml;base64," + base64.b64encode(svg_content.encode()).decode()


def svg_file_to_data_uri(path):
    """Read SVG file and encode as base64 data URI."""
    with open(path, "rb") as f:
        return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()


def update_fragment(badge_id, data_uri):
    """Update output/fragments/<id>.json"""
    frag_path = os.path.join(FRAGMENTS_DIR, f"{badge_id}.json")
    if not os.path.exists(frag_path):
        return False
    with open(frag_path, "r") as f:
        data = json.load(f)
    data["imageURL"] = data_uri
    with open(frag_path, "w") as f:
        json.dump(data, f, indent=2)
    return True


def update_lang_fragments(badge_id, iso3):
    """Update output/fragments/lang/<locale>/<id>.json for all locales.
    Language SVGs in language/<locale>/vectorized/ are already vectorized."""
    lang_dir = os.path.join(FRAGMENTS_DIR, "lang")
    count = 0
    for locale in sorted(os.listdir(lang_dir)):
        svg_path = os.path.join(ASSETS_DIR, "language", locale, "vectorized", f"{iso3}.svg")
        frag_path = os.path.join(lang_dir, locale, f"{badge_id}.json")
        if not os.path.exists(svg_path) or not os.path.exists(frag_path):
            continue
        data_uri = svg_file_to_data_uri(svg_path)
        with open(frag_path, "r") as f:
            data = json.load(f)
        data["imageURL"] = data_uri
        with open(frag_path, "w") as f:
            json.dump(data, f, indent=2)
        count += 1
    return count


def update_full_jsons(badge_id, data_uri):
    """Update the badge in all output/player-badge*.json files."""
    count = 0
    for path in glob.glob(os.path.join(OUTPUT_DIR, "player-badge*.json")):
        with open(path, "r") as f:
            data = json.load(f)
        updated = False
        for filt in data.get("filters", []):
            if filt.get("id") == badge_id:
                filt["imageURL"] = data_uri
                updated = True
        if updated:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            count += 1
    return count


def process_badge(badge_id):
    """Process a single badge ID. Returns True if updated."""
    # Static badge
    if badge_id in STATIC_BADGES:
        svg_content = vectorize_badge(badge_id)
        if svg_content is None:
            print(f"  ✗ {badge_id}: vectorization failed")
            return False

        data_uri = svg_to_data_uri(svg_content)
        frag_ok = update_fragment(badge_id, data_uri)
        full_count = update_full_jsons(badge_id, data_uri)

        vec_type = STATIC_BADGES[badge_id][1]
        method = "as-is" if vec_type == "raw" else "vectorized"
        parts = []
        if frag_ok:
            parts.append("fragment")
        if full_count:
            parts.append(f"{full_count} full JSON(s)")
        print(f"  ✓ {badge_id}: {method}, updated {', '.join(parts)}")
        return True

    # Language badge
    if badge_id in LANG_BADGES:
        iso3 = LANG_BADGES[badge_id]
        locale_count = update_lang_fragments(badge_id, iso3)
        en_svg = os.path.join(ASSETS_DIR, "language", "en", "vectorized", f"{iso3}.svg")
        full_count = 0
        if os.path.exists(en_svg):
            full_count = update_full_jsons(badge_id, svg_file_to_data_uri(en_svg))
        print(f"  ✓ {badge_id}: updated {locale_count} locale fragment(s), {full_count} full JSON(s)")
        return True

    print(f"  ✗ {badge_id}: unknown badge ID")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Update output JSONs after editing an SVG asset.",
        epilog="Examples:\n"
               "  %(prog)s p-imax-e              # raw SVG, no FreeType needed\n"
               "  %(prog)s p-4k p-dv              # re-vectorizes text via FreeType\n"
               "  %(prog)s --all                  # rebuild all badges\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("ids", nargs="*", help="Badge IDs to update (e.g. p-imax-e p-4k)")
    parser.add_argument("--all", action="store_true", help="Re-encode all badges from assets")
    args = parser.parse_args()

    if not args.ids and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.all:
        badge_ids = list(STATIC_BADGES.keys()) + list(LANG_BADGES.keys())
    else:
        badge_ids = args.ids

    print(f"Updating {len(badge_ids)} badge(s)...\n")
    ok = 0
    for bid in badge_ids:
        if process_badge(bid):
            ok += 1

    print(f"\nDone: {ok}/{len(badge_ids)} updated.")


if __name__ == "__main__":
    main()
