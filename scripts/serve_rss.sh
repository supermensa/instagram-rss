#!/bin/bash
# Start en simpel HTTP server til at serve RSS-filen fra public/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PUBLIC_DIR="$PROJECT_ROOT/public"
PORT=8000
RSS_FILE="instagram.xml"

cd "$PUBLIC_DIR"

echo "🌐 Starter lokal RSS server..."
echo "═══════════════════════════════════════════════════════"
echo "📡 URL: http://localhost:$PORT/$RSS_FILE"
echo "📁 Server mappe: $PUBLIC_DIR"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "📝 Tilføj dette i NetNewsWire:"
echo "   File → New Web Feed"
echo "   URL: http://localhost:$PORT/$RSS_FILE"
echo ""
echo "⚠️  Hold denne terminal åben mens du bruger RSS-feedet"
echo "🛑 Tryk Ctrl+C for at stoppe serveren"
echo ""

# Start Python's simple HTTP server
python3 -m http.server $PORT