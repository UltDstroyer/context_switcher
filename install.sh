#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "$BIN_DIR"

install -m 0755 "$ROOT/src/ctx" "$BIN_DIR/ctx"
install -m 0755 "$ROOT/src/ctxd" "$BIN_DIR/ctxd"
install -m 0755 "$ROOT/src/ctxdctl" "$BIN_DIR/ctxdctl"

printf 'Installed ctx, ctxd, and ctxdctl to %s\n' "$BIN_DIR"
printf 'Make sure %s is in PATH.\n' "$BIN_DIR"
