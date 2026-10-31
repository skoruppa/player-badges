#!/usr/bin/env python3
"""
Upload badge fragments to Cloudflare KV, sending only entries that changed.

Writes on the free plan are limited per day, so a hash of every deployed value
is kept in KV under `_deployed`. It always reflects what production holds and
works from any machine. Regenerating output/ with no real changes writes nothing.

Usage:
    python3 scripts/upload-kv.py --namespace-id <id>
    python3 scripts/upload-kv.py --namespace-id <id> --dry-run   # report only
    python3 scripts/upload-kv.py --namespace-id <id> --full      # ignore _deployed
"""

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRAGMENTS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "output", "fragments")
STATE_KEY = "_deployed"


def local_entries():
    entries = {}
    for path in glob.glob(os.path.join(FRAGMENTS_DIR, "*.json")):
        name = os.path.basename(path)
        if name != "groups.json":
            with open(path) as f:
                entries[name[: -len(".json")]] = f.read()

    for path in glob.glob(os.path.join(FRAGMENTS_DIR, "lang", "*", "*.json")):
        locale = os.path.basename(os.path.dirname(path))
        fid = os.path.basename(path)[: -len(".json")]
        with open(path) as f:
            entries[f"lang/{locale}/{fid}"] = f.read()
    return entries


def content_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def deployed_hashes(namespace_id):
    """Hashes stored in KV; empty on first deploy. Other failures abort the deploy."""
    result = subprocess.run(
        ["wrangler", "kv", "key", "get", STATE_KEY, f"--namespace-id={namespace_id}", "--remote", "--text"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    if "404: Not Found" in result.stdout + result.stderr:
        return {}
    sys.exit(f"Could not read {STATE_KEY}:\n{result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="Upload changed badge fragments to KV.")
    parser.add_argument("--namespace-id", required=True)
    parser.add_argument("--dry-run", action="store_true", help="report changes, upload nothing")
    parser.add_argument("--full", action="store_true", help="upload everything")
    args = parser.parse_args()

    entries = local_entries()
    hashes = {key: content_hash(value) for key, value in entries.items()}
    deployed = {} if args.full else deployed_hashes(args.namespace_id)

    changed = sorted(key for key, value in hashes.items() if deployed.get(key) != value)
    print(f"  {len(changed)} of {len(entries)} entries changed")
    if not changed or args.dry_run:
        return

    # The state goes last in the same request: a separate write could be refused
    # once a large upload has used up the daily limit, losing track of it.
    payload = [{"key": key, "value": entries[key]} for key in changed]
    payload.append({"key": STATE_KEY, "value": json.dumps(hashes, sort_keys=True)})

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "kv-bulk.json")
        with open(path, "w") as f:
            json.dump(payload, f)
        subprocess.run(
            ["wrangler", "kv", "bulk", "put", path, f"--namespace-id={args.namespace_id}", "--remote"],
            check=True,
        )


if __name__ == "__main__":
    main()
