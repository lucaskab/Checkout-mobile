#!/bin/zsh
# Brings the Mac's working copy up to origin/main without losing anything (tool runner "gitsync", Lucas 29/10).
# - copies the local eras_v2.blend (Blender work that only lives on the Mac) to a backup folder,
# - stashes every local change / untracked file (except Lucas's own assets/game-art/characters),
# - fast-forwards to origin/main,
# - puts the Mac's eras_v2.blend back and commits + pushes it when it differs from main.
# Output also goes to unity/CheckoutSimulator/Logs/gitsync.log.
set -uo pipefail
# The stash below removes this very file from the working copy (it may be untracked there): run from a copy in /tmp.
if [[ -z "${CHECKOUT_GITSYNC_COPY:-}" ]]; then
  cp "$0" /tmp/checkout-gitsync.sh && CHECKOUT_GITSYNC_COPY=1 exec zsh /tmp/checkout-gitsync.sh "$(git rev-parse --show-toplevel)"
  exit 1
fi
cd "$1" || exit 1
log=unity/CheckoutSimulator/Logs/gitsync.log
exec > >(tee "$log") 2>&1
ts=$(date +%Y%m%d-%H%M%S)
bk="$HOME/checkout-backup-$ts"; mkdir -p "$bk"
blend=unity/CheckoutSimulator/ArtSource/eras_v2/eras_v2.blend
[[ -f "$blend" ]] && cp "$blend" "$bk/eras_v2.blend" && echo "backup: $bk/eras_v2.blend"
git fetch origin main || exit 2
echo "HEAD before: $(git log --oneline -1)"
echo "local changes: $(git status --porcelain | wc -l)"
if [[ -n "$(git status --porcelain -- . ':(exclude)assets/game-art/characters')" ]]; then
  git stash push --include-untracked -m "backup copias do Claude $ts" -- . ':(exclude)assets/game-art/characters' || exit 3
  echo "stash: $(git stash list | head -1)"
fi
git merge --ff-only origin/main || exit 4
if [[ -f "$bk/eras_v2.blend" ]]; then
  cp "$bk/eras_v2.blend" "$blend"
  if ! git diff --quiet -- "$blend"; then
    git add "$blend" && git commit -m "eras_v2.blend with the bigger shops (from the Mac)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push origin HEAD:main || exit 5
  fi
fi
echo "HEAD after: $(git log --oneline -1)"
git status -sb | head -5
echo GITSYNC_OK
