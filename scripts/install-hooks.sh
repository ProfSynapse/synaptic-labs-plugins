#!/usr/bin/env bash
# Point this clone's hooks at scripts/hooks/, which is version controlled.
#
# core.hooksPath rather than copying into .git/hooks: a copy is a snapshot that
# silently rots when the tracked hook changes, and nothing tells you.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
git -C "$root" config core.hooksPath scripts/hooks
chmod +x "$root"/scripts/hooks/* 2>/dev/null || true

echo "hooks installed: $(git -C "$root" config core.hooksPath)"
echo "  pre-push  refuses a push while a marketplace pin is stale"
echo
echo "Undo with: git config --unset core.hooksPath"
