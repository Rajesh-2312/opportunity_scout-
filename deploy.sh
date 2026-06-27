#!/bin/bash
# =============================================================
# Opportunity Scout — Automated Server Setup
# Run this ONCE on a fresh Ubuntu 22.04 server
# Usage: chmod +x deploy.sh && ./deploy.sh
# =============================================================

set -e  # stop on any error

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${CYAN}[SETUP]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_USER="$(whoami)"

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Opportunity Scout — Server Setup${NC}"
echo -e "${CYAN}  Project: $PROJECT_DIR${NC}"
echo -e "${CYAN}  User:    $SERVICE_USER${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ── 1. System packages ────────────────────────────────────
log "Updating system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git curl ufw
ok "System packages installed"

# ── 2. Python virtual environment ────────────────────────
log "Creating Python virtual environment..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate
ok "Virtual environment created at $PROJECT_DIR/venv"

# ── 3. Install dependencies ───────────────────────────────
log "Installing Python dependencies (this takes 2-3 minutes)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "All dependencies installed"

# ── 4. Create data directories ────────────────────────────
log "Creating data directories..."
mkdir -p data reports leads
ok "Directories ready"

# ── 5. Check .env exists ──────────────────────────────────
if [ ! -f "$PROJECT_DIR/.env" ]; then
    warn ".env file not found — copying from .env.example"
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit your .env file before the service starts!${NC}"
    echo -e "${YELLOW}   Run: nano $PROJECT_DIR/.env${NC}"
    echo -e "${YELLOW}   Fill in: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_CHANNEL_ID, RAZORPAY_PAYMENT_LINK${NC}"
    echo ""
fi

# ── 6. Create systemd service — Scheduler ────────────────
log "Creating systemd service: opportunity-scout (scheduler)..."
sudo tee /etc/systemd/system/opportunity-scout.service > /dev/null <<EOF
[Unit]
Description=Opportunity Scout — Tender Intelligence Scheduler
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python main.py --schedule
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONUTF8=1

[Install]
WantedBy=multi-user.target
EOF
ok "Scheduler service created"

# ── 7. Create systemd service — Dashboard ─────────────────
log "Creating systemd service: opportunity-dashboard (web UI)..."
sudo tee /etc/systemd/system/opportunity-dashboard.service > /dev/null <<EOF
[Unit]
Description=Opportunity Scout — Web Dashboard
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python dashboard/run_dashboard.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
ok "Dashboard service created"

# ── 8. Enable and start services ──────────────────────────
log "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable opportunity-scout
sudo systemctl enable opportunity-dashboard
sudo systemctl start opportunity-scout
sudo systemctl start opportunity-dashboard
ok "Both services started"

# ── 9. Firewall ───────────────────────────────────────────
log "Configuring firewall..."
sudo ufw allow 22   > /dev/null 2>&1 || true
sudo ufw allow 8000 > /dev/null 2>&1 || true
sudo ufw --force enable > /dev/null 2>&1 || true
ok "Firewall: ports 22 (SSH) and 8000 (dashboard) open"

# ── 10. Status check ──────────────────────────────────────
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Setup Complete!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

SCOUT_STATUS=$(sudo systemctl is-active opportunity-scout)
DASH_STATUS=$(sudo systemctl is-active opportunity-dashboard)

if [ "$SCOUT_STATUS" = "active" ]; then
    echo -e "  ${GREEN}✅ Scheduler:  RUNNING${NC} (every 6 hours)"
else
    echo -e "  ${RED}❌ Scheduler:  $SCOUT_STATUS${NC}"
fi

if [ "$DASH_STATUS" = "active" ]; then
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    echo -e "  ${GREEN}✅ Dashboard:  RUNNING${NC} → http://$SERVER_IP:8000"
else
    echo -e "  ${RED}❌ Dashboard:  $DASH_STATUS${NC}"
fi

echo ""
echo -e "  ${CYAN}USEFUL COMMANDS:${NC}"
echo -e "  Watch live logs:    sudo journalctl -u opportunity-scout -f"
echo -e "  Restart scheduler:  sudo systemctl restart opportunity-scout"
echo -e "  Restart dashboard:  sudo systemctl restart opportunity-dashboard"
echo -e "  Add subscriber:     python3 add_subscriber.py add \"Name\" \"email\" basic"
echo -e "  Revenue dashboard:  python3 add_subscriber.py dashboard"
echo -e "  Run manually now:   python3 main.py --full"
echo ""

if [ ! -f "$PROJECT_DIR/.env" ] || grep -q "your_telegram_bot_token_here" "$PROJECT_DIR/.env" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  NEXT STEP: Fill in your .env file:${NC}"
    echo -e "${YELLOW}   nano $PROJECT_DIR/.env${NC}"
    echo -e "${YELLOW}   Then restart: sudo systemctl restart opportunity-scout${NC}"
    echo ""
fi
