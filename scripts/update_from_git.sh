#!/usr/bin/env bash
set -e
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

# Ensure git safe directory
git config --global --add safe.directory "$APP_DIR"

# Fetch latest commits on branch vm
git fetch origin vm --quiet

LOCAL_HASH=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE_HASH=$(git rev-parse origin/vm 2>/dev/null || echo "")

if [ "$LOCAL_HASH" != "$REMOTE_HASH" ] && [ -n "$REMOTE_HASH" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Updates detected on origin/vm ($LOCAL_HASH -> $REMOTE_HASH). Syncing..."
    
    CHANGED_FILES=$(git diff --name-only "$LOCAL_HASH" "$REMOTE_HASH")
    
    # Reset git working copy without touching untracked local env/data
    git reset --hard origin/vm
    
    # Check if backend requirements changed
    if echo "$CHANGED_FILES" | grep -qE '(backend/requirements\.txt|requirements\.txt)'; then
        echo "Updating python dependencies..."
        "$APP_DIR/backend/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt" --quiet
    fi

    # Check if frontend source or dependencies changed
    if echo "$CHANGED_FILES" | grep -qE 'package(-lock)?\.json'; then
        echo "Updating npm dependencies..."
        npm ci --production=false || npm install
    fi

    if echo "$CHANGED_FILES" | grep -qE '(src/|public/|index\.html|vite\.config\.ts|tailwind\.config\.js)'; then
        echo "Rebuilding frontend..."
        npm run build || true
        sudo systemctl restart nginx
    fi

    # Restart backend
    sudo systemctl restart crypto-bot-backend
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Updated successfully."
fi
