#!/usr/bin/env python3
"""
add_subscriber.py — Quick CLI to manage paying subscribers

Usage:
  python add_subscriber.py add "Ravi Kumar" "ravi@example.com" basic
  python add_subscriber.py add "Prasad Rao" "+91-9876543210" pro
  python add_subscriber.py list
  python add_subscriber.py dashboard
  python add_subscriber.py payment SUB_0001
  python add_subscriber.py cancel SUB_0002
"""

import sys
import json
import os
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

DATA_FILE = "./data/subscribers.json"

TIERS = {
    "free":       {"price": 0,    "label": "Free"},
    "basic":      {"price": 299,  "label": "Basic ₹299/mo"},
    "pro":        {"price": 999,  "label": "Pro ₹999/mo"},
    "enterprise": {"price": 5000, "label": "Enterprise ₹5K/mo"},
}


def load():
    os.makedirs("./data", exist_ok=True)
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"subscribers": [], "revenue_log": [], "leads_contacted": [],
            "created_at": datetime.now().isoformat()}


def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def log_revenue(data, amount, source_id, event_type):
    data["revenue_log"].append({
        "amount": amount, "source_id": source_id,
        "event_type": event_type, "date": datetime.now().isoformat()
    })


# ── Commands ──────────────────────────────────────────────

def cmd_add(args):
    """python add_subscriber.py add "Name" "email_or_phone" [tier] [source]"""
    if len(args) < 2:
        console.print("[red]Usage: add \"Name\" \"contact\" [basic|pro|enterprise] [source][/red]")
        return

    data = load()
    name    = args[0]
    contact = args[1]
    tier    = args[2] if len(args) > 2 else "basic"
    source  = args[3] if len(args) > 3 else "manual"

    if tier not in TIERS:
        console.print(f"[red]Unknown tier '{tier}'. Use: free, basic, pro, enterprise[/red]")
        return

    sub_id = f"SUB_{len(data['subscribers']) + 1:04d}"
    price  = TIERS[tier]["price"]

    subscriber = {
        "id":           sub_id,
        "name":         name,
        "contact":      contact,
        "tier":         tier,
        "price":        price,
        "status":       "active",
        "source":       source,
        "joined_at":    datetime.now().isoformat(),
        "next_billing": (datetime.now() + timedelta(days=30)).isoformat(),
        "total_paid":   price,
    }

    data["subscribers"].append(subscriber)
    log_revenue(data, price, sub_id, "new_subscription")
    save(data)

    console.print(Panel(
        f"[bold green]✅ Subscriber added![/bold green]\n\n"
        f"  ID:      [cyan]{sub_id}[/cyan]\n"
        f"  Name:    {name}\n"
        f"  Contact: {contact}\n"
        f"  Tier:    {TIERS[tier]['label']}\n"
        f"  Revenue: [green]₹{price:,}/month[/green]\n"
        f"  Billing: {subscriber['next_billing'][:10]}",
        title="New Subscriber", border_style="green"
    ))


def cmd_list(args):
    """python add_subscriber.py list"""
    data = load()
    subs = [s for s in data["subscribers"] if s.get("status") == "active"]

    if not subs:
        console.print("[yellow]No active subscribers yet. Run: python add_subscriber.py add ...[/yellow]")
        return

    t = Table(title=f"Active Subscribers ({len(subs)})", box=box.ROUNDED,
              header_style="bold cyan", show_lines=True)
    t.add_column("ID",      width=10)
    t.add_column("Name",    width=28)
    t.add_column("Contact", width=24)
    t.add_column("Tier",    width=12)
    t.add_column("₹/mo",   width=7)
    t.add_column("Next Bill", width=12)
    t.add_column("Source",  width=12)

    for s in subs:
        next_bill = s.get("next_billing", "")[:10]
        t.add_row(
            s["id"], s["name"][:27], s["contact"][:23],
            s["tier"], str(s["price"]), next_bill, s.get("source", "—")
        )
    console.print(t)


def cmd_dashboard(args):
    """python add_subscriber.py dashboard"""
    data = load()
    subs   = data["subscribers"]
    active = [s for s in subs if s.get("status") == "active"]
    mrr    = sum(s["price"] for s in active)
    total  = sum(e["amount"] for e in data.get("revenue_log", []))

    tier_breakdown = {}
    for s in active:
        tier_breakdown[s["tier"]] = tier_breakdown.get(s["tier"], 0) + 1

    goal = 50000
    progress = min(mrr / goal, 1.0) if goal > 0 else 0
    filled = int(progress * 35)
    bar = "█" * filled + "░" * (35 - filled)

    console.print(Panel(
        f"[bold cyan]💰 OPPORTUNITY SCOUT — REVENUE DASHBOARD[/bold cyan]\n"
        f"[dim]{datetime.now().strftime('%d %B %Y, %I:%M %p')}[/dim]",
        border_style="cyan"
    ))

    # MRR metrics
    m = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    m.add_column("Metric", style="dim", width=32)
    m.add_column("Value",  style="bold green")
    m.add_row("Monthly Recurring Revenue (MRR)", f"₹{mrr:,}")
    m.add_row("Annual Run Rate (ARR)",            f"₹{mrr*12:,}")
    m.add_row("Total Collected",                  f"₹{total:,}")
    m.add_row("Active Subscribers",               str(len(active)))
    m.add_row("Conversion Events",               str(len(data.get("revenue_log", []))))
    console.print("\n[bold]📊 METRICS[/bold]")
    console.print(m)

    # Tier breakdown
    if tier_breakdown:
        console.print("\n[bold]📦 TIER BREAKDOWN[/bold]")
        for tier, count in tier_breakdown.items():
            price = TIERS.get(tier, {}).get("price", 0)
            console.print(f"  {tier.upper():12}  {count:3} × ₹{price:,} = [green]₹{count*price:,}/mo[/green]")

    # Goal bar
    console.print(f"\n[bold]🎯 GOAL: ₹{goal:,} MRR[/bold]")
    console.print(f"[cyan]{bar}[/cyan] {progress*100:.0f}%")
    needed = max(0, goal - mrr) // 299
    console.print(f"[dim]₹{mrr:,} / ₹{goal:,}  —  need ~{needed} more Basic subscribers[/dim]\n")


def cmd_payment(args):
    """python add_subscriber.py payment SUB_0001"""
    if not args:
        console.print("[red]Usage: payment SUB_XXXX[/red]")
        return

    data   = load()
    sub_id = args[0].upper()
    for s in data["subscribers"]:
        if s["id"] == sub_id:
            s["total_paid"]   = s.get("total_paid", 0) + s["price"]
            s["last_payment"] = datetime.now().isoformat()
            s["next_billing"] = (datetime.now() + timedelta(days=30)).isoformat()
            log_revenue(data, s["price"], sub_id, "renewal")
            save(data)
            console.print(f"[green]💰 Payment recorded for {s['name']} — ₹{s['price']:,}[/green]")
            return

    console.print(f"[red]Subscriber {sub_id} not found. Run: python add_subscriber.py list[/red]")


def cmd_cancel(args):
    """python add_subscriber.py cancel SUB_0001"""
    if not args:
        console.print("[red]Usage: cancel SUB_XXXX[/red]")
        return

    data   = load()
    sub_id = args[0].upper()
    for s in data["subscribers"]:
        if s["id"] == sub_id:
            s["status"]       = "cancelled"
            s["cancelled_at"] = datetime.now().isoformat()
            save(data)
            console.print(f"[yellow]⚠️  {s['name']} ({sub_id}) marked as cancelled.[/yellow]")
            return

    console.print(f"[red]Subscriber {sub_id} not found.[/red]")


def cmd_help(args):
    console.print(Panel(
        "[bold]COMMANDS[/bold]\n\n"
        "  [cyan]add[/cyan] \"Name\" \"email/phone\" [tier] [source]\n"
        "    [dim]tier: basic (₹299) | pro (₹999) | enterprise (₹5000)[/dim]\n\n"
        "  [cyan]list[/cyan]\n"
        "    [dim]Show all active subscribers[/dim]\n\n"
        "  [cyan]dashboard[/cyan]\n"
        "    [dim]Revenue metrics and goal tracker[/dim]\n\n"
        "  [cyan]payment[/cyan] SUB_XXXX\n"
        "    [dim]Record a renewal payment[/dim]\n\n"
        "  [cyan]cancel[/cyan] SUB_XXXX\n"
        "    [dim]Mark a subscriber as cancelled[/dim]\n\n"
        "[bold]EXAMPLES[/bold]\n\n"
        '  python add_subscriber.py add "Ravi Kumar" "ravi@example.com" basic telegram\n'
        '  python add_subscriber.py add "Prasad Rao" "+91-9876543210" pro linkedin\n'
        "  python add_subscriber.py dashboard\n"
        "  python add_subscriber.py payment SUB_0001",
        title="Opportunity Scout — Subscriber Manager", border_style="cyan"
    ))


COMMANDS = {
    "add":       cmd_add,
    "list":      cmd_list,
    "dashboard": cmd_dashboard,
    "payment":   cmd_payment,
    "cancel":    cmd_cancel,
    "help":      cmd_help,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        cmd_help([])
    else:
        COMMANDS[sys.argv[1]](sys.argv[2:])
