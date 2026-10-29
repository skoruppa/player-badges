#!/bin/bash
# Upload all badge fragments to Cloudflare KV
# Requires: wrangler CLI (npm install -g wrangler)
#
# Usage:
#   cd player-badges
#   bash scripts/upload-to-kv.sh
#
# First run: wrangler login

NAMESPACE="BADGE_FRAGMENTS"
FRAGMENTS_DIR="output/fragments"

echo "Uploading static fragments..."
for f in "$FRAGMENTS_DIR"/p-*.json; do
  key=$(basename "$f" .json)
  echo "  $key"
  wrangler kv key put --namespace-id="$KV_NAMESPACE_ID" "$key" --path="$f"
done

echo "Uploading groups..."
wrangler kv key put --namespace-id="$KV_NAMESPACE_ID" "_groups" --path="$FRAGMENTS_DIR/groups.json"

echo "Uploading language fragments..."
for locale_dir in "$FRAGMENTS_DIR"/lang/*/; do
  locale=$(basename "$locale_dir")
  for f in "$locale_dir"/*.json; do
    key="lang/$locale/$(basename "$f" .json)"
    echo "  $key"
    wrangler kv key put --namespace-id="$KV_NAMESPACE_ID" "$key" --path="$f"
  done
done

echo "Done!"
