#!/bin/bash
# Daily Instagram RSS Update Script
# Kører maksimalt én gang per dag via sleepwatcher systemet

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAST_RUN_FILE="$PROJECT_ROOT/.last_run_date"
LOCK_FILE="$PROJECT_ROOT/.update_lock"
TODAY=$(date '+%Y-%m-%d')

cd "$PROJECT_ROOT"

# Fjern lock-fil ved exit (både success og fejl)
cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📱 Instagram RSS Daily Update"
echo "═══════════════════════════════════════════════════════"

# Tjek om scriptet allerede kører
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "⏸️  Script kører allerede (PID: $LOCK_PID)"
        echo "   Venter på at den anden process færdiggør..."
        exit 0
    else
        echo "🧹 Fjerner gammel lock-fil"
        rm -f "$LOCK_FILE"
    fi
fi

# Opret lock-fil med aktuel PID
echo $$ > "$LOCK_FILE"

# Tjek om scriptet allerede har kørt i dag
if [ -f "$LAST_RUN_FILE" ]; then
    LAST_RUN=$(cat "$LAST_RUN_FILE")
    if [ "$LAST_RUN" = "$TODAY" ]; then
        echo "✅ Allerede kørt i dag ($TODAY)"
        echo "   Sidste kørsel: $LAST_RUN"
        exit 0
    else
        echo "🔄 Sidste kørsel var: $LAST_RUN"
        echo "   Kører opdatering for: $TODAY"
    fi
else
    echo "🆕 Første kørsel - ingen tidligere kørsler fundet"
fi

# Aktivér virtual environment
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "✅ Virtual environment aktiveret"
else
    echo "⚠️  Virtual environment ikke fundet: $PROJECT_ROOT/.venv"
    exit 1
fi

# Kør RSS generator
echo ""
echo "🚀 Kører Instagram RSS generator..."
echo "───────────────────────────────────────────────────────"

if "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/instagram_rss.py"; then
    echo "───────────────────────────────────────────────────────"
    echo "✅ RSS generator færdig"
    
    # Push til GitHub
    echo ""
    echo "🔄 Opdaterer GitHub Pages..."
    if bash "$SCRIPT_DIR/update_github.sh"; then
        echo "✅ GitHub Pages opdateret"
        
        # Gem dagens dato som sidste kørsel
        echo "$TODAY" > "$LAST_RUN_FILE"
        echo ""
        echo "✅ SUCCES: Opdatering gennemført for $TODAY"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Instagram RSS opdatering færdig"
    else
        echo "⚠️  GitHub opdatering fejlede"
        exit 1
    fi
else
    echo "❌ RSS generator fejlede"
    exit 1
fi
