#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "Usage: scripts/create_clean_pr_branch.sh <new-branch-name> [commit-or-range]"
  echo
  echo "Examples:"
  echo "  scripts/create_clean_pr_branch.sh codex/tipsport-fix"
  echo "  scripts/create_clean_pr_branch.sh codex/tipsport-fix HEAD"
  echo "  scripts/create_clean_pr_branch.sh codex/tipsport-fix abc1234"
  echo "  scripts/create_clean_pr_branch.sh codex/tipsport-fix abc1234..def5678"
  exit 1
fi

NEW_BRANCH="$1"
COMMITS="${2:-}"

# Keep current branch name to print friendly return hint
CURRENT_BRANCH="$(git branch --show-current)"

# Ensure up-to-date reference for clean PR base
git fetch origin

# Start from clean base (origin/main)
git checkout -B "$NEW_BRANCH" origin/main

# Optionally cherry-pick only the wanted commit(s)
if [[ -n "$COMMITS" ]]; then
  if [[ "$COMMITS" == *".."* ]]; then
    git cherry-pick "${COMMITS%%..*}^..${COMMITS##*..}"
  else
    git cherry-pick "$COMMITS"
  fi
fi

echo
echo "✅ Branch '$NEW_BRANCH' is ready from origin/main."
echo "Next steps:"
echo "  git push -u origin $NEW_BRANCH"
echo "  (then open PR with base=main and compare=$NEW_BRANCH)"
echo
echo "Tip: return to previous branch: git checkout $CURRENT_BRANCH"
