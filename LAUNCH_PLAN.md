# Opportunity Scout — Business Launch Plan
### Goal: ₹14,950/month (50 subscribers × ₹299) in 30 days

---

## TODAY — Setup (2 hours)

### 1. Create Your Telegram Channel (10 min)
1. Open Telegram → tap the pencil icon → **New Channel**
2. Name: **"India Infra Intelligence"**
3. Description: *"Daily AI-powered government tender alerts — infrastructure, solar, airports, roads. Free preview every day. Premium: ₹299/month."*
4. Set to **Public** → username: `@IndiaInfraScout` (or similar)
5. Copy the channel link: `https://t.me/IndiaInfraScout`

### 2. Set Up Razorpay Payment Link (15 min)
1. Go to https://razorpay.com → Sign up (free, just needs PAN + bank account)
2. Dashboard → **Payment Links** → **Create Payment Link**
3. Amount: **₹299** | Description: "India Infra Intelligence — Monthly Premium"
4. Enable: *"Allow customers to change amount"* (so you can offer ₹5K/month B2B later)
5. Copy your payment link (looks like: `https://rzp.io/l/xxxx`)

### 3. Configure Your .env (5 min)
Open `.env` and fill in:
```
TELEGRAM_BOT_TOKEN=         # from @BotFather
TELEGRAM_CHAT_ID=           # your personal ID from @userinfobot
TELEGRAM_CHANNEL_ID=        # @IndiaInfraScout (your channel username)
RAZORPAY_PAYMENT_LINK=      # https://rzp.io/l/your-link
```

### 4. Post First Channel Update (5 min)
Run this to publish today's top opportunities to your channel:
```bash
python main.py --monetize
```
This automatically posts a teaser to your public channel with a link to subscribe.

---

## WEEK 1 — Get First 10 Subscribers

### Day 1-2: Warm Network
Use the messages in `OUTREACH_KIT.md` to reach out to:
- WhatsApp contacts who work in construction, civil, solar, logistics
- LinkedIn connections in infrastructure / EPC / contracting
- Any contractor or business owner you know personally

**Target: 3-5 free followers on your channel**

### Day 3-5: Join Relevant Telegram Groups
Search Telegram for groups like:
- "India tenders"
- "Government contracts India"  
- "Civil contractors"
- "Infrastructure business"
- "GeM portal"

Join 10-15 groups. Post the **Telegram Group Pitch** from `OUTREACH_KIT.md` in each one.

**Target: 10-20 channel followers**

### Day 5-7: Convert Free → Paid
DM everyone who joined your free channel. Use the **DM Conversion Script** from `OUTREACH_KIT.md`.

Offer the first 10 subscribers a **launch discount**: ₹199/month for 3 months (lock them in, get reviews).

**Target: 5 paying subscribers = ₹995-1,495/month**

---

## WEEK 2 — LinkedIn Growth

### Post 3x on LinkedIn this week:
Use the templates in `OUTREACH_KIT.md`. These posts work best:
1. **"I built a free tool that monitors all Indian govt tenders"** — share the tool story
2. **"This ₹5,000 Crore airport tender just dropped in AP"** — use real tender data
3. **"How I'm helping contractors stop missing government bids"** — value post

### LinkedIn DMs:
Search LinkedIn for:
- "Civil contractor Hyderabad" / "EPC company Andhra Pradesh"
- "Infrastructure project manager"
- "Solar EPC company India"

Send 20 DMs/day using the LinkedIn template from `OUTREACH_KIT.md`.

**Target: 20 total subscribers = ₹3,980-5,980/month**

---

## WEEK 3-4 — Scale & Convert B2B

### Upgrade 2-3 subscribers to ₹999/month Pro
Contact your most engaged subscribers (those who reply, ask questions).
Offer: **"I'll personally match tenders to your exact business type and send you a weekly call summary."**

### Post in contractor associations:
- CREDAI (builders association) local groups
- NASSCOM infrastructure group
- State PWD contractor WhatsApp groups (ask existing contacts to add you)

**Target by Day 30: 50 subscribers**
| Tier | Subscribers | Monthly Revenue |
|------|------------|-----------------|
| Basic ₹299/mo | 40 | ₹11,960 |
| Pro ₹999/mo | 8 | ₹7,992 |
| Enterprise ₹5K/mo | 1 | ₹5,000 |
| **TOTAL** | **49** | **₹24,952** |

---

## Daily Operations (30 min/day)

Every morning, run:
```bash
python main.py --full
```

This automatically:
- Scrapes fresh tenders from CPPP, GeM, BSE
- Scores them with AI
- Posts the teaser to your public channel
- Sends full digest to your private premium chat

Add new paying subscribers to tracker:
```bash
python add_subscriber.py add "Ravi Kumar" "ravi@example.com" basic
```

View revenue dashboard:
```bash
python add_subscriber.py dashboard
```

---

## Revenue Milestones

| Milestone | What to do next |
|-----------|----------------|
| First subscriber | Screenshot it. Post on LinkedIn. Social proof. |
| ₹5,000 MRR (17 subs) | Hire 1 part-time person to help with outreach |
| ₹15,000 MRR (50 subs) | Launch B2B contractor intelligence at ₹5K/mo |
| ₹50,000 MRR | Quit job / go full time |

---

## Pricing Tiers

| Plan | Price | What they get |
|------|-------|---------------|
| Free | ₹0 | 1 opportunity/day (teaser only) |
| Basic | ₹299/month | 5 top opportunities + AI scores + deadlines |
| Pro | ₹999/month | All opportunities + sector analysis + priority alerts |
| Enterprise | ₹5,000/month | Custom sector filtering + weekly WhatsApp briefing |

---

## Common Objections & Responses

**"I can check tenders myself"**
> "Sure — do you check eprocure.gov.in, gem.gov.in, BSE announcements, and 5 state portals every single day? We do. For ₹10/day you never miss a tender in your sector again."

**"₹299 is too much"**
> "One missed tender that you could have won covers 10 years of this subscription. Let me share this week's report free — judge the value yourself."

**"Is this legitimate?"**
> "Every tender I send links directly to the official government portal — eprocure.gov.in, gem.gov.in. I just find them faster and tell you which ones are worth your time."

---

*Run `python add_subscriber.py dashboard` anytime to see your revenue.*
*Update this plan as you learn what works best for your audience.*
