#!/bin/bash
#
# Full deploy: regenerate manifest + fragments, upload to KV, deploy worker, deploy Pages editor.
#
# Usage:
#   bash player-badges/scripts/deploy-all.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "═══════════════════════════════════════"
echo "  Nuvio Badges — Full Deploy"
echo "═══════════════════════════════════════"
echo ""

# Step 1: Regenerate manifest + fragments
echo "1/4 Regenerating manifest & fragments..."
python3 "$SCRIPT_DIR/generate-manifest.py"
echo ""

# Step 2: Upload fragments to KV + deploy worker
echo "2/4 Deploying worker + KV..."
bash "$SCRIPT_DIR/deploy-worker.sh"
echo ""

# Step 3: Deploy web editor to Pages
echo "3/4 Deploying web editor..."
bash "$SCRIPT_DIR/deploy-pages.sh"
echo ""

# Done
echo "═══════════════════════════════════════"
echo "  ✅ All done!"
echo ""
echo "  API:    https://nuvio-badges.skoruppa.workers.dev/v1/badge.json"
echo "  Editor: https://nuvio-badge-editor.pages.dev/web/index.html"
echo "═══════════════════════════════════════"
