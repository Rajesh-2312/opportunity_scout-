"""
monetization/customer_pipeline.py

Full customer lifecycle pipeline:
  1. Onboard new paying subscriber → save + send Telegram welcome
  2. Daily renewal check → remind subscribers expiring in 3 days
  3. Mark renewals paid / cancel lapsed subscriptions
  4. Revenue summary posted to your private Telegram every morning

Run modes:
  python monetization/customer_pipeline.py onboard    # add a new customer
  python monetization/customer_pipeline.py renew      # mark a renewal paid
  python monetization/customer_pipeline.py check      # run renewal reminders
  python monetization/customer_pipeline.py summary    # post revenue summary to Telegram
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()
console = Console()

DATA_FILE = "./data/subscribers.json"
RAZORPAY_LINK = os.getenv("RAZORPAY_PAYMENT_LINK", "https://razorpay.me/@marojurajesh")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OWNER_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TIERS = {
    "free":       {"price": 0,    "label": "Free"},
    "basic":      {"price": 299,  "label": "Basic ₹299/mo"},
    "pro":        {"price": 999,  "label": "Pro ₹999/mo"},
    "enterprise": {"price": 5000, "label": "Enterprise ₹5K/mo"},
}


# ─────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────

def load_data() -> Dict:
    os.makedirs("./data", exist_ok=True)
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"subscribers": [], "revenue_log": [], "leads_contacted": [],
            "created_at": datetime.now().isoformat()}


def save_data(data: Dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def log_revenue(data, amount, source_id, event_type):
    data["revenue_log"].append({
        "amount": amount, "source_id": source_id,
        "event_type": event_type, "date": datetime.now().isoformat()
    })


# ─────────────────────────────────────────────
# Telegram sender
# ─────────────────────────────────────────────

async def send_telegram(chat_id: str, text: str) -> bool:
    if not BOT_TOKEN or not chat_id:
        console.print(f"[yellow]📱 [Telegram not configured] Would send to {chat_id}:[/yellow]")
        console.print(text[:300])
        return False
    try:
        import aiohttp
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text[:4096],
                   "parse_mode": "HTML", "disable_web_page_preview": True}
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as r:
                ok = r.status == 200
                if not ok:
                    console.print(f"[red]Telegram error {r.status}: {await r.text()}[/red]")
                return ok
    except Exception as e:
        console.print(f"[red]Telegram send failed: {e}[/red]")
        return False


def tg(chat_id: str, text: str) -> bool:
    return asyncio.run(send_telegram(chat_id, text))


# ─────────────────────────────────────────────
# 1. ONBOARD NEW CUSTOMER
# ─────────────────────────────────────────────

def onboard_customer(name: str, contact: str, tier: str,
                     source: str = "manual", telegram_id: str = "") -> Dict:
    """
    Add a new paying subscriber and send them a Telegram welcome message.
    contact   = email or phone
    telegram_id = their Telegram user ID or @username (optional but enables direct messages)
    """
    if tier not in TIERS:
        console.print(f"[red]Unknown tier '{tier}'. Use: basic, pro, enterprise[/red]")
        sys.exit(1)

    data = load_data()
    price = TIERS[tier]["price"]
    sub_id = f"SUB_{len(data['subscribers']) + 1:04d}"
    next_bill = (datetime.now() + timedelta(days=30)).isoformat()

    subscriber = {
        "id":           sub_id,
        "name":         name,
        "contact":      contact,
        "telegram_id":  telegram_id,
        "tier":         tier,
        "price":        price,
        "status":       "active",
        "source":       source,
        "joined_at":    datetime.now().isoformat(),
        "next_billing": next_bill,
        "total_paid":   price,
        "renewals":     1,
    }

    data["subscribers"].append(subscriber)
    log_revenue(data, price, sub_id, "new_subscription")
    save_data(data)

    # ── Welcome message to customer ──────────────────────────
    if telegram_id:
        welcome = f"""🎉 <b>Welcome to India Infra Intelligence, {name.split()[0]}!</b>

Your <b>{TIERS[tier]['label']}</b> subscription is now active.

Here's what happens next:
✅ You'll receive daily tender alerts every morning
✅ Full AI analysis — which tenders have lowest competition
✅ Deadline reminders so you never miss a bid
✅ Direct access to me for any questions

📅 <b>Your next billing date:</b> {next_bill[:10]}
💳 <b>Payment link for renewal:</b> {RAZORPAY_LINK}

Today's intelligence digest will arrive in your Telegram shortly.

Questions? Just reply to this message.

— Rajesh M., India Infra Intelligence 🇮🇳"""
        sent = tg(telegram_id, welcome)
        console.print(f"[{'green' if sent else 'yellow'}]{'✅ Welcome message sent' if sent else '⚠️ Welcome message failed (no Telegram ID?)'}[/]")

    # ── Notify yourself ──────────────────────────────────────
    owner_msg = f"""💰 <b>NEW SUBSCRIBER!</b>

👤 {name}
📱 {contact}
💼 {TIERS[tier]['label']}
📣 Source: {source}
🆔 ID: {sub_id}

💵 MRR impact: +₹{price:,}/month
📅 Bills on: {next_bill[:10]}
🔗 {RAZORPAY_LINK}"""
    tg(OWNER_CHAT_ID, owner_msg)

    console.print(Panel(
        f"[bold green]✅ Customer onboarded![/bold green]\n\n"
        f"  ID:      [cyan]{sub_id}[/cyan]\n"
        f"  Name:    {name}\n"
        f"  Tier:    {TIERS[tier]['label']}\n"
        f"  Revenue: [green]₹{price:,}/month[/green]\n"
        f"  Bills:   {next_bill[:10]}",
        title="New Subscriber", border_style="green"
    ))

    return subscriber


# ─────────────────────────────────────────────
# 2. RENEWAL REMINDERS
# ─────────────────────────────────────────────

def run_renewal_check():
    """
    Called daily. Sends renewal reminders to subscribers expiring in 1-3 days.
    Auto-flags overdue (>5 days past billing) as lapsed.
    """
    data = load_data()
    today = datetime.now().date()
    reminders_sent = 0
    lapsed = 0

    for sub in data["subscribers"]:
        if sub.get("status") != "active":
            continue

        try:
            bill_date = datetime.fromisoformat(sub["next_billing"]).date()
        except Exception:
            continue

        days_until = (bill_date - today).days

        # ── Reminder: 3 days before ─────────────────────────
        if days_until in (3, 1):
            tid = sub.get("telegram_id", "")
            if tid:
                msg = f"""⏰ <b>Renewal reminder, {sub['name'].split()[0]}!</b>

Your <b>India Infra Intelligence</b> subscription renews in <b>{days_until} day{'s' if days_until > 1 else ''}</b>.

📅 Renewal date: {bill_date}
💳 Amount: ₹{sub['price']:,}
🔗 Pay here: {RAZORPAY_LINK}

Once paid, your access continues uninterrupted.
Reply "paid" and I'll confirm immediately.

— Rajesh M."""
                if tg(tid, msg):
                    reminders_sent += 1
                    console.print(f"[green]✅ Reminder sent → {sub['name']} (expires {bill_date})[/green]")

        # ── Auto-lapse: 5+ days overdue ──────────────────────
        elif days_until < -5:
            sub["status"] = "lapsed"
            sub["lapsed_at"] = datetime.now().isoformat()
            lapsed += 1
            console.print(f"[yellow]⚠️  Marked lapsed: {sub['name']} (overdue {abs(days_until)} days)[/yellow]")
            # Notify owner
            tg(OWNER_CHAT_ID, f"⚠️ <b>Lapsed subscriber:</b> {sub['name']} ({sub['tier']}) — {abs(days_until)} days overdue. ₹{sub['price']:,}/mo lost.")

    save_data(data)
    console.print(f"[bold]Renewal check done — {reminders_sent} reminders sent, {lapsed} lapsed[/bold]")
    return {"reminders_sent": reminders_sent, "lapsed": lapsed}


# ─────────────────────────────────────────────
# 3. MARK RENEWAL PAID
# ─────────────────────────────────────────────

def mark_renewal_paid(sub_id: str):
    """Call this when a subscriber pays their renewal."""
    data = load_data()
    sub_id = sub_id.upper()

    for sub in data["subscribers"]:
        if sub["id"] == sub_id:
            sub["total_paid"] = sub.get("total_paid", 0) + sub["price"]
            sub["renewals"]   = sub.get("renewals", 1) + 1
            sub["last_payment"] = datetime.now().isoformat()
            sub["next_billing"] = (datetime.now() + timedelta(days=30)).isoformat()
            sub["status"] = "active"
            log_revenue(data, sub["price"], sub_id, "renewal")
            save_data(data)

            console.print(f"[green]💰 Renewal recorded for {sub['name']} — ₹{sub['price']:,}[/green]")

            # Thank-you message
            if sub.get("telegram_id"):
                tg(sub["telegram_id"],
                   f"✅ <b>Payment received, {sub['name'].split()[0]}!</b>\n\n"
                   f"Thank you for renewing your India Infra Intelligence subscription.\n"
                   f"📅 Next billing: {sub['next_billing'][:10]}\n\n"
                   f"Your daily alerts continue — see you tomorrow morning! 🚀")

            # Notify owner
            tg(OWNER_CHAT_ID,
               f"💰 <b>Renewal received!</b>\n{sub['name']} — ₹{sub['price']:,} ({sub['tier']})\n"
               f"Total paid: ₹{sub['total_paid']:,} | Renewals: {sub['renewals']}")
            return

    console.print(f"[red]Subscriber {sub_id} not found. Run: python add_subscriber.py list[/red]")


# ─────────────────────────────────────────────
# 4. DAILY REVENUE SUMMARY (posted to your Telegram)
# ─────────────────────────────────────────────

def post_revenue_summary():
    """Post MRR snapshot to owner's Telegram every morning."""
    data = load_data()
    subs   = data["subscribers"]
    active = [s for s in subs if s.get("status") == "active"]
    lapsed = [s for s in subs if s.get("status") == "lapsed"]
    mrr    = sum(s["price"] for s in active)
    total  = sum(e["amount"] for e in data.get("revenue_log", []))

    # Expiring soon
    today = datetime.now().date()
    expiring = [
        s for s in active
        if (datetime.fromisoformat(s["next_billing"]).date() - today).days <= 7
    ]

    tier_lines = ""
    breakdown: Dict[str, int] = {}
    for s in active:
        breakdown[s["tier"]] = breakdown.get(s["tier"], 0) + 1
    for tier, count in breakdown.items():
        price = TIERS.get(tier, {}).get("price", 0)
        tier_lines += f"\n  {tier.upper():12} {count} × ₹{price:,} = ₹{count*price:,}/mo"

    expiry_lines = ""
    for s in expiring:
        bill = datetime.fromisoformat(s["next_billing"]).date()
        days = (bill - today).days
        expiry_lines += f"\n  • {s['name']} — {bill} ({days}d)"

    msg = f"""📊 <b>DAILY REVENUE SUMMARY</b>
📅 {datetime.now().strftime('%d %B %Y')}

💰 <b>MRR: ₹{mrr:,}/month</b>
📈 ARR: ₹{mrr*12:,}/year
💵 Total collected: ₹{total:,}

👥 Active subscribers: {len(active)}
❌ Lapsed: {len(lapsed)}
{tier_lines}

⏰ <b>Expiring this week ({len(expiring)}):</b>{expiry_lines if expiry_lines else ' None'}

🎯 Goal: ₹50,000 MRR — {mrr/50000*100:.0f}% there
{"🟢 " * int(mrr/50000*10)}{"⬜ " * (10 - int(mrr/50000*10))}

💳 Payment link: {RAZORPAY_LINK}"""

    sent = tg(OWNER_CHAT_ID, msg)
    console.print(f"[{'green' if sent else 'yellow'}]{'✅ Revenue summary sent to Telegram' if sent else '⚠️  Revenue summary (Telegram not configured)'}[/]")
    console.print(f"  MRR: ₹{mrr:,} | Active: {len(active)} | Total collected: ₹{total:,}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Opportunity Scout — Customer Pipeline")
    sub = parser.add_subparsers(dest="cmd")

    # onboard
    p_on = sub.add_parser("onboard", help="Add a new paying customer")
    p_on.add_argument("name",    help="Customer full name")
    p_on.add_argument("contact", help="Email or phone")
    p_on.add_argument("tier",    choices=["basic","pro","enterprise"], default="basic", nargs="?")
    p_on.add_argument("--source",      default="manual", help="Where they came from")
    p_on.add_argument("--telegram-id", default="",       help="Their Telegram user ID or @username")

    # renew
    p_re = sub.add_parser("renew", help="Mark a renewal payment received")
    p_re.add_argument("sub_id", help="e.g. SUB_0001")

    # check
    sub.add_parser("check", help="Run renewal reminders + lapse check")

    # summary
    sub.add_parser("summary", help="Post revenue summary to your Telegram")

    args = parser.parse_args()

    if args.cmd == "onboard":
        onboard_customer(args.name, args.contact, args.tier,
                         args.source, getattr(args, "telegram_id", ""))
    elif args.cmd == "renew":
        mark_renewal_paid(args.sub_id)
    elif args.cmd == "check":
        run_renewal_check()
    elif args.cmd == "summary":
        post_revenue_summary()
    else:
        console.print(Panel(
            "[bold]CUSTOMER PIPELINE COMMANDS[/bold]\n\n"
            '  [cyan]onboard[/cyan] "Name" "email/phone" [basic|pro|enterprise]\n'
            '    [dim]--source telegram|linkedin|whatsapp|referral[/dim]\n'
            '    [dim]--telegram-id @username (enables direct messages)[/dim]\n\n'
            '  [cyan]renew[/cyan] SUB_0001\n'
            '    [dim]Mark a renewal payment as received[/dim]\n\n'
            '  [cyan]check[/cyan]\n'
            '    [dim]Send renewal reminders + auto-lapse overdue subscribers[/dim]\n\n'
            '  [cyan]summary[/cyan]\n'
            '    [dim]Post revenue snapshot to your Telegram[/dim]\n\n'
            "[bold]EXAMPLES[/bold]\n\n"
            '  python monetization/customer_pipeline.py onboard "Ravi Kumar" "+91-9876543210" basic --source telegram --telegram-id @ravikumar\n'
            '  python monetization/customer_pipeline.py renew SUB_0001\n'
            '  python monetization/customer_pipeline.py check\n'
            '  python monetization/customer_pipeline.py summary',
            title="Customer Pipeline", border_style="cyan"
        ))


if __name__ == "__main__":
    main()
