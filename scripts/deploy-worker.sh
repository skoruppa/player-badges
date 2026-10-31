#!/bin/bash
#
# Deploy the badge API worker to Cloudflare.
# Also uploads changed fragments to KV.
#
# Usage:
#   bash player-badges/scripts/deploy-worker.sh
#   bash player-badges/scripts/deploy-worker.sh --skip-kv   # skip KV upload, deploy worker only
#   bash player-badges/scripts/deploy-worker.sh --full      # upload every fragment, ignoring _deployed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
WORKER_DIR="$BASE_DIR/worker"
KV_NAMESPACE_ID="8efe629c3733453cb2fd2aa8782a3888"

SKIP_KV=false
KV_ARGS=()
case "${1:-}" in
  --skip-kv) SKIP_KV=true ;;
  --full) KV_ARGS+=(--full) ;;
esac

# ── Upload changed fragments to KV ─────────────────────────────────────────

if [[ "$SKIP_KV" == false ]]; then
  echo "☁️  Uploading changed fragments to KV..."
  python3 "$SCRIPT_DIR/upload-kv.py" --namespace-id="$KV_NAMESPACE_ID" ${KV_ARGS[@]+"${KV_ARGS[@]}"}
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
if [[ -z "${PURGE_KEY:-}" && -f "$BASE_DIR/.env" ]]; then
  source "$BASE_DIR/.env"
fi
if [[ -z "${PURGE_KEY:-}" ]]; then
  echo "  ⚠ no purge key: set PURGE_KEY in .env"
  exit 0
fi
curl -s -X POST "https://nuvio-badges.skoruppa.workers.dev/v1/purge?key=$PURGE_KEY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'  ✓ {d}')" 2>/dev/null || echo "  ⚠ purge failed (try manually)"
