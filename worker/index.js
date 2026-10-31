/**
 * Cloudflare Worker - Dynamic Badge JSON API
 *
 * Assembles a badge JSON from KV-stored fragments based on URL parameters.
 * Cache-friendly: each unique URL = unique cache key.
 *
 * URL: /v1/badge.json?l=en&g=res,hdr,aud,ch,lang
 *
 * Parameters:
 *   l      - locale for language badges (en, pl, de, ja, iso...)
 *   c      - context: 'player' (default) or 'source'
 *   g      - comma-separated group IDs to include
 *   x      - (optional) comma-separated badge IDs to exclude from groups
 *   go     - (optional) group display order (only when reordered)
 *   o.{gid}- (optional) badge order within a group, e.g. o.res=p-4k,p-1080p
 *   s      - tag style: filled, bordered, none
 *   tc     - tag color (#AARRGGBB)
 *   bc     - border color (#AARRGGBB)
 *
 * Deploy: wrangler deploy
 * KV namespace: BADGE_FRAGMENTS (bind in wrangler.toml)
 */

const GROUPS = [
  { id: "res", name: "Resolution", isExpanded: true },
  { id: "hdr", name: "HDR / Vision", isExpanded: true },
  { id: "aud", name: "Audio Format", isExpanded: true },
  { id: "ch", name: "Channels", isExpanded: true },
  { id: "src", name: "Source", isExpanded: true },
  { id: "spc", name: "Special", isExpanded: true },
  { id: "lang", name: "Language", isExpanded: true },
];

// Map group -> ordered list of filter IDs (player context)
const GROUP_FILTERS = {
  res: ["p-8k", "p-4k", "p-1440p", "p-1080p", "p-720p", "p-480p"],
  hdr: ["p-dv", "p-hdr10p", "p-hdr10", "p-hlg", "p-hdr"],
  aud: ["p-atmos", "p-truehd", "p-ddp", "p-dd", "p-dtsx", "p-dtshdma", "p-dtshd", "p-dts", "p-flac", "p-opus", "p-aac", "p-ac4"],
  ch: ["p-71", "p-51", "p-20", "p-10"],
  src: ["p-remux", "p-bluray", "p-webdl", "p-webrip", "p-hdtv", "p-dvdscr", "p-dvdrip", "p-cam", "p-r5"],
  spc: ["p-imax-e", "p-imax", "p-seadex"],
  lang: [
    "p-eng", "p-pol", "p-spa", "p-fre", "p-ger", "p-ita", "p-por", "p-por-br", "p-rus",
    "p-jpn", "p-kor", "p-zho", "p-hin", "p-ara", "p-tur", "p-dut", "p-swe",
    "p-nor", "p-dan", "p-fin", "p-ces", "p-hun", "p-ron", "p-ukr", "p-ell",
    "p-heb", "p-tha", "p-vie", "p-ind", "p-msa", "p-hrv", "p-srp", "p-bul",
    "p-slk", "p-slv",
  ],
};

// Source context: text-only badges, filename-matching regex
const SOURCE_LANG_FILTERS = [
  "s-eng", "s-pol", "s-spa", "s-fre", "s-ger", "s-ita", "s-por", "s-por-br", "s-rus",
  "s-jpn", "s-kor", "s-zho", "s-hin", "s-ara", "s-tur", "s-dut", "s-swe",
  "s-nor", "s-dan", "s-fin", "s-ces", "s-hun", "s-ron", "s-ukr", "s-ell",
  "s-heb", "s-tha", "s-vie", "s-ind", "s-msa", "s-hrv", "s-srp", "s-bul",
  "s-slk", "s-slv",
];

// All lang filter IDs (for KV key lookup)
const ALL_LANG_IDS = new Set([...GROUP_FILTERS.lang, ...SOURCE_LANG_FILTERS]);

// Presets — per style variant colors + per-badge overrides
const PRESETS = {
  colorful: {
    bordered: { bc: '#FFFFFFFF', tc: '#00000000', ic: '#ffffff' },
    filled: { bc: '#00000000', tc: '#CC000000', ic: '#ffffff' },
    badgeColors: {
      'p-remux': '#ff6600', 'p-bluray': '#dd8800', 'p-webdl': '#ccaa00', 'p-webrip': '#ccaa00',
      'p-hdtv': '#888888', 'p-dvdscr': '#666666', 'p-dvdrip': '#666666', 'p-cam': '#555555', 'p-r5': '#555555',
      'p-8k': '#00ee55', 'p-4k': '#33cc44', 'p-1440p': '#55aa44', 'p-1080p': '#778844', 'p-720p': '#888855', 'p-480p': '#777766',
      'p-imax-e': '#ff3333', 'p-imax': '#ff3333', 'p-seadex': '#44ddaa',
      'p-dv': '#55aaff', 'p-hdr10p': '#55aaff', 'p-hdr10': '#55aaff', 'p-hlg': '#55aaff', 'p-hdr': '#55aaff',
      'p-atmos': '#999999', 'p-truehd': '#999999', 'p-ddp': '#888888', 'p-dd': '#888888',
      'p-dtsx': '#999999', 'p-dtshdma': '#999999', 'p-dtshd': '#888888', 'p-dts': '#888888',
      'p-flac': '#888888', 'p-opus': '#888888', 'p-aac': '#777777', 'p-ac4': '#777777',
      'p-71': '#888888', 'p-51': '#888888', 'p-20': '#777777', 'p-10': '#777777',
    }
  },
  neon: {
    bordered: { bc: '#CC00ffcc', tc: '#00000000', ic: '#00ffcc' },
    filled: { bc: '#0000ffcc', tc: '#CC003333', ic: '#00ffcc' },
    badgeColors: {}
  },
  stealth: {
    bordered: { bc: '#33ffffff', tc: '#00000000', ic: '#aaaaaa' },
    filled: { bc: '#1Affffff', tc: '#1Affffff', ic: '#aaaaaa' },
    badgeColors: {}
  },
  gold: {
    bordered: { bc: '#FFd4a843', tc: '#00000000', ic: '#d4a843' },
    filled: { bc: '#FFd4a843', tc: '#66d4a843', ic: '#d4a843' },
    badgeColors: {}
  },
};

function toArgb(hex, opacity) {
  const alpha = Math.round(opacity * 2.55).toString(16).padStart(2, '0').toUpperCase();
  return '#' + alpha + hex.replace('#', '').toUpperCase();
}

function recolorSvg(base64DataUri, color) {
  if (color === '#ffffff' || color === '#FFFFFF') return base64DataUri;
  const svg = atob(base64DataUri.split(',')[1]);
  const hex = color.toLowerCase();
  const r = svg
    .replace(/fill="white"/g, `fill="${hex}"`)
    .replace(/fill="#ffffff"/gi, `fill="${hex}"`)
    .replace(/fill:#ffffff/gi, `fill:${hex}`)
    .replace(/stroke="white"/g, `stroke="${hex}"`)
    .replace(/stroke:#ffffff/gi, `stroke:${hex}`);
  return 'data:image/svg+xml;base64,' + btoa(r);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Purge cache endpoint (POST /v1/purge?key=<secret>)
    if (url.pathname === "/v1/purge" && request.method === "POST") {
      const key = url.searchParams.get("key");
      if (key !== env.PURGE_KEY) {
        return new Response("Forbidden", { status: 403 });
      }
      await ctx.cache.purge({ purgeEverything: true });
      return new Response(JSON.stringify({ ok: true, message: "Cache purged" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // Only handle /v1/badge.json
    if (url.pathname !== "/v1/badge.json") {
      return new Response("Not found", { status: 404 });
    }

    // Parse params
    const locale = url.searchParams.get("l") || "en";
    const context = url.searchParams.get("c") || "player";
    const groupsParam = url.searchParams.get("g") || "res,hdr,aud,ch,src,spc,lang";
    const excludeParam = url.searchParams.get("x");
    const groupOrderParam = url.searchParams.get("go");
    const style = url.searchParams.get("s") || "bordered";
    const presetName = url.searchParams.get("p");
    const preset = presetName ? PRESETS[presetName] : null;
    const presetVariant = preset ? (preset[style] || preset.bordered) : null;

    const tc = presetVariant ? presetVariant.tc : decodeURIComponent(url.searchParams.get("tc") || "#00000000");
    const bc = presetVariant ? presetVariant.bc : decodeURIComponent(url.searchParams.get("bc") || "#FFFFFFFF");
    const ic = presetVariant ? presetVariant.ic : decodeURIComponent(url.searchParams.get("ic") || "#ffffff");
    const presetBadgeColors = preset ? (preset.badgeColors || {}) : {};

    // Build effective group filters map (swap lang based on context)
    const effectiveFilters = { ...GROUP_FILTERS };
    if (context === "source") {
      effectiveFilters.lang = SOURCE_LANG_FILTERS;
    }

    // Determine group order: go= overrides default
    let orderedGroups;
    if (groupOrderParam) {
      orderedGroups = groupOrderParam.split(",").map(s => s.trim());
    } else {
      orderedGroups = groupsParam.split(",").map(s => s.trim());
    }

    const requestedGroups = new Set(groupsParam.split(",").map(s => s.trim()));
    const excludeSet = excludeParam ? new Set(excludeParam.split(",").map(s => s.trim())) : new Set();

    // Per-group badge order overrides: o.res=p-4k,p-1080p
    const badgeOrderOverrides = {};
    for (const [key, value] of url.searchParams.entries()) {
      if (key.startsWith("o.")) {
        const gid = key.substring(2);
        badgeOrderOverrides[gid] = value.split(",").map(s => s.trim());
      }
    }

    // Build filter IDs in correct order
    let filterIds = [];
    for (const gid of orderedGroups) {
      if (!requestedGroups.has(gid)) continue;
      const defaultIds = effectiveFilters[gid];
      if (!defaultIds) continue;

      // Use custom order if provided, otherwise default
      const ids = badgeOrderOverrides[gid] || defaultIds;
      filterIds.push(...ids);
    }
    filterIds = filterIds.filter(id => !excludeSet.has(id));

    // Load fragments from KV
    const filters = [];
    for (const id of filterIds) {
      let kvKey;
      if (ALL_LANG_IDS.has(id)) {
        kvKey = `lang/${locale}/${id}`;
      } else {
        kvKey = id;
      }

      const data = await env.BADGE_FRAGMENTS.get(kvKey, "json");
      if (!data) continue;

      // Apply style overrides
      const badgeColor = presetBadgeColors[id];
      data.tagStyle = style;
      if (badgeColor) {
        data.borderColor = style === 'filled' ? toArgb(badgeColor, 80) : toArgb(badgeColor, 100);
        data.tagColor = style === 'filled' ? toArgb(badgeColor, 80) : '#00000000';
      } else {
        data.tagColor = tc;
        data.borderColor = bc;
      }

      // Recolor badge SVG
      if (ic !== '#ffffff' && ic !== '#FFFFFF' && data.imageURL) {
        data.imageURL = recolorSvg(data.imageURL, ic);
      }

      filters.push(data);
    }

    // Build response — preserve group order from orderedGroups
    const groups = orderedGroups
      .filter(gid => filters.some(f => f.groupId === gid))
      .map(gid => GROUPS.find(g => g.id === gid))
      .filter(Boolean);
    const body = JSON.stringify({ groups, filters });

    return new Response(body, {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=3600",
        "CDN-Cache-Control": "public, max-age=31536000",
      },
    });
  },
};
