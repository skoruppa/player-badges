#!/usr/bin/env node
/**
 * Local dev server for the badge editor + API.
 *
 * Serves:
 *   /v1/badge.json?l=en&g=res,hdr,...  → assembles badge JSON from output/fragments/
 *   /web/*                              → static files from web/
 *   /output/*                           → static files from output/ (manifest, fragments)
 *
 * Usage:
 *   node player-badges/scripts/dev-server.js [port]
 *   node player-badges/scripts/dev-server.js 3000
 *
 * Default port: 8080
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const BASE_DIR = path.resolve(__dirname, '..');
const FRAGMENTS_DIR = path.join(BASE_DIR, 'output', 'fragments');
const PORT = parseInt(process.argv[2] || '8080', 10);

// ── Group/filter definitions (mirrors worker/index.js) ─────────────────────

const GROUPS = [
  { id: "res", name: "Resolution", isExpanded: true },
  { id: "hdr", name: "HDR / Vision", isExpanded: true },
  { id: "aud", name: "Audio Format", isExpanded: true },
  { id: "ch", name: "Channels", isExpanded: true },
  { id: "src", name: "Source", isExpanded: true },
  { id: "spc", name: "Special", isExpanded: true },
  { id: "lang", name: "Language", isExpanded: true },
];

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

const SOURCE_LANG_FILTERS = [
  "s-eng", "s-pol", "s-spa", "s-fre", "s-ger", "s-ita", "s-por", "s-por-br", "s-rus",
  "s-jpn", "s-kor", "s-zho", "s-hin", "s-ara", "s-tur", "s-dut", "s-swe",
  "s-nor", "s-dan", "s-fin", "s-ces", "s-hun", "s-ron", "s-ukr", "s-ell",
  "s-heb", "s-tha", "s-vie", "s-ind", "s-msa", "s-hrv", "s-srp", "s-bul",
  "s-slk", "s-slv",
];

const ALL_LANG_IDS = new Set([...GROUP_FILTERS.lang, ...SOURCE_LANG_FILTERS]);

// ── Badge API handler ──────────────────────────────────────────────────────

function handleBadgeApi(query) {
  const locale = query.l || 'en';
  const context = query.c || 'player';
  const groupsParam = query.g || 'res,hdr,aud,ch,src,spc,lang';
  const excludeParam = query.x || '';
  const groupOrderParam = query.go || '';
  const style = query.s || 'filled';
  const tc = decodeURIComponent(query.tc || '#00000000');
  const bc = decodeURIComponent(query.bc || '#FFFFFFFF');

  // Group order
  let orderedGroups;
  if (groupOrderParam) {
    orderedGroups = groupOrderParam.split(',').map(s => s.trim());
  } else {
    orderedGroups = groupsParam.split(',').map(s => s.trim());
  }

  const requestedGroups = new Set(groupsParam.split(',').map(s => s.trim()));
  const excludeSet = excludeParam ? new Set(excludeParam.split(',').map(s => s.trim())) : new Set();

  // Per-group badge order overrides: o.res=p-4k,p-1080p
  const badgeOrderOverrides = {};
  for (const [key, value] of Object.entries(query)) {
    if (key.startsWith('o.')) {
      const gid = key.substring(2);
      badgeOrderOverrides[gid] = value.split(',').map(s => s.trim());
    }
  }

  // Build effective group filters (swap lang based on context)
  const effectiveFilters = { ...GROUP_FILTERS };
  if (context === 'source') {
    effectiveFilters.lang = SOURCE_LANG_FILTERS;
  }

  // Build filter IDs
  let filterIds = [];
  for (const gid of orderedGroups) {
    if (!requestedGroups.has(gid)) continue;
    const defaultIds = effectiveFilters[gid];
    if (!defaultIds) continue;
    const ids = badgeOrderOverrides[gid] || defaultIds;
    filterIds.push(...ids);
  }
  filterIds = filterIds.filter(id => !excludeSet.has(id));

  // Load fragments from files
  const filters = [];
  for (const id of filterIds) {
    let fragPath;
    if (ALL_LANG_IDS.has(id)) {
      fragPath = path.join(FRAGMENTS_DIR, 'lang', locale, `${id}.json`);
    } else {
      fragPath = path.join(FRAGMENTS_DIR, `${id}.json`);
    }

    try {
      const data = JSON.parse(fs.readFileSync(fragPath, 'utf-8'));
      data.tagStyle = style === 'none' ? 'filled' : style;
      data.tagColor = style === 'none' ? '#00000000' : tc;
      data.borderColor = style === 'bordered' ? bc : (style === 'none' ? '#00000000' : bc);
      filters.push(data);
    } catch {
      // Fragment not found for this locale
    }
  }

  const groups = orderedGroups
    .filter(gid => filters.some(f => f.groupId === gid))
    .map(gid => GROUPS.find(g => g.id === gid))
    .filter(Boolean);

  return JSON.stringify({ groups, filters });
}

// ── Static file serving ────────────────────────────────────────────────────

const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function serveStatic(res, filePath) {
  const absPath = path.join(BASE_DIR, filePath);
  if (!fs.existsSync(absPath) || !fs.statSync(absPath).isFile()) {
    res.writeHead(404);
    res.end('Not found');
    return;
  }
  const ext = path.extname(absPath);
  const mime = MIME_TYPES[ext] || 'application/octet-stream';
  res.writeHead(200, {
    'Content-Type': mime,
    'Access-Control-Allow-Origin': '*',
  });
  fs.createReadStream(absPath).pipe(res);
}

// ── Server ─────────────────────────────────────────────────────────────────

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url, true);
  const pathname = parsed.pathname;

  // API endpoint
  if (pathname === '/v1/badge.json') {
    const body = handleBadgeApi(parsed.query);
    res.writeHead(200, {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    });
    res.end(body);
    return;
  }

  // Static: /output/*
  if (pathname.startsWith('/output/')) {
    serveStatic(res, pathname.substring(1));
    return;
  }

  // Static: web files at root (index.html, app.js, style.css, i18n.js)
  const webFiles = ['index.html', 'app.js', 'style.css', 'i18n.js', 'favicon.svg'];
  const basename = pathname.substring(1); // strip leading /
  if (webFiles.includes(basename)) {
    serveStatic(res, 'web/' + basename);
    return;
  }

  // Root → serve index.html
  if (pathname === '/' || pathname === '') {
    serveStatic(res, 'web/index.html');
    return;
  }

  res.writeHead(404);
  res.end('Not found');
});

server.listen(PORT, () => {
  console.log(`Badge dev server running at http://localhost:${PORT}`);
  console.log(`  Editor:  http://localhost:${PORT}/`);
  console.log(`  API:     http://localhost:${PORT}/v1/badge.json?l=en&g=res,hdr`);
  console.log(`  Files:   /output/*`);
  console.log();
  console.log('Press Ctrl+C to stop.');
});
