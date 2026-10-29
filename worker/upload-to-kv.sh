#!/bin/bash
#
# Upload all badge fragments to Cloudflare KV.
#
# Prerequisites:
#   - wrangler CLI installed and authenticated
#   - KV namespace created: wrangler kv namespace create BADGE_FRAGMENTS
#   - Update wrangler.toml with the namespace ID
#
# Usage:
#   cd player-badges/worker
#   bash upload-to-kv.sh
#
# KV key scheme:
#   Static filters:  p-4k, p-dv, p-atmos, ...
#   Player lang:     lang/en/p-eng, lang/pl/p-pol, ...
#   Source lang:     lang/en/s-eng, lang/pl/s-pol, ...

set -euo pipefail

FRAGMENTS_DIR="../output/fragments"
BINDING="BADGE_FRAGMENTS"

echo "Uploading static fragments..."
for f in "$FRAGMENTS_DIR"/p-*.json "$FRAGMENTS_DIR"/s-*.json; do
  [ -f "$f" ] || continue
  key=$(basename "$f" .json)
  echo "  $key"
  wrangler kv key put --binding="$BINDING" "$key" --path="$f"
done

echo ""
echo "Uploading language fragments..."
for locale_dir in "$FRAGMENTS_DIR"/lang/*/; do
  locale=$(basename "$locale_dir")
  for f in "$locale_dir"/*.json; do
    [ -f "$f" ] || continue
    id=$(basename "$f" .json)
    key="lang/$locale/$id"
    echo "  $key"
    wrangler kv key put --binding="$BINDING" "$key" --path="$f"
  done
done

echo ""
echo "Done. Upload complete."
