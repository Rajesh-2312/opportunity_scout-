
"""
stock_intelligence/investment_advisor.py

"Stocks to Invest for Profit" engine.
 - Recommends Indian (NSE) stocks to buy, with an approximate target profit %
   and a holding horizon between 1 month and 3 years.
 - Tracks the recommended positions and monitors them with LIVE prices.
 - If a position falls to its stop-loss (a loss), it raises an IMMEDIATE
   "SELL OFF" alert on Telegram. If it hits target, it sends a book-profit alert.

Heuristic, transparent signals (momentum + trend + volatility) from yfinance.
NOT SEBI-registered financial advice — educational/automation use only.
"""

import os
import json
import warnings
from datetime import datetime
from typing import List, Dict, Optional

import yfinance as yf
from rich.console import Console

warnings.filterwarnings("ignore")
console = Console()

DISCLAIMER = "⚠️ Auto-generated signals, not financial advice. Do your own research."

# ── Curated NSE universe (infra / energy / capex theme — matches the project) ──
UNIVERSE: Dict[str, Dict] = {
    "NTPC.NS":       {"name": "NTPC",                 "sector": "Power"},
    "POWERGRID.NS":  {"name": "Power Grid Corp",      "sector": "Power Transmission"},
    "LT.NS":         {"name": "Larsen & Toubro",      "sector": "EPC/Engineering"},
    "ADANIPORTS.NS": {"name": "Adani Ports & SEZ",    "sector": "Ports"},
    "ADANIGREEN.NS": {"name": "Adani Green Energy",   "sector": "Renewable Energy"},
    "TATAPOWER.NS":  {"name": "Tata Power",           "sector": "Energy"},
    "NCC.NS":        {"name": "NCC Limited",          "sector": "Construction"},
    "KNRCON.NS":     {"name": "KNR Constructions",    "sector": "Roads/Irrigation"},
    "IRB.NS":        {"name": "IRB Infrastructure",   "sector": "Roads"},
    "JSWINFRA.NS":   {"name": "JSW Infrastructure",   "sector": "Ports/Logistics"},
    "RVNL.NS":       {"name": "Rail Vikas Nigam",     "sector": "Railways"},
    "IRFC.NS":       {"name": "Indian Railway Fin.",  "sector": "Railways Finance"},
    "NHPC.NS":       {"name": "NHPC",                 "sector": "Hydro Power"},
    "SJVN.NS":       {"name": "SJVN",                 "sector": "Hydro/Renewable"},
    "BHEL.NS":       {"name": "BHEL",                 "sector": "Power Equipment"},
    "COALINDIA.NS":  {"name": "Coal India",           "sector": "Energy/Mining"},
}

POSITIONS_FILE = "./data/investments.json"
DEFAULT_STOP_LOSS_PCT = -8.0   # exit if a position falls this much from entry


# ─────────────────────────────────────────────────────────
class InvestmentAdvisor:
    def __init__(self, positions_file: str = POSITIONS_FILE):
        self.positions_file = positions_file
        os.makedirs(os.path.dirname(positions_file) or ".", exist_ok=True)

    # ── price helpers ────────────────────────────────────
    @staticmethod
    def _history(symbol: str, period: str = "1y"):
        try:
            h = yf.Ticker(symbol).history(period=period)
            return h if not h.empty else None
        except Exception:
            return None

    @staticmethod
    def _pct(series, lookback: int) -> Optional[float]:
        if series is None or len(series) <= lookback:
            return None
        old = series.iloc[-lookback - 1]
        new = series.iloc[-1]
        if old <= 0:
            return None
        return (new / old - 1) * 100

    # ── core analysis: one stock -> a recommendation ─────
    def analyze(self, symbol: str) -> Optional[Dict]:
        h = self._history(symbol, "1y")
        if h is None or len(h) < 60:
            return None
        close = h["Close"]
        price = float(close.iloc[-1])

        ret_1m = self._pct(close, 21) or 0.0
        ret_6m = self._pct(close, 126) or 0.0
        ret_1y = self._pct(close, 251) or 0.0
        dma50 = float(close.tail(50).mean())
        dma200 = float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean())
        daily = close.pct_change().dropna()
        vol = float(daily.std() * (252 ** 0.5) * 100) if len(daily) else 25.0  # annualized %

        above50 = price > dma50
        above200 = price > dma200

        # Only recommend names in an uptrend / not falling hard
        if not (above200 or ret_6m > 0) or ret_6m < -15:
            return None

        # Decide horizon + approximate target profit %
        if above50 and above200 and ret_1m > 4:
            horizon, target = "1-3 months", min(max(8.0, ret_1m * 1.4), 22.0)
        elif above200 and ret_6m > 8:
            horizon, target = "6-12 months", min(max(15.0, ret_6m * 0.9), 40.0)
        else:
            horizon, target = "1-3 years", min(max(30.0, ret_1y * 1.1), 80.0)

        # stop-loss widens slightly for more volatile names
        stop_loss = round(min(DEFAULT_STOP_LOSS_PCT, -max(6.0, vol * 0.15)), 1)

        # composite quality/momentum score (for ranking)
        score = round(
            (ret_6m * 0.4) + (ret_1y * 0.2) + (15 if above200 else 0) +
            (10 if above50 else 0) - (vol * 0.1), 1
        )

        info = UNIVERSE.get(symbol, {})
        return {
            "symbol": symbol,
            "name": info.get("name", symbol),
            "sector": info.get("sector", ""),
            "entry_price": round(price, 2),
            "target_profit_pct": round(target, 1),
            "target_price": round(price * (1 + target / 100), 2),
            "stop_loss_pct": stop_loss,
            "stop_loss_price": round(price * (1 + stop_loss / 100), 2),
            "horizon": horizon,
            "momentum_1m_pct": round(ret_1m, 1),
            "momentum_6m_pct": round(ret_6m, 1),
            "momentum_1y_pct": round(ret_1y, 1),
            "volatility_pct": round(vol, 1),
            "score": score,
            "rationale": self._rationale(above50, above200, ret_6m, horizon),
        }

    @staticmethod
    def _rationale(above50, above200, ret_6m, horizon) -> str:
        bits = []
        if above200: bits.append("above 200-DMA (long-term uptrend)")
        if above50: bits.append("above 50-DMA (short-term strength)")
        if ret_6m > 0: bits.append(f"+{ret_6m:.0f}% in 6 months")
        bits.append(f"suited to a {horizon} hold")
        return ", ".join(bits).capitalize()

    # ── generate ranked recommendations & persist as positions ──
    def generate(self, top_n: int = 6) -> List[Dict]:
        console.print("[cyan]📊 Analyzing NSE universe for profit opportunities...[/cyan]")
        recs = []
        for sym in UNIVERSE:
            r = self.analyze(sym)
            if r:
                recs.append(r)
        recs.sort(key=lambda x: x["score"], reverse=True)
        top = recs[:top_n]

        # persist as active positions (keep ones still open from before)
        existing = self._load()
        open_syms = {p["symbol"] for p in existing if p.get("status") == "ACTIVE"}
        now = datetime.now().isoformat(timespec="seconds")
        for r in top:
            if r["symbol"] in open_syms:
                continue
            existing.append({
                **r,
                "status": "ACTIVE",
                "recommended_at": now,
                "alerted_loss": False,
                "alerted_profit": False,
            })
        self._save(existing)
        console.print(f"[green]✅ {len(top)} stocks recommended, tracking {len(existing)} positions[/green]")
        return top

    # ── live status (NO telegram, for dashboard) ─────────
    def live_status(self) -> List[Dict]:
        positions = self._load()
        out = []
        for p in positions:
            cur = self._last_price(p["symbol"])
            pl = round((cur / p["entry_price"] - 1) * 100, 2) if cur and p.get("entry_price") else None
            out.append({**p, "current_price": cur, "pl_pct": pl, "eval": self._eval(p, pl)})
        return out

    # ── monitor + ALERT (sends telegram on loss/target) ──
    def monitor_and_alert(self, notifier=None) -> Dict:
        from notifier.telegram_bot import TelegramNotifier
        import asyncio
        tg = notifier or TelegramNotifier()
        positions = self._load()
        sell_alerts, profit_alerts = [], []

        for p in positions:
            if p.get("status") != "ACTIVE":
                continue
            cur = self._last_price(p["symbol"])
            if not cur:
                continue
            pl = round((cur / p["entry_price"] - 1) * 100, 2)
            p["current_price"] = cur
            p["pl_pct"] = pl

            # LOSS -> immediate sell-off alert
            if pl <= p["stop_loss_pct"] and not p.get("alerted_loss"):
                msg = self._sell_msg(p, cur, pl)
                asyncio.run(tg.send_message(msg))
                p["alerted_loss"] = True
                p["status"] = "SELL_LOSS"
                sell_alerts.append(p)

            # TARGET hit -> book profit alert
            elif pl >= p["target_profit_pct"] and not p.get("alerted_profit"):
                msg = self._profit_msg(p, cur, pl)
                asyncio.run(tg.send_message(msg))
                p["alerted_profit"] = True
                p["status"] = "BOOK_PROFIT"
                profit_alerts.append(p)

        self._save(positions)
        return {"sell_alerts": sell_alerts, "profit_alerts": profit_alerts,
                "checked": sum(1 for p in positions)}

    # ── Telegram message formatting ──────────────────────
    @staticmethod
    def format_recommendations(recs: List[Dict]) -> str:
        today = datetime.now().strftime("%d %b %Y")
        lines = [f"💹 <b>STOCKS TO INVEST FOR PROFIT</b>\n📅 {today}\n",
                 "<i>Indian (NSE) infra/energy picks — target & horizon below</i>\n",
                 "━━━━━━━━━━━━━━━━━━━━"]
        for i, r in enumerate(recs, 1):
            lines.append(
                f"\n<b>{i}. {r['name']}</b> ({r['symbol'].replace('.NS','')})\n"
                f"🏷️ {r['sector']}\n"
                f"💰 Buy ~₹{r['entry_price']}\n"
                f"🎯 Target: <b>+{r['target_profit_pct']}%</b> → ₹{r['target_price']}\n"
                f"⏳ Horizon: <b>{r['horizon']}</b>\n"
                f"🛑 Stop-loss: {r['stop_loss_pct']}% (₹{r['stop_loss_price']})\n"
                f"📈 {r['rationale']}"
            )
        lines.append("\n━━━━━━━━━━━━━━━━━━━━")
        lines.append("🔔 You'll get an instant alert to SELL if any pick hits its stop-loss.")
        lines.append(DISCLAIMER)
        return "\n".join(lines)

    @staticmethod
    def _sell_msg(p, cur, pl) -> str:
        return (f"🚨🔻 <b>SELL ALERT — BOOK LOSS NOW</b>\n\n"
                f"<b>{p['name']}</b> ({p['symbol'].replace('.NS','')})\n"
                f"Bought ~₹{p['entry_price']} → now ₹{cur}\n"
                f"📉 P/L: <b>{pl}%</b> (stop-loss {p['stop_loss_pct']}%)\n\n"
                f"⚡ Recommend EXIT to limit further loss.\n{DISCLAIMER}")

    @staticmethod
    def _profit_msg(p, cur, pl) -> str:
        return (f"✅🎯 <b>TARGET HIT — BOOK PROFIT</b>\n\n"
                f"<b>{p['name']}</b> ({p['symbol'].replace('.NS','')})\n"
                f"Bought ~₹{p['entry_price']} → now ₹{cur}\n"
                f"📈 P/L: <b>+{pl}%</b> (target +{p['target_profit_pct']}%)\n"
                f"⏳ Horizon was {p['horizon']}\n\n"
                f"💰 Consider booking profit.\n{DISCLAIMER}")

    # ── internals ────────────────────────────────────────
    @staticmethod
    def _eval(p, pl) -> str:
        if pl is None: return "UNKNOWN"
        if pl <= p.get("stop_loss_pct", -8): return "LOSS_EXIT"
        if pl >= p.get("target_profit_pct", 100): return "TARGET_HIT"
        return "HOLD"

    def _last_price(self, symbol: str) -> Optional[float]:
        h = self._history(symbol, "5d")
        if h is None or h.empty:
            return None
        return round(float(h["Close"].iloc[-1]), 2)

    def _load(self) -> List[Dict]:
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self, positions: List[Dict]):
        with open(self.positions_file, "w", encoding="utf-8") as f:
            json.dump(positions, f, indent=2, ensure_ascii=False)


# ── convenience entry points ─────────────────────────────
def run_investment_recommendations(top_n: int = 6, send_telegram: bool = True) -> List[Dict]:
    import asyncio
    from notifier.telegram_bot import TelegramNotifier
    adv = InvestmentAdvisor()
    recs = adv.generate(top_n)
    if send_telegram and recs:
        tg = TelegramNotifier()
        asyncio.run(tg.send_message(adv.format_recommendations(recs)))
    return recs


def run_investment_monitor() -> Dict:
    adv = InvestmentAdvisor()
    result = adv.monitor_and_alert()
    console.print(f"[green]Monitored {result['checked']} positions — "
                  f"{len(result['sell_alerts'])} sell, {len(result['profit_alerts'])} profit alerts[/green]")
    return result


if __name__ == "__main__":
    run_investment_recommendations(6, send_telegram=False)
