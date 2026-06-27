# Opportunity Scout — 24/7 Server Deployment Guide
### Free server + auto-restart + web dashboard accessible from anywhere

---

## OPTION A — Oracle Cloud (100% FREE forever)
Best choice. Real Linux server, always-on, no credit card needed for free tier.

### Step 1 — Create Free Oracle Cloud Account (10 min)
1. Go to https://cloud.oracle.com/free
2. Sign up — needs a credit/debit card for verification only (won't be charged)
3. Choose **Home Region: Mumbai** (closest to India, fastest)
4. Wait for account activation (takes 5-30 minutes)

### Step 2 — Create a Free VM (5 min)
1. Go to: **Compute → Instances → Create Instance**
2. Change image → **Ubuntu 22.04** (Canonical)
3. Shape: Keep default **VM.Standard.E2.1.Micro** (Always Free)
4. Under "Add SSH keys" → click **Generate a key pair** → Download both files
   - Save `ssh-key-XXXX.key` and `ssh-key-XXXX-public.pem` to your PC
5. Click **Create**
6. Wait 2 minutes — copy the **Public IP address** shown (e.g. `150.230.xx.xx`)

---

## OPTION B — Hetzner VPS (₹350/month, most reliable)
If you want paid hosting that's cheap and fast.

1. Go to https://hetzner.com/cloud
2. Sign up → **Create Server**
3. Location: Helsinki or Falkenstein
4. Image: **Ubuntu 22.04**
5. Type: **CX11** (1 vCPU, 2GB RAM) — €3.29/month
6. SSH Keys: paste your public key
7. Click Create — copy the IP address

---

## STEP 3 — Connect to Your Server (Windows)

### Install PuTTY (free SSH client for Windows)
1. Download from https://putty.org
2. Install and open **PuTTYgen** → Load your `.key` file → Save private key as `.ppk`
3. Open **PuTTY**:
   - Host: `your-server-ip`
   - Port: `22`
   - Connection → SSH → Auth → Browse → select your `.ppk` file
   - Click **Open**
4. Login as: `ubuntu` (Oracle) or `root` (Hetzner)

### Or use Windows PowerShell (easier):
```powershell
# Convert key permissions first (run once)
icacls "C:\path\to\ssh-key.key" /inheritance:r /grant:r "%USERNAME%:R"

# Connect
ssh -i "C:\path\to\ssh-key.key" ubuntu@YOUR_SERVER_IP
```

---

## STEP 4 — Upload Your Project to the Server

### On your Windows PC, open PowerShell:
```powershell
# Upload the entire project folder
scp -i "C:\path\to\ssh-key.key" -r "D:\final_scout\opportunity-scout-final" ubuntu@YOUR_SERVER_IP:~/opportunity-scout

# Upload your .env file (has your API keys)
scp -i "C:\path\to\ssh-key.key" "D:\final_scout\opportunity-scout-final\.env" ubuntu@YOUR_SERVER_IP:~/opportunity-scout/.env
```

---

## STEP 5 — Set Up the Server (run these on the server)

### SSH into your server, then run:
```bash
# 1. Run the automated setup script
cd ~/opportunity-scout
chmod +x deploy.sh
./deploy.sh
```

This script does everything automatically:
- Installs Python 3.11
- Installs all project dependencies
- Sets up 2 background services (scheduler + dashboard)
- Starts both immediately

**That's it. Your project is now running 24/7.**

---

## STEP 6 — Open Your Dashboard From Anywhere

### Allow port 8000 through the firewall:

**Oracle Cloud (extra step needed):**
1. Go to your instance → **Primary VNIC** → Subnet → **Security List**
2. Click **Add Ingress Rules**
3. Source CIDR: `0.0.0.0/0` | Protocol: TCP | Port: `8000`
4. Click Add

**Hetzner:** Port is open by default.

### On the server, open the firewall:
```bash
sudo ufw allow 8000
sudo ufw allow 22
sudo ufw enable
```

### Access your dashboard:
Open in your browser: `http://YOUR_SERVER_IP:8000`

Your web dashboard is now live 24/7 from anywhere in the world.

---

## STEP 7 — Verify Everything is Running

```bash
# Check if scheduler is running
sudo systemctl status opportunity-scout

# Check if dashboard is running
sudo systemctl status opportunity-dashboard

# Watch live logs from the scheduler
sudo journalctl -u opportunity-scout -f

# Watch live logs from dashboard
sudo journalctl -u opportunity-dashboard -f
```

You should see output like:
```
✅ Tender scrape complete — 15 opportunities found
✅ AI analysis done — top score: 9.8/10
✅ Telegram message sent!
✅ Channel post published → @IndiaInfraScout
⏰ Next run in 6 hours...
```

---

## Daily Management Commands

```bash
# SSH into server
ssh -i "C:\path\to\ssh-key.key" ubuntu@YOUR_SERVER_IP

# View today's opportunities
cat ~/opportunity-scout/reports/report_$(date +%Y%m%d)*.txt

# Add a paying subscriber
cd ~/opportunity-scout
python3 add_subscriber.py add "Ravi Kumar" "ravi@example.com" basic

# View revenue dashboard
python3 add_subscriber.py dashboard

# Restart scheduler (if needed)
sudo systemctl restart opportunity-scout

# Restart dashboard (if needed)
sudo systemctl restart opportunity-dashboard

# Run manually right now (instead of waiting for next 6-hour cycle)
python3 main.py --full
```

---

## If Something Goes Wrong

| Problem | Fix |
|---------|-----|
| Telegram not sending | Check `sudo journalctl -u opportunity-scout -f` for error |
| Dashboard not loading | Run `sudo systemctl status opportunity-dashboard` |
| Out of disk space | Run `df -h` — clear old logs: `sudo journalctl --vacuum-time=7d` |
| Server rebooted | Services restart automatically (systemd handles this) |
| Need to update .env | Edit with `nano ~/opportunity-scout/.env` → restart: `sudo systemctl restart opportunity-scout` |
| Update project files | Run `scp` from your PC again → `sudo systemctl restart opportunity-scout` |

---

## What Runs 24/7 After Setup

| Service | What it does | Schedule |
|---------|-------------|---------|
| `opportunity-scout` | Scrapes tenders → AI analysis → Telegram → Channel post | Every 6 hours |
| `opportunity-dashboard` | Web dashboard at YOUR_IP:8000 | Always on |

**Both services restart automatically if they crash or if the server reboots.**

---

## Cost Summary

| Option | Cost | What you get |
|--------|------|-------------|
| Oracle Cloud Free | ₹0/month | 1 vCPU, 1GB RAM — runs fine |
| Hetzner CX11 | ~₹350/month | 2 vCPU, 2GB RAM — faster |
| Railway | ~₹420/month | Easy UI, managed |

Oracle Free Tier is enough for this project. Use Hetzner if you want more speed or reliability SLA.
