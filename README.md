# Opportunity Scout — India Infrastructure Intelligence System
## All 5 Phases | Zero Cost | Built with AI

---

## Quick Start (15 minutes to live)

### Step 1 — Install
```bash
# Open this folder in VS Code terminal
pip install -r requirements.txt

# Copy config file
cp .env.example .env
```

### Step 2 — Get Free API Keys

**Groq API (Free LLM):**
1. Go to https://console.groq.com
2. Sign up → Create API Key → Copy it
3. Paste in .env as GROQ_API_KEY

**Telegram Bot (Free notifications):**
1. Open Telegram → search @BotFather → /newbot
2. Give it a name → copy the bot token
3. Search @userinfobot → /start → copy your chat ID
4. Paste both in .env

### Step 3 — Run
```bash
python main.py              # Run once
python main.py --schedule   # Run every 6 hours
```

---

## All Commands

| Command | What it does |
|---------|-------------|
| `python main.py` | Phase 1: Scrape tenders + AI analysis |
| `python main.py --market` | Phase 3: Scan BSE signals + predictions |
| `python main.py --stocks` | Phase 4: Stock signals + paper trades |
| `python main.py --monetize` | Phase 2: Publish channel + newsletter + leads |
| `python main.py --full` | ALL phases in sequence |
| `python main.py --dashboard` | Revenue dashboard in terminal |
| `python main.py --portfolio` | Paper trading portfolio |
| `python main.py --leads` | Generate contractor leads only |
| `python main.py --search "solar"` | Search tender memory |
| `python main.py --schedule` | Run every 6 hours automatically |
| `python dashboard/run_dashboard.py` | Phase 5: Web dashboard → localhost:8000 |

---

## Project Structure

```
opportunity-scout/
├── main.py                              ← Master orchestrator
├── requirements.txt                     ← All dependencies
├── .env.example                         ← Config template
│
├── scrapers/
│   └── tender_scraper.py               ← Phase 1: CPPP + GeM + News
│
├── memory/
│   └── vector_store.py                 ← ChromaDB vector memory
│
├── agents/
│   └── scout_agent.py                  ← LangGraph AI agent
│
├── notifier/
│   └── telegram_bot.py                 ← Telegram alerts
│
├── monetization/                       ← Phase 2
│   ├── channel_publisher.py            ← Auto-post to channel
│   ├── lead_generator.py               ← Find contractors + emails
│   ├── newsletter_formatter.py         ← Substack + LinkedIn + WhatsApp
│   └── payment_tracker.py             ← Revenue dashboard
│
├── market_intelligence/                ← Phase 3
│   ├── bse_scraper.py                  ← BSE/NSE signals
│   ├── intelligence_agent.py           ← Predict upcoming tenders
│   └── correlation_engine.py           ← Signal × tender matching
│
├── stock_intelligence/                 ← Phase 4
│   ├── signal_detector.py              ← Tender → stock signals
│   ├── paper_trader.py                 ← Virtual ₹1L portfolio
│   └── stock_dashboard.py             ← Terminal + reports
│
└── dashboard/                          ← Phase 5
    ├── api_server.py                   ← FastAPI REST backend
    ├── run_dashboard.py                ← One-command launcher
    └── static/index.html               ← Web dashboard UI
```

---

## Data Sources (All Free)

| Source | URL | What it gives |
|--------|-----|--------------|
| CPPP | eprocure.gov.in | Central govt tenders |
| GeM | gem.gov.in | Govt marketplace bids |
| BSE | bseindia.com | Corporate announcements |
| ET RSS | economictimes.com | Infrastructure news |
| BS RSS | business-standard.com | Policy & budget news |

---

## Monetization

Once running, three income streams:

**1. Telegram channel (₹299/month)**
- Free channel: 1 tender/day (teaser)
- Paid group: 5 tenders + full AI analysis
- 50 subscribers = ₹15,000/month

**2. B2B contractor intelligence (₹5,000-15,000/month)**
- Find contractors on IndiaMart
- Match tenders to their capabilities
- Sell as monthly intelligence service
- 5 clients = ₹25,000-75,000/month

**3. Stock intelligence newsletter**
- Weekly stock signals from tender data
- Substack paid tier
- LinkedIn audience → Razorpay payments

---

## Tech Stack (All Free)

| Component | Technology | Cost |
|-----------|-----------|------|
| AI Brain | Groq + Llama 3.1 70B | FREE |
| Agent Framework | LangGraph | FREE |
| Vector Memory | ChromaDB | FREE |
| Web Scraping | BeautifulSoup + Requests | FREE |
| Notifications | Telegram Bot API | FREE |
| Web Dashboard | FastAPI + HTML | FREE |
| Hosting | Your PC / Google Colab | FREE |

**Total monthly cost: ₹0**

---

## Troubleshooting

**Portal blocked / no tenders?**
The system auto-uses mock data when govt portals block access.
This is normal — works fine for testing. Try at off-peak hours (6am-9am).

**Groq rate limit?**
Free tier: 30 requests/minute. System handles this automatically.

**Telegram not sending?**
Make sure you sent /start to your bot first.
Check TELEGRAM_CHAT_ID is your personal ID, not the bot's.

**Dashboard won't open?**
Run: `pip install fastapi uvicorn`
Then: `python dashboard/run_dashboard.py`
Open: http://localhost:8000

---

*Built with LangGraph + Groq + ChromaDB + FastAPI*
*Zero capital. Zero cost. Pure intelligence.*
# opportunity_scout-
