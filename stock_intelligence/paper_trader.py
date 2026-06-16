"""
stock_intelligence/paper_trader.py

Paper trading engine — tracks virtual trades to validate signals
BEFORE putting real money at risk.

Philosophy:
  Run paper trades for 90 days.
  If accuracy > 60% and avg return > 8%, graduate to real trading.
  If not, fix the signals first.

Uses Zerodha Kite API (paper mode) OR internal simulation.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

TRADES_FILE = "./data/paper_trades.json"


class PaperTrader:
    """
    Simulates trades based on stock signals.
    Tracks P&L, win rate, best/worst performers.
    No real money — just proof of concept.
    """

    def __init__(self, starting_capital: float = 100000):
        self.starting_capital = starting_capital
        self.data = self._load_trades()

    def _load_trades(self) -> Dict:
        os.makedirs("./data", exist_ok=True)
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE) as f:
                return json.load(f)
        return {
            "capital": self.starting_capital,
            "trades": [],
            "closed_trades": [],
            "created_at": datetime.now().isoformat()
        }

    def _save(self):
        with open(TRADES_FILE, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def enter_trade(self, signal: Dict, entry_price: float,
                    quantity: int = None) -> Dict:
        """Enter a paper trade based on a signal"""

        # Position sizing: stronger signal = more capital
        strength = signal.get("strength", 5)
        available = self._get_available_capital()
        max_position_pct = min(0.15, strength / 100)  # Max 15% per trade
        position_value = available * max_position_pct

        if entry_price <= 0:
            console.print(f"[yellow]⚠️ Invalid price for {signal['symbol']}[/yellow]")
            return {}

        qty = quantity or max(1, int(position_value / entry_price))
        trade_value = qty * entry_price

        if trade_value > available * 0.15:
            console.print(f"[yellow]⚠️ Position too large for {signal['symbol']}. Skipping.[/yellow]")
            return {}

        trade = {
            "id": f"PT_{len(self.data['trades']) + 1:04d}",
            "symbol": signal["symbol"],
            "company": signal.get("company_name", ""),
            "sector": signal.get("sector", ""),
            "signal_type": signal.get("signal_type", ""),
            "signal_strength": strength,
            "entry_price": entry_price,
            "quantity": qty,
            "investment": round(trade_value, 2),
            "entry_date": datetime.now().isoformat(),
            "target_price": round(entry_price * 1.15, 2),   # 15% target
            "stop_loss": round(entry_price * 0.93, 2),       # 7% stop loss
            "hold_days": signal.get("hold_days", 60),
            "exit_date_planned": (
                datetime.now() + timedelta(days=signal.get("hold_days", 60))
            ).strftime("%d-%m-%Y"),
            "status": "OPEN",
            "reasoning": signal.get("reasoning", ""),
            "tender_title": signal.get("tender_title", "")
        }

        self.data["trades"].append(trade)
        self.data["capital"] -= trade_value
        self._save()

        console.print(f"[green]📈 Paper trade entered: {trade['id']} | "
                      f"{signal['symbol']} | {qty} shares @ ₹{entry_price} | "
                      f"Investment: ₹{trade_value:,.0f}[/green]")
        return trade

    def close_trade(self, trade_id: str, exit_price: float,
                    reason: str = "Manual") -> Dict:
        """Close a paper trade and record P&L"""
        for trade in self.data["trades"]:
            if trade["id"] == trade_id:
                entry = trade["entry_price"]
                qty = trade["quantity"]
                pnl = (exit_price - entry) * qty
                pnl_pct = ((exit_price - entry) / entry) * 100
                trade_value = exit_price * qty

                closed = {
                    **trade,
                    "exit_price": exit_price,
                    "exit_date": datetime.now().isoformat(),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "exit_reason": reason,
                    "status": "CLOSED",
                    "outcome": "WIN" if pnl > 0 else "LOSS"
                }

                self.data["closed_trades"].append(closed)
                self.data["trades"].remove(trade)
                self.data["capital"] += trade_value
                self._save()

                emoji = "✅" if pnl > 0 else "❌"
                console.print(
                    f"{emoji} Trade closed: {trade_id} | {trade['symbol']} | "
                    f"P&L: ₹{pnl:+,.0f} ({pnl_pct:+.1f}%)"
                )
                return closed

        console.print(f"[yellow]Trade {trade_id} not found[/yellow]")
        return {}

    def auto_close_expired(self, current_prices: Dict[str, float]):
        """Auto-close trades that hit target, stop loss, or time limit"""
        closed = []
        for trade in list(self.data["trades"]):
            symbol = trade["symbol"]
            price = current_prices.get(symbol, trade["entry_price"])

            reason = None
            if price >= trade["target_price"]:
                reason = "TARGET_HIT"
            elif price <= trade["stop_loss"]:
                reason = "STOP_LOSS"
            else:
                planned_exit = datetime.strptime(
                    trade["exit_date_planned"], "%d-%m-%Y"
                )
                if datetime.now() >= planned_exit:
                    reason = "TIME_EXPIRED"

            if reason:
                result = self.close_trade(trade["id"], price, reason)
                closed.append(result)

        return closed

    def _get_available_capital(self) -> float:
        return self.data.get("capital", self.starting_capital)

    def get_portfolio_summary(self) -> Dict:
        """Calculate current portfolio metrics"""
        closed = self.data["closed_trades"]
        open_trades = self.data["trades"]

        if not closed:
            return {
                "total_trades": 0,
                "open_trades": len(open_trades),
                "win_rate": 0,
                "total_pnl": 0,
                "avg_return_pct": 0,
                "best_trade": None,
                "worst_trade": None,
                "available_capital": self._get_available_capital(),
                "invested_capital": sum(t["investment"] for t in open_trades)
            }

        wins = [t for t in closed if t["outcome"] == "WIN"]
        total_pnl = sum(t["pnl"] for t in closed)
        avg_return = sum(t["pnl_pct"] for t in closed) / len(closed)
        best = max(closed, key=lambda x: x["pnl_pct"])
        worst = min(closed, key=lambda x: x["pnl_pct"])

        return {
            "total_trades": len(closed),
            "open_trades": len(open_trades),
            "wins": len(wins),
            "losses": len(closed) - len(wins),
            "win_rate": round(len(wins) / len(closed) * 100, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_return_pct": round(avg_return, 2),
            "best_trade": {
                "symbol": best["symbol"],
                "pnl_pct": best["pnl_pct"],
                "reasoning": best.get("reasoning", "")[:60]
            },
            "worst_trade": {
                "symbol": worst["symbol"],
                "pnl_pct": worst["pnl_pct"],
                "reasoning": worst.get("reasoning", "")[:60]
            },
            "available_capital": round(self._get_available_capital(), 2),
            "invested_capital": round(sum(t["investment"] for t in open_trades), 2),
            "total_portfolio_value": round(
                self._get_available_capital() +
                sum(t["investment"] for t in open_trades), 2
            ),
            "is_ready_for_real_trading": (
                len(closed) >= 10 and
                len(wins) / len(closed) > 0.6 and
                avg_return > 8
            )
        }


class TradingSignalExecutor:
    """
    Takes signals from SignalDetector and executes paper trades.
    Uses mock prices from Phase 3 stock monitor.
    """

    def __init__(self):
        self.trader = PaperTrader(starting_capital=100000)

    def execute_signals(self, signals: List[Dict],
                        price_data: List[Dict]) -> List[Dict]:
        """Execute top signals as paper trades"""
        price_map = {
            p["symbol"]: p.get("ltp", 0)
            for p in price_data
        }

        executed = []
        console.print(f"\n[bold cyan]⚡ Executing paper trades for top signals...[/bold cyan]")

        # Only trade BUY signals with strength >= 6
        buy_signals = [
            s for s in signals
            if s.get("strength", 0) >= 6 and "BUY" in s.get("action", "")
        ][:5]  # Max 5 trades

        for signal in buy_signals:
            symbol = signal["symbol"]
            price = price_map.get(symbol, 0)

            if price <= 0:
                # Use mock price from signal_detector's price map
                mock_prices = {
                    "ADANIGREEN": 1850, "ADANIPORTS": 1285, "TATAPOWER": 425,
                    "NTPC": 385, "POWERGRID": 315, "IRB": 72, "KNRCON": 315,
                    "NCC": 230, "GMRINFRA": 92, "JSWINFRA": 285,
                    "WAAREEENER": 2850, "POLYCAB": 5200, "KEI": 3100,
                    "ULTRACEMCO": 10200, "LT": 3720, "BHEL": 285,
                    "CONCOR": 775, "DELHIVERY": 385, "SIEMENS": 5400,
                }
                price = mock_prices.get(symbol, 500)

            trade = self.trader.enter_trade(signal, price)
            if trade:
                executed.append(trade)

        return executed

    def get_portfolio(self) -> Dict:
        return self.trader.get_portfolio_summary()

    def get_open_trades(self) -> List[Dict]:
        return self.trader.data.get("trades", [])


def run_paper_trading(signals: List[Dict], price_data: List[Dict]) -> Dict:
    """Full paper trading pipeline"""
    console.print("\n[bold magenta]📊 Starting Paper Trading Engine...[/bold magenta]")

    executor = TradingSignalExecutor()
    executed_trades = executor.execute_signals(signals, price_data)
    portfolio = executor.get_portfolio()

    console.print(f"\n[bold]💼 Portfolio Status:[/bold]")
    console.print(f"  Available capital: ₹{portfolio.get('available_capital', 0):,.0f}")
    console.print(f"  Invested capital:  ₹{portfolio.get('invested_capital', 0):,.0f}")
    console.print(f"  Open trades: {portfolio.get('open_trades', 0)}")

    if portfolio.get("total_trades", 0) > 0:
        console.print(f"  Win rate: {portfolio.get('win_rate', 0)}%")
        console.print(f"  Avg return: {portfolio.get('avg_return_pct', 0)}%")
        console.print(f"  Total P&L: ₹{portfolio.get('total_pnl', 0):+,.0f}")

        ready = portfolio.get("is_ready_for_real_trading", False)
        if ready:
            console.print("[bold green]🎯 READY FOR REAL TRADING![/bold green]")
        else:
            trades_needed = max(0, 10 - portfolio.get("total_trades", 0))
            console.print(f"[yellow]📈 {trades_needed} more closed trades needed to validate[/yellow]")

    return {
        "executed_trades": executed_trades,
        "portfolio": portfolio
    }


if __name__ == "__main__":
    mock_signals = [
        {
            "symbol": "ADANIGREEN",
            "company_name": "Adani Green Energy",
            "sector": "solar",
            "signal_type": "DIRECT",
            "strength": 9.0,
            "action": "🟢 STRONG BUY",
            "reasoning": "500MW solar tender direct beneficiary",
            "tender_title": "500MW Solar Power Plant",
            "hold_days": 60
        },
        {
            "symbol": "NTPC",
            "company_name": "NTPC",
            "sector": "power",
            "signal_type": "DIRECT",
            "strength": 7.5,
            "action": "🟢 BUY",
            "reasoning": "Power sector tender",
            "tender_title": "Power Plant Construction",
            "hold_days": 45
        }
    ]

    result = run_paper_trading(mock_signals, [])
    print(f"\nExecuted {len(result['executed_trades'])} trades")
    print(json.dumps(result["portfolio"], indent=2))
