#!/usr/bin/env bash
set -euo pipefail

host="$(command -v ctx-firefox-host || true)"
if [[ -z "$host" ]]; then
  echo "ctx-firefox-register: ctx-firefox-host is not installed" >&2
  exit 1
fi

host="$(readlink -f "$host")"
destination="${HOME}/.mozilla/native-messaging-hosts/org.ctx_switcher.firefox.json"
mkdir -p "$(dirname "$destination")"
python3 - "$host" "$destination" <<'PY'
import json
import os
import sys

host, path = sys.argv[1:]
manifest = {
    "name": "org.ctx_switcher.firefox",
    "description": "Local Firefox bridge for Context Switcher",
    "path": host,
    "type": "stdio",
    "allowed_extensions": ["context-switcher@local"],
}
with open(path, "w", encoding="utf-8") as output:
    json.dump(manifest, output, indent=2)
    output.write("\n")
os.chmod(path, 0o600)
print("Registered Firefox native host at " + path)
PY
