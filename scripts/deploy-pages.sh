#!/bin/bash
#
# Deploy the badge web editor to Cloudflare Pages.
# Bundles web/ + output/ (manifest + fragments) into a single deploy.
#
# Usage:
#   bash player-badges/scripts/deploy-pages.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
WORKER_URL="https://nuvio-badges.skoruppa.workers.dev"
PAGES_PROJECT="nuvio-badge-editor"
DEPLOY_DIR="/tmp/pages-deploy"

# ── Prepare deploy directory ────────────────────────────────────────────────

echo "📦 Preparing deploy..."
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR/output"

# Copy web files to root
cp "$BASE_DIR/web/index.html" \
   "$BASE_DIR/web/app.js" \
   "$BASE_DIR/web/i18n.js" \
   "$BASE_DIR/web/style.css" \
   "$BASE_DIR/web/favicon.svg" \
   "$DEPLOY_DIR/"

# Copy output (manifest + bundles for editor, fragments for individual access)
cp "$BASE_DIR/output/manifest.json" "$DEPLOY_DIR/output/"
cp -r "$BASE_DIR/output/bundles" "$DEPLOY_DIR/output/bundles"
cp -r "$BASE_DIR/output/fragments" "$DEPLOY_DIR/output/fragments"

# Patch app.js: point generated URLs to worker (not localhost)
sed -i "s|location.origin|'${WORKER_URL}'|" "$DEPLOY_DIR/app.js"

echo "  $(find "$DEPLOY_DIR" -type f | wc -l) files"

# ── Deploy to Cloudflare Pages ──────────────────────────────────────────────

echo "🚀 Deploying to Pages..."
wrangler pages deploy "$DEPLOY_DIR" --project-name "$PAGES_PROJECT"

# ── Cleanup ─────────────────────────────────────────────────────────────────

rm -rf "$DEPLOY_DIR"

echo ""
echo "✅ Editor deployed: https://${PAGES_PROJECT}.pages.dev"
