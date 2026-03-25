#!/bin/bash
# Setup: Automatisk start RSS server ved boot

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.instagram-rss.server.plist"
PUBLIC_DIR="$PROJECT_ROOT/public"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.instagram-rss.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>http.server</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PUBLIC_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/server.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/server.log</string>
</dict>
</plist>
EOF

echo "✅ Launchd service oprettet!"
echo ""
echo "Start serveren:"
echo "  launchctl load $PLIST_FILE"
echo ""
echo "Stop serveren:"
echo "  launchctl unload $PLIST_FILE"
echo ""
echo "Feed URL: http://localhost:8000/instagram.xml"