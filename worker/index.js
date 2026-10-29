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
    const style = url.searchParams.get("s") || "filled";
    const tc = decodeURIComponent(url.searchParams.get("tc") || "#00000000");
    const bc = decodeURIComponent(url.searchParams.get("bc") || "#FFFFFFFF");

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
      data.tagStyle = style === "none" ? "filled" : style;
      data.tagColor = style === "none" ? "#00000000" : tc;
      data.borderColor = style === "bordered" ? bc : (style === "none" ? "#00000000" : bc);

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
