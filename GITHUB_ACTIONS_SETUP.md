# GitHub Actions Setup — Run Scout for Free (No Server Needed)

This runs your project every 6 hours automatically using GitHub's free servers.
No credit card. No VPS. Just push your code.

**What works:** Telegram alerts + Channel posts + Lead generation + Reports
**What doesn't:** The web dashboard (GitHub Actions can't host a website)

---

## Step 1 — Push your project to GitHub (5 min)

1. Go to https://github.com → Sign up / log in
2. Click **New Repository** → Name: `opportunity-scout` → Private → Create
3. Open PowerShell on your PC:

```powershell
cd "D:\final_scout\opportunity-scout-final"

git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/opportunity-scout.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## Step 2 — Add your secrets to GitHub (3 min)

Your API keys must be stored as GitHub Secrets (not in the code).

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each one below:

| Secret Name | Where to get it |
|-------------|----------------|
| `GROQ_API_KEY` | https://console.groq.com → API Keys |
| `TELEGRAM_BOT_TOKEN` | From @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | From @userinfobot on Telegram |
| `TELEGRAM_CHANNEL_ID` | Your channel username e.g. `@IndiaInfraScout` |
| `RAZORPAY_PAYMENT_LINK` | Your Razorpay link e.g. `https://rzp.io/l/xxxx` |

---

## Step 3 — Enable Actions

1. Go to your repo → **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. You'll see **"Opportunity Scout — 24/7 Runner"** in the list

---

## Step 4 — Run it manually to test

1. Click the workflow → **Run workflow** → **Run workflow**
2. Wait ~5 minutes
3. Check your Telegram — you should get the daily digest!
4. Click the run to see logs and download the reports

---

## After that — it runs automatically

Every day at:
- **5:30 AM IST** (12:30 AM UTC)
- **11:30 AM IST** (6:00 AM UTC)
- **5:30 PM IST** (12:00 PM UTC)
- **11:30 PM IST** (6:00 PM UTC)

Your Telegram channel gets updated, alerts are sent, reports are saved.

---

## View your reports

After each run, GitHub saves the reports for 7 days:
1. Go to **Actions** tab → click any completed run
2. Scroll to **Artifacts** at the bottom
3. Download `scout-reports-N` → contains all JSON + text reports

---

## Free tier limits

| Resource | Free allowance | Your usage |
|----------|---------------|-----------|
| Minutes/month | 2,000 min | ~120 min (4 runs/day × 10 min × 30 days) |
| Storage | 500 MB | ~50 MB |
| Concurrent jobs | 20 | 1 |

You use only ~6% of the free limit. Plenty of headroom.

---

## Troubleshooting

**Run failed — check the logs:**
1. Actions tab → click the failed run → click the `scout` job → expand each step

**Telegram not sending:**
- Check the `TELEGRAM_BOT_TOKEN` secret is correct
- Make sure you sent `/start` to your bot

**No tenders found:**
- This is normal — govt portals sometimes block scrapers. System uses mock data.
- Try running manually at a different time.
