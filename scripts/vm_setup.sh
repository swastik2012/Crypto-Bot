#!/usr/bin/env bash
# ==============================================================================
#  AetherTrade AI - Oracle Cloud VM Automated Setup & Optimization Script
#  Configures 1CPU / 1GB RAM VM with Swap, Nginx, Systemd, and Auto-Deployment
# ==============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

CURRENT_USER=$(whoami)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}  🚀 Starting AetherTrade AI VM Deployment Setup     ${NC}"
echo -e "${CYAN}  User: ${CURRENT_USER} | Path: ${APP_DIR}            ${NC}"
echo -e "${CYAN}====================================================${NC}"

# 1. SWAP & LOW-RAM OPTIMIZATION (1 CPU / 1GB RAM)
echo -e "\n${YELLOW}Step 1: Setting up 2GB Swap and kernel memory tuning...${NC}"
if [ ! -f /swapfile ]; then
    echo "Creating 2GB swapfile..."
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    fi
    echo -e "${GREEN}✓ Swapfile created and activated.${NC}"
else
    echo "Swapfile already exists."
    sudo swapon /swapfile 2>/dev/null || true
fi

# Kernel memory tuning for 1GB RAM
sudo sysctl -w vm.swappiness=20 >/dev/null
sudo sysctl -w vm.vfs_cache_pressure=50 >/dev/null
if ! grep -q 'vm.swappiness=20' /etc/sysctl.conf 2>/dev/null; then
    echo 'vm.swappiness=20' | sudo tee -a /etc/sysctl.conf
    echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
fi
echo -e "${GREEN}✓ Memory tuning applied (swappiness=20, vfs_cache_pressure=50).${NC}"

# 2. INSTALL SYSTEM PACKAGES
echo -e "\n${YELLOW}Step 2: Installing system packages (Nginx, Python3, Git, etc.)...${NC}"
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip nginx git curl nodejs npm iptables-persistent netfilter-persistent
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf update -y
    sudo dnf install -y python3 python3-pip nginx git curl nodejs npm firewalld
elif command -v yum >/dev/null 2>&1; then
    sudo yum update -y
    sudo yum install -y python3 python3-pip nginx git curl nodejs npm
fi
echo -e "${GREEN}✓ System packages installed.${NC}"

# 3. FIREWALL / PORT 80 & 443 INGRESS CONFIGURATION
echo -e "\n${YELLOW}Step 3: Configuring OS Firewall for HTTP (Port 80) and HTTPS (Port 443)...${NC}"
if command -v iptables >/dev/null 2>&1; then
    # Oracle Cloud Linux distributions have a default reject rule on INPUT
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT
    if command -v netfilter-persistent >/dev/null 2>&1; then
        sudo netfilter-persistent save || true
    elif command -v service >/dev/null 2>&1; then
        sudo service iptables save 2>/dev/null || true
    fi
fi
if command -v firewall-cmd >/dev/null 2>&1; then
    sudo firewall-cmd --permanent --add-service=http 2>/dev/null || true
    sudo firewall-cmd --permanent --add-service=https 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true
fi
if command -v ufw >/dev/null 2>&1; then
    sudo ufw allow 80/tcp 2>/dev/null || true
    sudo ufw allow 443/tcp 2>/dev/null || true
fi
echo -e "${GREEN}✓ OS Firewall rules updated for port 80 & 443.${NC}"

# 4. PYTHON BACKEND VENV & DEPENDENCIES
echo -e "\n${YELLOW}Step 4: Setting up Python Virtual Environment...${NC}"
cd "$APP_DIR"
VENV_PATH="$APP_DIR/backend/venv"
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
fi
"$VENV_PATH/bin/pip" install --upgrade pip --quiet
"$VENV_PATH/bin/pip" install -r "$APP_DIR/backend/requirements.txt" --quiet
echo -e "${GREEN}✓ Python virtual environment ready with requirements.${NC}"

# 5. PERMISSIONS FOR NGINX WEB ROOT
# Ensure nginx user can read the application dist directory in /home/<user>
chmod 755 /home/"$CURRENT_USER"
chmod -R 755 "$APP_DIR/dist"

# 6. NGINX REVERSE PROXY CONFIGURATION
echo -e "\n${YELLOW}Step 5: Configuring Nginx reverse proxy...${NC}"
NGINX_CONF="/etc/nginx/sites-available/crypto-bot"
if [ ! -d "/etc/nginx/sites-available" ]; then
    sudo mkdir -p /etc/nginx/conf.d
    NGINX_CONF="/etc/nginx/conf.d/crypto-bot.conf"
fi

sudo tee "$NGINX_CONF" > /dev/null <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 50M;

    # Gzip Compression for Fast Loading
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Static React Frontend
    root ${APP_DIR}/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # FastAPI Backend APIs
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    # Interactive API Docs
    location ~ ^/(docs|openapi\.json|redoc|health) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # WebSocket Real-Time Crypto Streaming
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
EOF

# Enable Nginx site if debian/ubuntu style
if [ -d "/etc/nginx/sites-enabled" ]; then
    sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    sudo ln -sf /etc/nginx/sites-available/crypto-bot /etc/nginx/sites-enabled/
fi

sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
echo -e "${GREEN}✓ Nginx configured and running on port 80.${NC}"

# 7. SYSTEMD SERVICE FOR FASTAPI BACKEND
echo -e "\n${YELLOW}Step 6: Setting up crypto-bot-backend systemd service...${NC}"
sudo tee /etc/systemd/system/crypto-bot-backend.service > /dev/null <<EOF
[Unit]
Description=Crypto Bot 2 FastAPI Autonomous Backend
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/backend/venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable crypto-bot-backend
sudo systemctl restart crypto-bot-backend
echo -e "${GREEN}✓ Backend service started and enabled on boot.${NC}"

# 8. AUTOMATIC UPDATE SYNCHRONIZATION (GITHUB -> VM)
echo -e "\n${YELLOW}Step 7: Configuring automated GitHub push sync on branch 'vm'...${NC}"

# Create update script
tee "${APP_DIR}/scripts/update_from_git.sh" > /dev/null <<'EOF'
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
    
    # Reset git working copy without touching untracked local env/data
    git reset --hard origin/vm
    
    # Check if backend requirements changed
    if git diff --name-only "$LOCAL_HASH" "$REMOTE_HASH" | grep -q 'backend/requirements.txt'; then
        echo "Updating python dependencies..."
        "$APP_DIR/backend/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt" --quiet
    fi

    # Restart backend
    sudo systemctl restart crypto-bot-backend
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Updated successfully."
fi
EOF

chmod +x "${APP_DIR}/scripts/update_from_git.sh"

# Create systemd auto-update service & timer (polls git origin/vm every 60 seconds)
sudo tee /etc/systemd/system/crypto-bot-autoupdate.service > /dev/null <<EOF
[Unit]
Description=Crypto Bot Automated Git Sync
After=network.target

[Service]
Type=oneshot
User=${CURRENT_USER}
ExecStart=${APP_DIR}/scripts/update_from_git.sh
EOF

sudo tee /etc/systemd/system/crypto-bot-autoupdate.timer > /dev/null <<EOF
[Unit]
Description=Run Crypto Bot Git Sync every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
AccuracySec=5s

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now crypto-bot-autoupdate.timer
echo -e "${GREEN}✓ Auto-update systemd timer active (checks GitHub every 60 seconds).${NC}"

echo -e "\n${CYAN}====================================================${NC}"
echo -e "${GREEN}🎉 Setup Complete!                                   ${NC}"
echo -e "${CYAN}====================================================${NC}"
