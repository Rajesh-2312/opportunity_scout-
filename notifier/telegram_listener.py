"""
notifier/telegram_listener.py

Interactive Telegram command bot. Long-polls getUpdates and answers
slash-commands so you can pull updates on demand from your phone:

  /start  /help          → show this menu
  /latest                → latest top opportunities (tenders)
  /insights              → sector intelligence summary
  /invest                → stock recommendations (target % + horizon)
  /positions             → invested stocks with live P/L
  /monitor               → check positions now (SELL/PROFIT alerts)
  /scan                  → run a fresh opportunity scan (takes a few min)

Run:  python main.py --listen
Needs network access to Telegram (VPN/hotspot/proxy if your ISP blocks it).
Honors TELEGRAM_PROXY from .env.
"""

import os
import glob
import json
import time
import threading
import requests
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

API = "https://api.telegram.org"
COMMANDS = [
    ("start", "Show the command menu"),
    ("help", "Show the command menu"),
    ("latest", "Latest top opportunities"),
    ("insights", "Sector intelligence summary"),
    ("invest", "Stock recommendations (target % + horizon)"),
    ("positions", "Invested stocks with live P/L"),
    ("monitor", "Check positions now (sell/profit alerts)"),
    ("scan", "Run a fresh opportunity scan"),
]


class TelegramListener:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.proxy = os.getenv("TELEGRAM_PROXY", "").strip() or None
        self.proxies = {"https": self.proxy, "http": self.proxy} if self.proxy else None
        self.enabled = bool(self.token and self.token != "your_telegram_bot_token_here")
        self.offset = 0
        self._scanning = False

    # ── low-level API (aiohttp: works under WARP; requests hit WinError 10013) ──
    async def _api_async(self, method: str, timeout_total: int = 45, **params):
        import aiohttp, socket
        from notifier.telegram_bot import _telegram_ips, _PinnedResolver, _TELEGRAM_HOST
        url = f"{API}/bot{self.token}/{method}"
        strategies = ["normal"] + ([] if self.proxy else await _telegram_ips())
        last_err = None
        for strat in strategies:
            try:
                timeout = aiohttp.ClientTimeout(total=timeout_total)
                if self.proxy or strat == "normal":
                    connector = aiohttp.TCPConnector()
                else:
                    connector = aiohttp.TCPConnector(
                        resolver=_PinnedResolver(_TELEGRAM_HOST, strat), family=socket.AF_INET)
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as s:
                    async with s.post(url, json=params, proxy=self.proxy) as r:
                        return await r.json(content_type=None)
            except Exception as e:
                last_err = e
                continue
        if method != "getUpdates":
            console.print(f"[red]Telegram API error ({method}): {last_err}[/red]")
        return {}

    def _api(self, method: str, **params):
        import asyncio
        tt = 45 if method != "getUpdates" else int(params.get("timeout", 0)) + 15
        return asyncio.run(self._api_async(method, timeout_total=tt, **params))

    def send(self, text: str, chat_id=None):
        self._api("sendMessage", chat_id=chat_id or self.chat_id,
                  text=text[:4096], parse_mode="HTML", disable_web_page_preview=True)

    def register_menu(self):
        cmds = [{"command": c, "description": d} for c, d in COMMANDS]
        self._api("setMyCommands", commands=cmds)

    # ── subscriber authorization ─────────────────────────
    SUBSCRIBER_DB = "./data/subscribers.json"

    def _is_subscriber(self, chat_id) -> bool:
        """
        Returns True if chat_id belongs to an active paying subscriber.
        Matches against telegram_id field (stored as string or int).
        Owner's personal chat_id always passes (so you can test commands yourself).
        """
        if str(chat_id) == str(self.chat_id):
            return True  # owner always authorized
        try:
            with open(self.SUBSCRIBER_DB, encoding="utf-8") as f:
                data = json.load(f)
            for sub in data.get("subscribers", []):
                if sub.get("status") != "active":
                    continue
                tid = str(sub.get("telegram_id", "")).strip().lstrip("@")
                cid = str(chat_id).strip().lstrip("@")
                if tid and tid == cid:
                    return True
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return False

    def _send_paywall(self, chat_id):
        razorpay = os.getenv("RAZORPAY_PAYMENT_LINK", "https://razorpay.me/@marojurajesh")
        channel = os.getenv("TELEGRAM_CHANNEL_ID", "@opportunity_scout")
        self.send(
            f"🔒 <b>Premium subscribers only</b>\n\n"
            f"This command is available to active subscribers of <b>India Infra Intelligence</b>.\n\n"
            f"💼 <b>Subscribe now — ₹299/month</b>\n"
            f"👉 {razorpay}\n\n"
            f"📡 Free daily alerts: {channel}\n"
            f"Questions? Message @marojurajesh directly.",
            chat_id
        )

    # ── data helpers ─────────────────────────────────────
    @staticmethod
    def _latest_pipeline() -> dict:
        files = sorted(glob.glob("./data/pipeline_results_*.json"), reverse=True)
        for f in files:
            try:
                return json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
        return {}

    # ── command handlers ─────────────────────────────────
    # Commands that anyone can run (free / public)
    FREE_COMMANDS = {"start", "help", ""}

    def handle(self, text: str, chat_id):
        cmd = text.strip().lower().lstrip("/").split("@")[0].split()[0] if text.strip() else ""

        # Free commands — no auth check
        if cmd in self.FREE_COMMANDS:
            self.send(self._menu(), chat_id)
            return

        # All other commands require an active subscription
        if not self._is_subscriber(chat_id):
            console.print(f"[yellow]⛔ Blocked non-subscriber {chat_id} from /{cmd}[/yellow]")
            self._send_paywall(chat_id)
            return

        # Authorized — run the command
        if cmd in ("latest", "opportunities"):
            self.send(self._latest_opps(), chat_id)
        elif cmd == "insights":
            self.send(self._insights(), chat_id)
        elif cmd == "invest":
            self.send(self._invest(), chat_id)
        elif cmd in ("positions", "portfolio"):
            self.send(self._positions(), chat_id)
        elif cmd == "monitor":
            self.send("🔄 Checking live prices…", chat_id)
            self._run_monitor(chat_id)
        elif cmd == "scan":
            self._run_scan(chat_id)
        else:
            self.send(f"❓ Unknown command: /{cmd}\n\n{self._menu()}", chat_id)

    def _menu(self) -> str:
        lines = ["🤖 <b>Opportunity Scout — Commands</b>\n"]
        for c, d in COMMANDS:
            if c == "help":
                continue
            lines.append(f"/{c} — {d}")
        return "\n".join(lines)

    def _latest_opps(self) -> str:
        rep = self._latest_pipeline()
        opps = rep.get("top_opportunities", [])
        if not opps:
            return "No opportunities yet. Try /scan."
        out = ["🏆 <b>TOP OPPORTUNITIES</b>\n"]
        for i, o in enumerate(opps[:5], 1):
            s = o.get("total_score", 0)
            emoji = "🔥" if s >= 8 else "⭐" if s >= 6 else "📌"
            out.append(f"{emoji} <b>{i}. {o.get('title','')[:90]}</b>\n"
                       f"   💰 {o.get('value','TBD')} | 📍 {o.get('location','N/A')} | ⏰ {o.get('deadline','N/A')}")
        return "\n\n".join(out)

    def _insights(self) -> str:
        rep = self._latest_pipeline()
        ins = rep.get("sector_insights", "")
        return ("📊 <b>SECTOR INTELLIGENCE</b>\n\n" + ins[:3500]) if ins else "No insights yet. Try /scan."

    def _invest(self) -> str:
        try:
            from stock_intelligence.investment_advisor import InvestmentAdvisor
            adv = InvestmentAdvisor()
            pos = adv._load()
            if not pos:
                return "No stock recommendations yet. Generating… run /scan or use the dashboard 'Recommend stocks'."
            return adv.format_recommendations(pos[:6])
        except Exception as e:
            return f"Invest data error: {e}"

    def _positions(self) -> str:
        try:
            from stock_intelligence.investment_advisor import InvestmentAdvisor
            pos = InvestmentAdvisor().live_status()
            if not pos:
                return "No tracked positions. Use /invest first."
            out = ["💼 <b>INVESTED STOCKS — LIVE P/L</b>\n"]
            for p in pos:
                pl = p.get("pl_pct")
                arrow = "🟢" if (pl or 0) >= 0 else "🔴"
                out.append(f"{arrow} <b>{p['symbol'].replace('.NS','')}</b> ₹{p.get('current_price','?')} "
                           f"| P/L {pl}% | 🎯+{p['target_profit_pct']}% | {p['horizon']} | {p.get('status','ACTIVE')}")
            return "\n".join(out)
        except Exception as e:
            return f"Positions error: {e}"

    def _run_monitor(self, chat_id):
        try:
            from stock_intelligence.investment_advisor import InvestmentAdvisor
            r = InvestmentAdvisor().monitor_and_alert()
            self.send(f"✅ Checked {r['checked']} positions — "
                      f"{len(r['sell_alerts'])} sell, {len(r['profit_alerts'])} profit alerts.", chat_id)
        except Exception as e:
            self.send(f"Monitor error: {e}", chat_id)

    def _run_scan(self, chat_id):
        if self._scanning:
            self.send("⏳ A scan is already running…", chat_id)
            return
        self.send("🚀 Starting a fresh scan — I'll send results when ready (a few minutes)…", chat_id)

        def _bg():
            self._scanning = True
            try:
                from scrapers.tender_scraper import run_all_scrapers
                from memory.vector_store import OpportunityMemory
                from agents.scout_agent import run_scout_agent
                cfg = {"target_sectors": ["infrastructure", "energy", "ports", "logistics", "airports"],
                       "target_states": ["Telangana", "Andhra Pradesh"]}
                scraped = run_all_scrapers(cfg)
                OpportunityMemory("./data/chroma_db").store_bulk(scraped)
                run_scout_agent(scraped)
                self.send("✅ Scan complete! Use /latest to see the top opportunities.", chat_id)
            except Exception as e:
                self.send(f"Scan failed: {e}", chat_id)
            finally:
                self._scanning = False

        threading.Thread(target=_bg, daemon=True).start()

    # ── connectivity preflight ───────────────────────────
    def _can_reach_telegram(self) -> bool:
        try:
            return bool(self._api("getMe").get("ok"))
        except Exception:
            return False

    # ── main poll loop ───────────────────────────────────
    def run(self):
        if not self.enabled:
            console.print("[red]Telegram not configured (TELEGRAM_BOT_TOKEN missing).[/red]")
            return

        if not self._can_reach_telegram():
            console.print(
                "\n[bold red]❌ Cannot reach Telegram — the connection is being blocked.[/bold red]\n"
                "[yellow]Your ISP is blocking api.telegram.org at the network level.[/yellow]\n\n"
                "[bold]Fix it with ONE of these, then re-run [cyan]python main.py --listen[/cyan]:[/bold]\n"
                "  1. Turn on a VPN — install the free [cyan]1.1.1.1 (Cloudflare WARP)[/cyan] app and toggle it ON\n"
                "  2. Connect this PC to your phone's mobile [cyan]hotspot[/cyan]\n"
                "  3. Set [cyan]TELEGRAM_PROXY=http://host:port[/cyan] in your .env file\n"
            )
            return

        self.register_menu()
        console.print("[bold green]📡 Telegram command bot is listening. Send /start in your chat.[/bold green]")
        console.print("[dim]Press Ctrl+C to stop.[/dim]")
        while True:
            try:
                resp = self._api("getUpdates", offset=self.offset, timeout=0)
                for upd in resp.get("result", []):
                    self.offset = upd["update_id"] + 1
                    msg = upd.get("message") or upd.get("edited_message") or {}
                    text = msg.get("text", "")
                    chat_id = (msg.get("chat") or {}).get("id")
                    if text and chat_id:
                        console.print(f"[cyan]← {text}[/cyan] from {chat_id}")
                        self.handle(text, chat_id)
                time.sleep(2)  # short-poll; keeps connections short-lived (WARP-safe)
            except KeyboardInterrupt:
                console.print("\n[yellow]Listener stopped.[/yellow]")
                break
            except Exception as e:
                console.print(f"[yellow]Poll error (retrying): {e}[/yellow]")
                time.sleep(5)


def run_listener():
    TelegramListener().run()


if __name__ == "__main__":
    run_listener()
