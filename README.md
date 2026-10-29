# Player Badges

Vectorized SVG badges for NuvioTV and NuvioMobile. Badges show playback info (resolution, codec, HDR, audio format, language, source quality) as small chips in the player controls overlay and source list.

**Live editor**: https://nuvio-badge-editor.pages.dev
**API**: https://nuvio-badges.skoruppa.workers.dev/v1/badge.json

## Two contexts

### Player context (`p-` prefix)
Badges matched against decoder info + filename. Language badges have speaker icon 🔊 and space-bounded regex (only matches `playbackMatchText` tokens, not filename).

### Source context (`s-` prefix)
Badges matched against stream filename/title. Language badges are text-only (no speaker icon) with word-boundary regex + script detection (e.g. `[가-힯]{3,}` for Korean characters in filename).

## Directory structure

```
player-badges/
  assets/
    resolution/              8K, 4K, 1440p, 1080p, 720p, 480p
    hdr/                     Dolby Vision, HDR10+, HDR10, HLG, HDR
    audio/                   Dolby Atmos/Digital+/Digital/TrueHD, DTS variants, FLAC, Opus, AAC, AC-4
    channels/                7.1, 5.1, 2.0, 1.0
    source/                  Remux, BluRay, WebDL, WebRip, HDTV, DVDScr, DVDRip, CAM, R5
    special/                 IMAX, IMAX Enhanced, SeaDex
    language/<locale>/
      vectorized/            Speaker icon + text (player context)
      text-only/             Text only (source context)
      preview/               Preview SVGs with <text> (for editing, not shipped)
  icons/                     Source SVG icons (disc, globe, tv, dvd, camera, imax)
  output/
    manifest.json            Badge catalog (no base64)
    fragments/               Per-filter JSON with base64 imageURL
    bundles/                 Pre-built bundles per locale+context (for fast editor loading)
    player-badge.json        Full test JSON (English)
    player-badge-iso.json    Full test JSON (ISO codes)
    player-badge-pl.json     Full test JSON (Polish)
  scripts/
    badge_vec.py             Shared vectorization module (FreeType)
    generate-badge-json.py   Full test JSON generator
    generate-language-assets.py  Language SVG generator (all locales)
    generate-manifest.py     Manifest + fragments + bundles generator
    update-badge-svg.py      Update individual badges after manual SVG edits
    dev-server.js            Local dev server (API + editor)
    deploy-worker.sh         Deploy API worker + KV upload
    deploy-pages.sh          Deploy web editor to Cloudflare Pages
    deploy-all.sh            Full pipeline (regenerate + deploy everything)
  web/
    index.html               Badge editor (HTML shell)
    app.js                   Editor logic
    style.css                Editor styles
    i18n.js                  UI translations (22 languages)
  worker/
    index.js                 Cloudflare Worker (badge API)
    wrangler.toml            Worker config
  drafts/                    Test files, screenshots
```

## SVG design

- **ViewBox**: 14px height, variable width
- **Font**: Roboto Medium (9px), vectorized as `<path>` curves (font-independent, works on all platforms including iOS)
- **Non-Latin scripts**: Noto Sans fallback chain (Arabic, Hebrew, CJK, Devanagari, Bengali, Thai, Greek)
- **Icons**: Inline SVG shapes (Dolby DD logo, speaker with waves, disc, globe, TV, camera, IMAX logo)
- **Colors**: White fill on transparent background
- **Padding**: 4px left, 3px right
- **No hinting**: `FT_LOAD_NO_HINTING` for even letter spacing at small sizes

## API

### URL scheme
```
GET /v1/badge.json?l=en&g=res,hdr,aud,ch,lang
GET /v1/badge.json?l=pl&g=res,hdr,aud,ch,lang&c=source
GET /v1/badge.json?l=en&g=res,hdr&x=p-480p,p-hlg&go=hdr,res
```

### Parameters
| Param | Description | Default |
|---|---|---|
| `l` | Locale (en, pl, de, ja, iso...) | `en` |
| `c` | Context: `player` or `source` | `player` |
| `g` | Group IDs to include (comma-separated) | `res,hdr,aud,ch,lang` |
| `x` | Badge IDs to exclude | — |
| `go` | Group display order (when reordered) | — |
| `o.{gid}` | Badge order within group (e.g. `o.lang=s-pol,s-eng`) | — |
| `s` | Style: `bordered`, `filled`, `none` | `filled` |
| `tc` | Tag color (#AARRGGBB) | `#00000000` |
| `bc` | Border color (#AARRGGBB) | `#FFFFFFFF` |

### Caching
- **Cloudflare edge cache**: 30 days (`CDN-Cache-Control: max-age=2592000`)
- **Browser cache**: 1 day (`Cache-Control: max-age=86400`)
- Each unique URL = unique cache key (normalized, params sorted)
- Second request to same URL from same PoP: `cf-cache-status: HIT`, worker not invoked

### Groups
| ID | Name | Badges |
|---|---|---|
| `res` | Resolution | 8K, 4K, 1440p, 1080p, 720p, 480p |
| `hdr` | HDR / Vision | Dolby Vision, HDR10+, HDR10, HLG, HDR |
| `aud` | Audio Format | Atmos, TrueHD, DD+, DD, DTS:X, DTS-HD MA, DTS-HD, DTS, FLAC, Opus, AAC, AC-4 |
| `ch` | Channels | 7.1, 5.1, 2.0, 1.0 |
| `src` | Source | Remux, BluRay, WebDL, WebRip, HDTV, DVDScr, DVDRip, CAM, R5 |
| `spc` | Special | IMAX Enhanced, IMAX, SeaDex |
| `lang` | Language | 34 languages × 27 locales |

## Scripts

### Daily workflow

```bash
# Edit an SVG in Inkscape, then update just that badge:
python3 scripts/update-badge-svg.py p-imax-e

# Regenerate everything and deploy:
bash scripts/deploy-all.sh
```

### Individual scripts

| Script | Purpose |
|---|---|
| `generate-language-assets.py` | Generate vectorized language SVGs for all locales (requires FreeType + Babel) |
| `generate-badge-json.py` | Generate full test JSONs (player-badge.json etc.) |
| `generate-manifest.py` | Generate manifest + fragments + bundles |
| `update-badge-svg.py` | Update output after manual SVG edit (`--all` for all badges) |
| `dev-server.js` | Local dev server: `node scripts/dev-server.js [port]` |
| `deploy-worker.sh` | Upload KV + deploy worker (`--skip-kv` to skip KV) |
| `deploy-pages.sh` | Deploy web editor to Cloudflare Pages |
| `deploy-all.sh` | Full pipeline: regenerate → KV → worker → Pages |

### Requirements
- Python 3.8+: `pip install -r requirements.txt` (freetype-py, babel)
- Node.js 18+ (for dev server)
- Wrangler CLI (for Cloudflare deploy): `npm install -g wrangler`
- Fonts included in `fonts/` (Roboto Apache 2.0, Noto Sans OFL 1.1)

## App integration

### NuvioTV
- `PlayerBadges.kt` — `rememberPlayerBadges()` builds merged candidate, matches against filters
- `PlaybackMatchText.kt` — generates synthetic tokens from decoder info
- `PlayerMediaInfo.kt` — reads codec/HDR/channel info from ExoPlayer and mpv
- `StreamImportedBadgeChip.kt` — renders the badge chip UI

### NuvioMobile
- Same architecture in `composeApp/src/commonMain/.../player/`

### Chip rendering
- Chip height: 20dp, image height: ~16dp
- Image width: min 34dp, max 92dp
- `ContentScale.Fit`, `tagColor: #00000000` = transparent (SVG content only)

## Localization notes

- 27 UI locales for language badge labels
- `pt` (Portugal) and `pt-br` (Brazil) have distinct translations: Polaco/Polonês, Checo/Tcheco
- Non-Latin scripts use Noto Sans fallback (Arabic, Hebrew, CJK, Devanagari, Bengali, Thai, Greek)
- ISO locale uses 3-letter codes (ENG, POL, SPA)
