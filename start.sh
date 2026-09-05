#!/usr/bin/env bash

# ==============================================================================
#  AetherTrade AI - Unified Development Runner
#  Starts both FastAPI Backend (port 8000) and Vite Frontend (port 5173) in 1-go
# ==============================================================================

set -e

# Terminal Colors
CYAN='\033[0;36m'
BOLD_CYAN='\033[1;36m'
GREEN='\033[0;32m'
BOLD_GREEN='\033[1;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
RED='\033[0;31m'
NC='\033[0m' # No Color
DIM='\033[2m'

# Absolute directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Print Banner
echo -e "${BOLD_CYAN}"
echo "  ╔════════════════════════════════════════════════════════════════╗"
echo "  ║        ⚡ AETHERTRADE AI — MULTI-AGENT CRYPTO TERMINAL ⚡       ║"
echo "  ║             Unified Backend + Frontend Launcher               ║"
echo "  ╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 2. Detect Local Wi-Fi / Network IP for Mobile access
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

# 3. Pre-flight Checks: Node & Python
echo -e "${DIM}Checking system environment...${NC}"

if ! command -v node >/dev/null 2>&1; then
  echo -e "${RED}Error: Node.js is not installed or not in PATH.${NC}"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${RED}Error: Python 3 is not installed or not in PATH.${NC}"
  exit 1
fi

# 4. Check Frontend Dependencies
if [ ! -d "node_modules" ]; then
  echo -e "${YELLOW}node_modules not found. Installing frontend dependencies...${NC}"
  npm install
fi

# 5. Check Backend Python Virtual Environment
VENV_DIR="backend/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
UVICORN_BIN="$VENV_DIR/bin/uvicorn"

if [ ! -d "$VENV_DIR" ] || [ ! -f "$UVICORN_BIN" ]; then
  echo -e "${YELLOW}Python virtual environment not found. Setting up $VENV_DIR...${NC}"
  python3 -m venv "$VENV_DIR"
  echo -e "${DIM}Installing backend requirements...${NC}"
  "$VENV_DIR/bin/pip" install --upgrade pip --quiet
  "$VENV_DIR/bin/pip" install -r backend/requirements.txt --quiet
  echo -e "${GREEN}✓ Backend virtual environment ready.${NC}"
fi

# 6. Check and free occupied ports if existing stale processes are running
free_port() {
  local port=$1
  local name=$2
  local pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo -e "${YELLOW}Notice: Port $port is in use ($name). Stopping stale process(es)...${NC}"
    for pid in $pids; do
      kill -9 "$pid" 2>/dev/null || true
    done
    sleep 0.8
  fi
}

free_port 8000 "FastAPI Backend"
free_port 5173 "Vite Dev Server"

# 7. Graceful Shutdown Handler (Ctrl+C / SIGINT / SIGTERM)
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo -e "${YELLOW}Stopping AetherTrade AI services...${NC}"
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo -e "${BOLD_GREEN}✓ All services stopped cleanly. Goodbye!${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

# 8. Start Backend in Background
echo -e "${BOLD_CYAN}► Starting FastAPI Backend on 0.0.0.0:8000...${NC}"
"$UVICORN_BIN" backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait briefly for backend to initialize
sleep 1.2

# 9. Start Frontend in Background
echo -e "${BOLD_GREEN}► Starting Vite Frontend on 0.0.0.0:5173...${NC}"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

# Wait briefly for Vite banner
sleep 1.0

# 10. Print Active Endpoints Table
echo ""
echo -e "${BOLD_CYAN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD_CYAN}║                    🚀 SERVERS RUNNING 🚀                         ║${NC}"
echo -e "${BOLD_CYAN}╠═══════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD_CYAN}║${NC}  ${BOLD_GREEN}Frontend (Local):${NC}    http://localhost:5173                      ${BOLD_CYAN}║${NC}"
if [ -n "$LOCAL_IP" ] && [ "$LOCAL_IP" != "127.0.0.1" ]; then
echo -e "${BOLD_CYAN}║${NC}  ${BOLD_GREEN}Frontend (Mobile):${NC}   http://${LOCAL_IP}:5173                 ${BOLD_CYAN}║${NC}"
fi
echo -e "${BOLD_CYAN}║${NC}  ${PURPLE}Backend API:${NC}         http://localhost:8000                      ${BOLD_CYAN}║${NC}"
echo -e "${BOLD_CYAN}║${NC}  ${PURPLE}Interactive Docs:${NC}    http://localhost:8000/docs                 ${BOLD_CYAN}║${NC}"
echo -e "${BOLD_CYAN}╠═══════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD_CYAN}║${NC}  ${DIM}Press [CTRL + C] anytime to gracefully stop both servers.${NC}       ${BOLD_CYAN}║${NC}"
echo -e "${BOLD_CYAN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Keep running and wait for children
wait
