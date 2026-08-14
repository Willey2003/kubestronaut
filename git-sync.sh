#!/usr/bin/env bash
# One-command sync: commit everything + push to GitHub.
# Usage: ./git-sync.sh ["commit message"]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

MSG="${1:-Auto-sync: Golden Astronaut 2026}"

if [ -z "$(git status --porcelain)" ]; then
  echo "Nothing to commit - working tree clean."
  exit 0
fi

git add -A
git commit -m "$MSG"
git push origin main
echo "Pushed to GitHub."
