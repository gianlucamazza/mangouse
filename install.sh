#!/usr/bin/env bash
# Local install: uv tool entry point + optional config + agent skill links.
# Idempotent. Does not register MCP and does not write ~/.grok/config.toml.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${HOME}/.local/bin"
CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mangouse"

need() {
	command -v "$1" >/dev/null 2>&1 || {
		echo "mangouse: missing $1" >&2
		exit 1
	}
}

need uv
mkdir -p "$BIN" "$CFG_DIR"

# uv caches wheels by version; --reinstall deploys this checkout even if
# __version__ is unchanged.
# [mcp] so mangouse-mcp can handshake; Grok registration is still a separate step.
uv tool install --force --reinstall "${REPO}[mcp]"

if [[ ! -f "$CFG_DIR/config.toml" ]]; then
	umask 077
	cp "$REPO/examples/config.toml" "$CFG_DIR/config.toml"
	chmod 600 "$CFG_DIR/config.toml"
	echo "Created $CFG_DIR/config.toml"
fi

link_skill() {
	local dest="$1"
	mkdir -p "$dest"
	ln -sfn "$REPO/skills/mangouse/SKILL.md" "$dest/SKILL.md"
	echo "Linked skill → $dest/SKILL.md"
}

# Only attach to skill roots that already exist (do not invent host trees).
for root in "${HOME}/.claude/skills" "${HOME}/.grok/skills" "${HOME}/.agents/skills"; do
	if [[ -d "$root" ]]; then
		link_skill "${root}/mangouse"
	fi
done

command -v grim >/dev/null || echo "warn: grim missing — shot will fail"
command -v mmsg >/dev/null || echo "warn: mmsg missing — mango backend will fail"
command -v magick >/dev/null || echo "warn: magick missing — --fit is a no-op"

if ! command -v mangouse >/dev/null; then
	echo "warn: mangouse not on PATH (expected $BIN). Add it: export PATH=\"\$HOME/.local/bin:\$PATH\""
	exit 1
fi

echo "mangouse $(mangouse --version 2>/dev/null || true)"
mangouse --json doctor | head -c 400
echo
echo "Installed. Try: mangouse --json desktop"
