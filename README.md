# Player Badges

Vectorized SVG badges for NuvioTV and NuvioMobile. Badges show playback info (resolution, HDR, audio format, channels, language, source quality) as small chips in the player controls overlay and source list.

**Live editor**: https://nuvio-badge-editor.pages.dev
**API**: https://nuvio-badges.skoruppa.workers.dev/v1/badge.json

## Two contexts

### Player context (`p-` prefix)
Shows what is playing right now. Badges match decoder tokens first; a group with no decoder hit falls back to the filename and stream name, so `pattern` must stay exclusive within a group. Source and Special always come from those names, because the decoder cannot report them. The stream description is not available here. Language badges have speaker icon 🔊 and space-bounded regex (only matches `playbackMatchText` tokens, not filename).

### Source context (`s-` prefix)
Badges matched against stream filename, name, title and description. Language badges are text-only (no speaker icon) with word-boundary regex + script detection (e.g. `[가-힯]{3,}` for Korean characters in filename).

Non-language badges share `p-` IDs and SVGs with the player context, but every tag found gets its own badge (e.g. Dolby Vision + HDR10+, TrueHD + Atmos). The worker swaps `pattern` for `sourcePattern` when `c=source`; overrides live in `SOURCE_PATTERNS` in `generate-manifest.py`.

## Directory structure

```
player-badges/
  assets/
    resolution/              8K, 4K, 1440p, 1080p, 720p, 480p
    hdr/                     Dolby Vision, HDR10+, HDR10, HLG, HDR
    audio/                   Dolby Atmos/Digital+/Digital/TrueHD, DTS variants, FLAC, Opus, AAC, AC-4
    channels/                7.1, 6.1, 5.1, 2.0, 1.0
    source/                  Remux, BluRay, WebDL, WebRip, HDTV, DVDRip, DVDScr, CAM, R5
    special/                 IMAX, IMAX Enhanced, SeaDex
    network/                 Streaming service wordmarks (Netflix, Prime Video, Disney+...)
    language/<locale>/
      vectorized/            Speaker icon + text (player context)
      text-only/             Text only (source context, compact player)
      vectorized-bold/       Bold variant of vectorized/
      text-only-bold/        Bold variant of text-only/
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
    deploy-worker.sh         Deploy API worker + KV upload + cache purge
    upload-kv.py             Build bundles and upload changed ones to KV
    deploy-pages.sh          Deploy web editor to Cloudflare Pages
    deploy-all.sh            Full pipeline (regenerate + deploy everything)
  web/
    index.html               Badge editor (HTML shell)
    app.js                   Editor logic
    style.css                Editor styles
    i18n.js                  UI translations (18 languages)
  worker/
    index.js                 Cloudflare Worker (badge API)
    wrangler.toml            Worker config
  fonts/                     Bundled fonts (Roboto, Noto Sans) — see fonts/README.md
```

## SVG design

- **ViewBox**: 14px height, variable width
- **Font**: Roboto Medium (9px), Roboto Bold for the bold variant, vectorized as `<path>` curves (font-independent, works on all platforms including iOS)
- **Non-Latin scripts**: Noto Sans fallback chain (Arabic, Hebrew, CJK, Devanagari, Bengali, Tamil, Telugu, Malayalam, Thai, Greek), with bold counterparts
- **Dolby**: DD logo with the full name; compact uses the boxed Dolby mark with a short uppercase label (VISION, ATMOS, DIGITAL+)
- **Variants**: Fragments carry `images` (`bold`, `compact`, `boldCompact`); the worker swaps one into `imageURL`
- **Icons**: Inline SVG shapes (Dolby DD logo, speaker with waves, disc, globe, TV, camera, IMAX logo)
- **Colors**: White fill on transparent background
- **Padding**: 4px left, 3px right
- **Complex scripts**: Arabic, Hebrew, Bengali etc. are shaped with HarfBuzz (joined letters, RTL order, conjuncts); Roboto text is not, so its spacing stays unchanged
- **No hinting**: `FT_LOAD_NO_HINTING` for even letter spacing at small sizes

## API

### URL scheme
```
GET /v1/badge.json?l=en&g=res,hdr,aud,ch,lang
GET /v1/badge.json?l=pl&g=res,hdr,aud,ch,lang&c=source
GET /v1/badge.json?l=en&g=res,hdr&x=p-480p,p-hlg&go=hdr,res
GET /v1/badge.json?l=en&c=source&b=1&cp=1&p=gold
```

### Parameters
| Param | Description | Default |
|---|---|---|
| `l` | Locale (en, pl, de, ja, iso...) | `en` |
| `c` | Context: `player` or `source` | `player` |
| `g` | Group IDs to include (comma-separated) | all groups except opt-in `rat` and `net` |
| `x` | Badge IDs to exclude | — |
| `go` | Group display order (when reordered) | player: `res,hdr,aud,ch,lang,src,spc,net,rat`<br>source: `res,src,hdr,aud,ch,spc,lang,net,rat` |
| `o.{gid}` | Badge order within group (e.g. `o.lang=s-pol,s-eng`) | — |
| `s` | Style: `bordered`, `filled`, `none` | `bordered` |
| `b` | Bold text (`1`); logos stay unchanged | off |
| `cp` | Compact: no icons, Dolby as boxed mark + short label (`1`) | off |
| `p` | Color preset: `colorful`, `neon`, `stealth`, `gold`; replaces `tc`, `bc` and `ic` | — |
| `tc` | Tag color (#AARRGGBB) | `#00000000` |
| `bc` | Border color (#AARRGGBB) | `#FFFFFFFF` |
| `ic` | Badge content color (#RRGGBB) | `#ffffff` |

Without `go`, groups always follow the context default, whatever the order in `g`.

### Caching
- **Cloudflare edge cache**: 1 year (`CDN-Cache-Control: max-age=31536000`), purged on every worker deploy
- **Browser cache**: 1 hour (`Cache-Control: max-age=3600`)
- Each unique URL string = unique cache key; the worker does not normalize parameter order
- Second request to same URL from same PoP: `cf-cache-status: HIT`, worker not invoked

### Groups
| ID | Name | Badges |
|---|---|---|
| `res` | Resolution | 8K, 4K, 1440p, 1080p, 720p, 480p |
| `hdr` | HDR / Vision | Dolby Vision, HDR10+, HDR10, HLG, HDR |
| `aud` | Audio Format | Atmos, TrueHD, DD+, DD, DTS:X, DTS-HD MA, DTS-HD, DTS, FLAC, Opus, AAC, AC-4 |
| `ch` | Channels | 7.1, 6.1, 5.1, 2.0, 1.0 |
| `src` | Source | Remux, BluRay, WebDL, WebRip, HDTV, DVDRip, DVDScr, CAM, R5 |
| `spc` | Special | IMAX Enhanced, IMAX, SeaDex |
| `lang` | Language | 38 languages × 30 locales |
| `net` | Networks (opt-in, request it with `g=`) | Netflix, Prime Video, Apple TV, Disney+, HBO Max, Hulu, Peacock, Paramount+, Crave, Crunchyroll |
| `rat` | Star Rating (opt-in, request it with `g=`) | 5 down to 0.5 in half steps, read from AIOStreams `::star` text in the stream name |

### Networks
Network badges read release tags. Unique tags (`NFLX`, `AMZN`, `ATVP`, `DSNP`, `HMAX`, `HULU`, `PCOK`, `PMTP`, `CRAV`) and full names (`Netflix`, `Prime Video`, `Apple TV`, `Disney+`, `HBO Max`, `Paramount+`, `Crunchyroll`) match anywhere. Short codes and plain words that also appear in titles (`NF`, `MAX`, `CR`, `HBO`, `Amazon`, `Disney`, `Peacock`, `Paramount`, `Crave`) match only right before `WEB`, `WEB-DL` or `WEBRip`, and `MAX` only in capitals.

The wordmarks come from Wikimedia Commons, where they are tagged `PD-textlogo` and trademarked. Each one is flattened to a single white path, so it follows the icon color and presets, and stays the same in bold and compact variants. The Disney+ arc, the Peacock dots and the Prime Video smile are left out, Paramount+ is the wordmark only and HBO Max is the horizontal lockup.

Logos are trademarks of their owners and only show where a release comes from. Nuvio is not affiliated with these services.

## Scripts

### Daily workflow

```bash
# Edit an SVG in Inkscape, then update just that badge:
python3 scripts/update-badge-svg.py p-imax-e

# Regenerate manifest + fragments and deploy:
bash scripts/deploy-all.sh
```

`deploy-all.sh` does not run `generate-language-assets.py`, so run that first after changing languages or translations.

### Deploying

- **Cache purge key**: put `PURGE_KEY=...` in a git-ignored `.env`, matching the worker secret set with `wrangler secret put PURGE_KEY`. Without it the deploy skips the purge and prints a warning.
- **KV bundles**: `upload-kv.py` builds `bundle/<context>/<locale>/<variant>` from `output/fragments/`, 240 entries in total. A request costs one KV read, and a change to a shared badge rewrites all bundles.
- **KV write limit**: the free plan limits writes per day, so only changed bundles are uploaded. `--skip-kv` and `deploy-pages.sh` do not write to KV.
- **Worker and KV format**: upload KV first when the bundle format changes, because `--skip-kv` deploys a worker that expects bundles already in KV.
- **After a deploy**: KV reads can lag for about a minute, so `upload-kv.py --dry-run` may briefly report everything as changed.
- **Apps**: an imported URL keeps its filters, so users must import it again to get changes.

### Adding a badge

Nothing keeps these lists in sync, so update each one:

1. `FILTERS` in `generate-manifest.py` and `SOURCE_PATTERNS` if the source regex differs
2. `STATIC_BADGES` in `badge_vec.py`
3. `GROUP_FILTERS` in `worker/index.js` and `scripts/dev-server.js`
4. `PRESETS` in `worker/index.js` and `web/app.js` for per-badge colors
5. Group lists: `GROUP_ORDER` in `worker/index.js`, `scripts/dev-server.js` and `generate-manifest.py` when adding a group

### Individual scripts

| Script | Purpose |
|---|---|
| `generate-language-assets.py` | Generate vectorized language SVGs for all locales (requires FreeType, Babel and HarfBuzz) |
| `generate-badge-json.py` | Generate full test JSONs (player-badge.json etc.) |
| `generate-manifest.py` | Generate manifest + fragments + bundles |
| `update-badge-svg.py` | Update output after manual SVG edit (`--all` for all badges) |
| `dev-server.js` | Local dev server: `node scripts/dev-server.js [port]`, editor at `/`; no `p` or `ic` support |
| `deploy-worker.sh` | Upload changed KV bundles + deploy worker (`--skip-kv` to skip KV, `--full` to upload everything) |
| `upload-kv.py` | Build KV bundles and upload only changed ones, tracked under `_deployed` (`--dry-run` to preview) |
| `deploy-pages.sh` | Deploy web editor to the production Pages branch |
| `deploy-all.sh` | Full pipeline: manifest → KV → worker → cache purge → Pages |

### Requirements
- Python 3.8+: `pip install -r requirements.txt` (freetype-py, babel, uharfbuzz)
- Node.js 18+ (for dev server)
- Wrangler CLI (for Cloudflare deploy): `npm install -g wrangler`
- Fonts included in `fonts/` (Roboto Apache 2.0, Noto Sans OFL 1.1)

## App integration

### NuvioTV
- `PlayerBadges.kt` — `rememberPlayerBadges()` collects playback and name candidates
- `StreamBadgeRules.kt` — filter import, `StreamBadgeMatcher` and two-phase player matching
- `PlaybackMatchText.kt` — generates synthetic tokens from decoder info
- `PlayerMediaInfo.kt` — reads codec/HDR/channel info from ExoPlayer and mpv
- `StreamBadgeChips.kt` — `StreamImportedBadgeChip` renders the badge chip UI

### NuvioMobile
- Same architecture in `composeApp/src/commonMain/.../features/player/` and `features/streams/`

### Chip rendering
- Chip height: 20dp, image height: ~16dp
- Image width (NuvioTV): min 34dp, max 92dp, so short compact labels keep side margins
- `ContentScale.Fit`; `tagColor` is drawn only with `tagStyle: filled`

## Localization notes

- 30 UI locales for language badge labels
- Brazilian Portuguese (`pt-BR`) is a separate badge from European Portuguese (`pt`) in both contexts
- `pt` (Portugal) and `pt-br` (Brazil) UI locales have distinct translations: Polaco/Polonês, Checo/Tcheco
- Source language regex also matches AIOStreams `::smallcaps` codes (`ᴊᴀ · ᴇɴ`), skipping subtitle codes in brackets
- Source language regex includes emoji flag matching (🇵🇱, 🇬🇧, 🇧🇷, etc.) and script detection (CJK, Cyrillic, Arabic)
- Non-Latin scripts use Noto Sans fallback (Arabic, Hebrew, CJK, Devanagari, Bengali, Tamil, Telugu, Malayalam, Thai, Greek), shaped with HarfBuzz
- ISO locale uses 3-letter codes (ENG, POL, SPA)
