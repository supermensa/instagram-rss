#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🔄 Opdaterer GitHub Pages..."
git add public/

if git diff --cached --quiet; then
    echo "ℹ️  Ingen ændringer i public/ at committe"
    exit 0
fi

git commit -m "Update public feeds - $(date '+%Y-%m-%d %H:%M')"
git push
echo "✅ RSS feed opdateret på GitHub Pages!"
echo "⏳ Det kan tage 1-2 minutter før ændringerne er live"