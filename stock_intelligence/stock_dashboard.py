"""
stock_intelligence/stock_dashboard.py

Displays stock intelligence in terminal + generates reports.
Shows: signals, portfolio, sector heat map, top picks.
"""

import os
import json
from datetime import datetime
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

console = Console()


class StockDashboard:
    """
    Terminal dashboard for stock intelligence.
    Visual, actionable, zero cost.
    """

    def display_signals(self, signals: List[Dict]):
        """Display ranked stock signals table"""
        if not signals:
            console.print("[yellow]No stock signals generated yet.[/yellow]")
            return

        table = Table(
            title="📡 Stock Intelligence Signals",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("#",          width=4)
        table.add_column("Symbol",     width=14)
        table.add_column("Action",     width=30)
        table.add_column("Type",       width=12)
        table.add_column("Score",      width=7)
        table.add_column("Hold",       width=8)
        table.add_column("Reason",     max_width=40)

        for i, sig in enumerate(signals[:15], 1):
            action = sig.get("action", "")
            action_style = (
                "bold green"  if "STRONG BUY" in action else
                "green"       if "BUY" in action else
                "yellow"      if "WATCH" in action else
                "dim"
            )

            table.add_row(
                str(i),
                sig.get("symbol", ""),
                f"[{action_style}]{action}[/{action_style}]",
                sig.get("signal_type", ""),
                str(sig.get("strength", 0)),
                f"{sig.get('hold_days', 0)}d",
                sig.get("reasoning", "")[:40]
            )

        console.print(table)

    def display_portfolio(self, portfolio: Dict, open_trades: List[Dict]):
        """Display current paper portfolio status"""
        # Summary panel
        pnl = portfolio.get("total_pnl", 0)
        pnl_color = "green" if pnl >= 0 else "red"
        win_rate = portfolio.get("win_rate", 0)

        summary = (
            f"[bold]Available Capital:[/bold] ₹{portfolio.get('available_capital', 0):,.0f}\n"
            f"[bold]Invested:[/bold]          ₹{portfolio.get('invested_capital', 0):,.0f}\n"
            f"[bold]Total P&L:[/bold]         [{pnl_color}]₹{pnl:+,.0f}[/{pnl_color}]\n"
            f"[bold]Win Rate:[/bold]           {win_rate}% "
            f"({portfolio.get('wins', 0)}W / {portfolio.get('losses', 0)}L)\n"
            f"[bold]Avg Return:[/bold]        {portfolio.get('avg_return_pct', 0):+.1f}%\n"
            f"[bold]Closed Trades:[/bold]     {portfolio.get('total_trades', 0)}"
        )

        ready = portfolio.get("is_ready_for_real_trading", False)
        status = "[bold green]✅ READY FOR REAL MONEY[/bold green]" if ready else \
                 "[yellow]📈 Still validating signals[/yellow]"

        console.print(Panel(
            summary + "\n\n" + status,
            title="💼 Paper Portfolio",
            style="cyan"
        ))

        # Open trades
        if open_trades:
            otable = Table(
                title=f"📂 Open Trades ({len(open_trades)})",
                box=box.SIMPLE,
                header_style="bold"
            )
            otable.add_column("ID",       width=8)
            otable.add_column("Symbol",   width=12)
            otable.add_column("Entry ₹",  width=10)
            otable.add_column("Target ₹", width=10)
            otable.add_column("Stop ₹",   width=10)
            otable.add_column("Qty",      width=6)
            otable.add_column("Value ₹",  width=12)
            otable.add_column("Exit By",  width=12)

            for t in open_trades:
                otable.add_row(
                    t.get("id", ""),
                    t.get("symbol", ""),
                    f"₹{t.get('entry_price', 0):,.1f}",
                    f"₹{t.get('target_price', 0):,.1f}",
                    f"₹{t.get('stop_loss', 0):,.1f}",
                    str(t.get("quantity", 0)),
                    f"₹{t.get('investment', 0):,.0f}",
                    t.get("exit_date_planned", "")
                )

            console.print(otable)

    def display_sector_heatmap(self, signals: List[Dict]):
        """Show which sectors have strongest signals"""
        sector_scores = {}
        for sig in signals:
            sector = sig.get("sector", "other")
            score = sig.get("strength", 0)
            if sector not in sector_scores:
                sector_scores[sector] = []
            sector_scores[sector].append(score)

        if not sector_scores:
            return

        # Average scores by sector
        avg_scores = {
            s: round(sum(scores) / len(scores), 1)
            for s, scores in sector_scores.items()
        }
        sorted_sectors = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)

        console.print("\n[bold]🌡️ SECTOR HEAT MAP[/bold]")
        for sector, score in sorted_sectors:
            bar_len = int(score * 3)
            color = "bold red" if score >= 8 else "yellow" if score >= 6 else "dim"
            bar = "█" * bar_len
            console.print(
                f"  {sector:15} [{color}]{bar}[/{color}] {score}/10 "
                f"({len(sector_scores[sector])} signals)"
            )

    def generate_telegram_report(self, signals: List[Dict],
                                  portfolio: Dict) -> str:
        """Format stock intelligence as Telegram message"""
        today = datetime.now().strftime("%d %b %Y")
        top_buys = [s for s in signals if "BUY" in s.get("action", "")][:5]

        lines = [
            f"📡 <b>STOCK INTELLIGENCE REPORT</b>",
            f"📅 {today}",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"🎯 <b>TOP PICKS THIS WEEK</b>",
            f"",
        ]

        for i, sig in enumerate(top_buys, 1):
            action_icon = "🔥" if "STRONG" in sig.get("action", "") else "⭐"
            lines += [
                f"{action_icon} <b>#{i} {sig.get('symbol')}</b> — {sig.get('company_name', '')}",
                f"   📊 Signal: {sig.get('signal_type')} | Score: {sig.get('strength')}/10",
                f"   💡 {sig.get('reasoning', '')[:80]}",
                f"   ⏳ Hold: {sig.get('hold_days', 0)} days",
                f"",
            ]

        # Portfolio summary
        pnl = portfolio.get("total_pnl", 0)
        lines += [
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"💼 <b>PAPER PORTFOLIO</b>",
            f"Open trades: {portfolio.get('open_trades', 0)}",
            f"Closed: {portfolio.get('total_trades', 0)} | Win rate: {portfolio.get('win_rate', 0)}%",
            f"Total P&L: ₹{pnl:+,.0f}",
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"⚠️ <i>Paper trading only. Not financial advice.</i>",
            f"🤖 <i>Powered by Opportunity Scout AI</i>",
        ]

        return "\n".join(lines)

    def save_report(self, signals: List[Dict], portfolio: Dict,
                    output_dir: str = "./reports") -> str:
        """Save stock intelligence report to file"""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{output_dir}/stock_intel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report_data = {
            "generated_at": datetime.now().isoformat(),
            "signals": signals[:20],
            "portfolio_summary": portfolio,
            "top_buys": [s for s in signals if "BUY" in s.get("action", "")][:5],
            "disclaimer": "Paper trading only. Not financial advice."
        }

        with open(filename, "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        console.print(f"[green]💾 Stock report saved: {filename}[/green]")
        return filename


def run_stock_dashboard(signals: List[Dict], portfolio: Dict,
                         open_trades: List[Dict]):
    """Display complete stock intelligence dashboard"""
    dashboard = StockDashboard()

    console.print("\n")
    console.print(Panel(
        "[bold cyan]📡 STOCK INTELLIGENCE LAYER[/bold cyan]\n"
        "[dim]Tender data → Stock signals → Paper trades → Wealth[/dim]",
        style="cyan"
    ))

    dashboard.display_signals(signals)
    dashboard.display_sector_heatmap(signals)
    dashboard.display_portfolio(portfolio, open_trades)

    return dashboard


if __name__ == "__main__":
    mock_signals = [
        {
            "symbol": "ADANIGREEN", "company_name": "Adani Green Energy",
            "sector": "solar", "signal_type": "DIRECT",
            "strength": 9.2, "action": "🟢 STRONG BUY — Pre-announcement alpha",
            "reasoning": "500MW solar tender direct beneficiary",
            "hold_days": 60
        },
        {
            "symbol": "POLYCAB", "company_name": "Polycab India",
            "sector": "power", "signal_type": "INDIRECT",
            "strength": 7.1, "action": "🟢 BUY — Strong direct beneficiary",
            "reasoning": "Cable demand from power infra tenders",
            "hold_days": 30
        },
    ]
    mock_portfolio = {
        "total_trades": 3, "wins": 2, "losses": 1,
        "win_rate": 66.7, "total_pnl": 12450,
        "avg_return_pct": 11.2, "available_capital": 82000,
        "invested_capital": 18000, "open_trades": 2,
        "is_ready_for_real_trading": False
    }

    run_stock_dashboard(mock_signals, mock_portfolio, [])
