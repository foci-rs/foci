#!/bin/sh
set -eu
hooks_dir=$(git rev-parse --git-path hooks)
target="$hooks_dir/pre-commit"
want="$(git rev-parse --show-toplevel)/tools/git-hooks/pre-commit"
if { [ -e "$target" ] || [ -L "$target" ]; } && [ "$(readlink "$target" 2>/dev/null)" != "$want" ]; then
  echo "refusing to overwrite existing hook at $target; install or chain it manually" >&2
  exit 1
fi
ln -sf "$want" "$target"
echo "installed vocabulary drift pre-commit hook at $target"
