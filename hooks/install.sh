#!/usr/bin/env bash
# Install git hooks from the tracked hooks/ directory.
# Beads hooks (if present) are appended automatically by `bd init`.
set -e

repo_root="$(git rev-parse --show-toplevel)"
hooks_dir="$repo_root/hooks"

for hook in pre-commit pre-push; do
  if [ -f "$hooks_dir/$hook" ]; then
    cp "$hooks_dir/$hook" "$repo_root/.git/hooks/$hook"
    chmod +x "$repo_root/.git/hooks/$hook"
    echo "installed $hook"
  fi
done
