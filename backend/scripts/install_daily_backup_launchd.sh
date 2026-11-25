#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/swastik/Desktop/AI Agent/Crypto Bot 2"
PYTHON_BIN="$ROOT_DIR/backend/venv/bin/python"
BACKUP_SCRIPT="$ROOT_DIR/backend/scripts/backup_vm_db.py"
LOG_DIR="$ROOT_DIR/backend/backups/logs"
PLIST_PATH="$HOME/Library/LaunchAgents/com.cryptobot.daily_backup.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.cryptobot.daily_backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$BACKUP_SCRIPT</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/daily_backup.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/daily_backup.err.log</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/com.cryptobot.daily_backup" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl print "gui/$(id -u)/com.cryptobot.daily_backup" | head -n 20
echo "✅ Installed macOS LaunchAgent at $PLIST_PATH (Daily at 09:00 local time)"
