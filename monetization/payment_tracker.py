"""
monetization/payment_tracker.py

Tracks subscribers, revenue, and growth metrics.
Stores data locally in JSON (no database needed).
Shows P&L dashboard in terminal.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

DATA_FILE = "./data/subscribers.json"


# ─────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────
def load_data() -> Dict:
    os.makedirs("./data", exist_ok=True)
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {
        "subscribers": [],
        "revenue_log": [],
        "leads_contacted": [],
        "created_at": datetime.now().isoformat()
    }


def save_data(data: Dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ─────────────────────────────────────────────
# Subscriber Management
# ─────────────────────────────────────────────
class SubscriberTracker:
    """Track who's paying and what tier"""

    TIERS = {
        "free": {"price": 0, "label": "Free", "features": "1 opportunity/day"},
        "basic": {"price": 299, "label": "Basic ₹299/mo", "features": "5 opportunities + analysis"},
        "pro": {"price": 999, "label": "Pro ₹999/mo", "features": "All + lead matching + alerts"},
        "enterprise": {"price": 5000, "label": "Enterprise ₹5K/mo", "features": "Custom + direct calls"},
    }

    def __init__(self):
        self.data = load_data()

    def add_subscriber(self, name: str, contact: str,
                       tier: str = "basic",
                       source: str = "manual") -> Dict:
        subscriber = {
            "id": f"SUB_{len(self.data['subscribers']) + 1:04d}",
            "name": name,
            "contact": contact,
            "tier": tier,
            "price": self.TIERS.get(tier, {}).get("price", 299),
            "status": "active",
            "source": source,
            "joined_at": datetime.now().isoformat(),
            "next_billing": (datetime.now() + timedelta(days=30)).isoformat(),
            "total_paid": 0
        }

        self.data["subscribers"].append(subscriber)
        self._log_revenue(subscriber["price"], subscriber["id"], "new_subscription")
        save_data(self.data)

        console.print(f"[green]✅ Subscriber added: {name} ({tier})[/green]")
        return subscriber

    def mark_payment(self, subscriber_id: str) -> bool:
        for sub in self.data["subscribers"]:
            if sub["id"] == subscriber_id:
                sub["total_paid"] = sub.get("total_paid", 0) + sub["price"]
                sub["last_payment"] = datetime.now().isoformat()
                sub["next_billing"] = (datetime.now() + timedelta(days=30)).isoformat()
                self._log_revenue(sub["price"], subscriber_id, "renewal")
                save_data(self.data)
                console.print(f"[green]💰 Payment marked for {sub['name']}[/green]")
                return True
        return False

    def add_lead_contacted(self, company: str, contact: str, method: str = "email"):
        lead = {
            "company": company,
            "contact": contact,
            "method": method,
            "contacted_at": datetime.now().isoformat(),
            "status": "sent"
        }
        self.data["leads_contacted"].append(lead)
        save_data(self.data)

    def _log_revenue(self, amount: float, source_id: str, event_type: str):
        self.data["revenue_log"].append({
            "amount": amount,
            "source_id": source_id,
            "event_type": event_type,
            "date": datetime.now().isoformat()
        })

    def get_metrics(self) -> Dict:
        subs = self.data["subscribers"]
        active = [s for s in subs if s.get("status") == "active"]

        mrr = sum(s["price"] for s in active)
        total_collected = sum(e["amount"] for e in self.data["revenue_log"])

        tier_breakdown = {}
        for s in active:
            tier = s["tier"]
            tier_breakdown[tier] = tier_breakdown.get(tier, 0) + 1

        return {
            "total_subscribers": len(subs),
            "active_subscribers": len(active),
            "mrr": mrr,
            "arr": mrr * 12,
            "total_collected": total_collected,
            "leads_contacted": len(self.data["leads_contacted"]),
            "tier_breakdown": tier_breakdown,
            "conversion_rate": (
                round(len(active) / len(self.data["leads_contacted"]) * 100, 1)
                if self.data["leads_contacted"] else 0
            )
        }


# ─────────────────────────────────────────────
# Revenue Dashboard
# ─────────────────────────────────────────────
class RevenueDashboard:
    """Terminal dashboard showing P&L and growth"""

    def __init__(self):
        self.tracker = SubscriberTracker()

    def display(self):
        metrics = self.tracker.get_metrics()
        data = self.tracker.data

        # ── Header ──────────────────────────────────
        console.print(Panel(
            f"[bold cyan]💰 OPPORTUNITY SCOUT — REVENUE DASHBOARD[/bold cyan]\n"
            f"[dim]{datetime.now().strftime('%d %B %Y, %I:%M %p')}[/dim]",
            style="cyan"
        ))

        # ── Revenue Metrics ──────────────────────────
        console.print("\n[bold]📊 REVENUE METRICS[/bold]")
        metrics_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        metrics_table.add_column("Metric", style="dim")
        metrics_table.add_column("Value", style="bold green")

        metrics_table.add_row("Monthly Recurring Revenue (MRR)", f"₹{metrics['mrr']:,}")
        metrics_table.add_row("Annual Run Rate (ARR)", f"₹{metrics['arr']:,}")
        metrics_table.add_row("Total Collected", f"₹{metrics['total_collected']:,}")
        metrics_table.add_row("Active Subscribers", str(metrics["active_subscribers"]))
        metrics_table.add_row("Leads Contacted", str(metrics["leads_contacted"]))
        metrics_table.add_row("Conversion Rate", f"{metrics['conversion_rate']}%")
        console.print(metrics_table)

        # ── Subscribers ──────────────────────────────
        subs = data["subscribers"]
        if subs:
            console.print("\n[bold]👥 SUBSCRIBERS[/bold]")
            sub_table = Table(box=box.ROUNDED, show_header=True,
                              header_style="bold cyan")
            sub_table.add_column("ID", width=10)
            sub_table.add_column("Name", width=25)
            sub_table.add_column("Tier", width=12)
            sub_table.add_column("₹/mo", width=8)
            sub_table.add_column("Status", width=10)
            sub_table.add_column("Joined", width=12)

            for s in subs[-10:]:  # Show last 10
                status_style = "green" if s.get("status") == "active" else "red"
                sub_table.add_row(
                    s["id"],
                    s["name"][:24],
                    s["tier"],
                    str(s["price"]),
                    f"[{status_style}]{s.get('status', 'active')}[/{status_style}]",
                    s["joined_at"][:10]
                )
            console.print(sub_table)

        # ── Goal Tracker ─────────────────────────────
        goal_mrr = 50000
        progress = min(metrics["mrr"] / goal_mrr, 1.0)
        bar_len = 30
        filled = int(progress * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        console.print(f"\n[bold]🎯 GOAL: ₹50,000 MRR[/bold]")
        console.print(f"[cyan]{bar}[/cyan] {progress*100:.0f}%")
        console.print(f"[dim]₹{metrics['mrr']:,} / ₹{goal_mrr:,} — "
                      f"Need {max(0, goal_mrr - metrics['mrr'])//299} more Basic subscribers[/dim]")

        # ── Tier Breakdown ───────────────────────────
        if metrics["tier_breakdown"]:
            console.print("\n[bold]📦 TIER BREAKDOWN[/bold]")
            for tier, count in metrics["tier_breakdown"].items():
                price = SubscriberTracker.TIERS.get(tier, {}).get("price", 0)
                console.print(f"  {tier.upper():12} {count:3} subs × ₹{price:5,} = ₹{count*price:,}/mo")


# ─────────────────────────────────────────────
# Quick Actions
# ─────────────────────────────────────────────
def add_sample_data():
    """Add sample data to see the dashboard in action"""
    tracker = SubscriberTracker()
    tracker.add_subscriber("Ravi Kumar - Sri Venkateswara Contractors", "ravi@svcivil.com", "basic", "indiamart")
    tracker.add_subscriber("Prasad Rao - Andhra EPC", "prasad@andhraEPC.com", "pro", "linkedin")
    tracker.add_subscriber("Suresh Reddy - Green Power", "suresh@greenpowerap.com", "basic", "telegram")
    tracker.add_lead_contacted("ABC Infra Ltd", "contact@abc.com", "email")
    tracker.add_lead_contacted("XYZ Construction", "info@xyz.com", "email")
    console.print("[green]✅ Sample data added[/green]")


if __name__ == "__main__":
    # Add sample data and show dashboard
    add_sample_data()
    dashboard = RevenueDashboard()
    dashboard.display()
