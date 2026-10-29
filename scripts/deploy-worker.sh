#!/bin/bash
#
# Deploy the badge API worker to Cloudflare.
# Also uploads all fragments to KV (bulk put).
#
# Usage:
#   bash player-badges/scripts/deploy-worker.sh
#   bash player-badges/scripts/deploy-worker.sh --skip-kv   # skip KV upload, deploy worker only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
WORKER_DIR="$BASE_DIR/worker"
FRAGMENTS_DIR="$BASE_DIR/output/fragments"
KV_NAMESPACE_ID="8efe629c3733453cb2fd2aa8782a3888"

SKIP_KV=false
if [[ "${1:-}" == "--skip-kv" ]]; then
  SKIP_KV=true
fi

# ── Upload fragments to KV ─────────────────────────────────────────────────

if [[ "$SKIP_KV" == false ]]; then
  echo "📦 Building KV bulk upload..."

  python3 -c "
import json, os, glob

fragments_dir = '$FRAGMENTS_DIR'
entries = []

for f in sorted(glob.glob(os.path.join(fragments_dir, '*.json'))):
    name = os.path.basename(f)
    if name == 'groups.json':
        continue
    key = name.replace('.json', '')
    with open(f) as fh:
        entries.append({'key': key, 'value': fh.read()})

lang_dir = os.path.join(fragments_dir, 'lang')
for locale in sorted(os.listdir(lang_dir)):
    locale_path = os.path.join(lang_dir, locale)
    if not os.path.isdir(locale_path):
        continue
    for f in sorted(glob.glob(os.path.join(locale_path, '*.json'))):
        fid = os.path.basename(f).replace('.json', '')
        key = f'lang/{locale}/{fid}'
        with open(f) as fh:
            entries.append({'key': key, 'value': fh.read()})

print(f'  {len(entries)} entries')
with open('/tmp/kv-bulk.json', 'w') as f:
    json.dump(entries, f)
"

  echo "☁️  Uploading to KV..."
  wrangler kv bulk put /tmp/kv-bulk.json --namespace-id="$KV_NAMESPACE_ID" --remote
  rm /tmp/kv-bulk.json
  echo ""
fi

# ── Deploy worker ───────────────────────────────────────────────────────────

echo "🚀 Deploying worker..."
cd "$WORKER_DIR"
wrangler deploy

echo ""
echo "✅ Worker deployed: https://nuvio-badges.skoruppa.workers.dev"

# ── Purge edge cache ───────────────────────────────────────────────────────

echo ""
echo "🧹 Purging edge cache..."
sleep 5
PURGE_KEY="okgzTIYITKurqdWQcGiH58SGpdGm1HXp-39Kr4tcPWE"
curl -s -X POST "https://nuvio-badges.skoruppa.workers.dev/v1/purge?key=$PURGE_KEY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'  ✓ {d}')" 2>/dev/null || echo "  ⚠ purge failed (try manually)"
