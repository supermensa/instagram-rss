#!/bin/bash
# GitHub Pages setup til Instagram RSS

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UPDATE_SCRIPT="$SCRIPT_DIR/update_github.sh"

cd "$PROJECT_ROOT"

echo "🚀 GitHub Pages Setup for Instagram RSS"
echo "════════════════════════════════════════════════════════"
echo ""

# Tjek om git er installeret
if ! command -v git &> /dev/null; then
    echo "❌ Git er ikke installeret"
    echo "Install med: brew install git"
    exit 1
fi

# Tjek om GitHub CLI er installeret
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI ikke fundet - vi laver manuelt setup"
    MANUAL=true
else
    MANUAL=false
fi

REPO_NAME="instagram-rss"

echo "📋 Setup trin:"
echo "1. Opret GitHub repo (hvis det ikke findes)"
echo "2. Initialiser git i denne mappe"
echo "3. Push public/ til GitHub"
echo "4. Aktiver GitHub Pages"
echo ""

# Initialiser git hvis ikke allerede gjort
if [ ! -d ".git" ]; then
    echo "📦 Initialiserer git..."
    git init
    echo "*.pyc" >> .gitignore
    echo "__pycache__/" >> .gitignore
    echo ".DS_Store" >> .gitignore
    git add .
    git commit -m "Initial commit: Instagram RSS generator"
    echo "✅ Git initialiseret"
else
    echo "✅ Git allerede initialiseret"
fi

if [ "$MANUAL" = true ]; then
    echo ""
    echo "════════════════════════════════════════════════════════"
    echo "MANUELLE TRIN:"
    echo "════════════════════════════════════════════════════════"
    echo ""
    echo "1️⃣  Gå til: https://github.com/new"
    echo "   Repo navn: $REPO_NAME"
    echo "   Public ✓"
    echo "   Klik 'Create repository'"
    echo ""
    read -p "Tryk Enter når repo er oprettet..."
    echo ""
    echo "2️⃣  Hvad er dit GitHub brugernavn?"
    read -p "Brugernavn: " USERNAME
    echo ""

    # Tilføj remote
    git remote remove origin 2>/dev/null || true
    git remote add origin "https://github.com/$USERNAME/$REPO_NAME.git"

    echo "3️⃣  Pusher til GitHub..."
    git branch -M main
    git push -u origin main

    echo ""
    echo "4️⃣  Aktiver GitHub Pages:"
    echo "   → Gå til: https://github.com/$USERNAME/$REPO_NAME/settings/pages"
    echo "   → Source: Deploy from branch"
    echo "   → Branch: main / (root)"
    echo "   → Klik 'Save'"
    echo ""
    read -p "Tryk Enter når GitHub Pages er aktiveret..."

    PAGES_URL="https://$USERNAME.github.io/$REPO_NAME/public/instagram.xml"
else
    echo "🤖 Opretter repo med GitHub CLI..."
    gh repo create "$REPO_NAME" --public --source=. --remote=origin --push

    echo "🌐 Aktiverer GitHub Pages..."
    gh api repos/:owner/$REPO_NAME/pages -X POST -f source[branch]=main -f source[path]=/

    USERNAME=$(gh api user --jq '.login')
    PAGES_URL="https://$USERNAME.github.io/$REPO_NAME/public/instagram.xml"
fi

chmod +x "$UPDATE_SCRIPT"

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ SETUP FÆRDIG!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📡 Din RSS Feed URL:"
echo "   $PAGES_URL"
echo ""
echo "📱 Tilføj i NetNewsWire:"
echo "   File → New Web Feed"
echo "   URL: $PAGES_URL"
echo ""
echo "🔄 Når du opdaterer feedet:"
echo "   ./scripts/update_github.sh"
echo ""
echo "💡 TIP: Når du kører ./scripts/run_batches.sh næste gang,"
echo "   kør derefter ./scripts/update_github.sh for at opdatere online feed"