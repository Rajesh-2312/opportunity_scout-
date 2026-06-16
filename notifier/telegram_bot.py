"""
notifier/telegram_bot.py
Sends daily opportunity digest via Telegram
Setup: Create bot via @BotFather, get chat ID from @userinfobot
"""

import os
import socket
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

# ── ISP-block bypass ──────────────────────────────────────
# Some ISPs (notably in India) DNS-hijack api.telegram.org to a dead IP.
# We resolve the REAL IP via DoH (Cloudflare 1.1.1.1, an IP so it can't be
# hijacked) and pin it, keeping TLS SNI = api.telegram.org. Falls back to
# known Telegram IPs if DoH is unavailable.
_TELEGRAM_HOST = "api.telegram.org"
_FALLBACK_IPS = ["149.154.167.220", "149.154.167.222", "149.154.166.110"]
_cached_ips: Optional[list] = None


async def _doh_resolve(host: str) -> Optional[str]:
    """Resolve A record via Cloudflare DNS-over-HTTPS (bypasses ISP DNS)."""
    try:
        import aiohttp
        url = f"https://1.1.1.1/dns-query?name={host}&type=A"
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url, headers={"accept": "application/dns-json"}) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    ips = [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
                    return ips[0] if ips else None
    except Exception:
        return None
    return None


async def _telegram_ips() -> list:
    global _cached_ips
    if _cached_ips:
        return _cached_ips
    ip = await _doh_resolve(_TELEGRAM_HOST)
    cands = ([ip] if ip else []) + _FALLBACK_IPS
    # de-dup preserving order
    _cached_ips = list(dict.fromkeys(cands))
    return _cached_ips


class _PinnedResolver:
    """aiohttp resolver that forces api.telegram.org to a known-good IP."""
    def __init__(self, host: str, ip: str):
        self._host, self._ip = host, ip

    async def resolve(self, host, port=0, family=socket.AF_INET):
        if host == self._host:
            return [{"hostname": host, "host": self._ip, "port": port,
                     "family": socket.AF_INET, "proto": socket.IPPROTO_TCP, "flags": 0}]
        import aiohttp
        return await aiohttp.ThreadedResolver().resolve(host, port, family)

    async def close(self):
        pass


class TelegramNotifier:
    """
    Sends formatted opportunity alerts to Telegram
    FREE - no cost, instant delivery to your phone
    """

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.token != "your_telegram_bot_token_here")

        if not self.enabled:
            console.print("[yellow]⚠️ Telegram not configured. Reports will be saved to file only.[/yellow]")

    async def send_message(self, text: str, parse_mode: str = "HTML", retries: int = 3) -> bool:
        """Send message to Telegram with retry on transient network failures"""
        if not self.enabled:
            console.print("[yellow]📱 [Telegram disabled] Would have sent message[/yellow]")
            return False

        import aiohttp
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text[:4096],  # Telegram limit
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        ips = await _telegram_ips()
        for attempt in range(1, retries + 1):
            ip = ips[(attempt - 1) % len(ips)]  # rotate IP each retry
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                connector = aiohttp.TCPConnector(
                    resolver=_PinnedResolver(_TELEGRAM_HOST, ip),
                    family=socket.AF_INET,  # avoid hijacked IPv6
                )
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            console.print("[green]✅ Telegram message sent![/green]")
                            return True
                        else:
                            error = await response.text()
                            # 4xx (bad token/chat) won't fix on retry — bail out
                            if 400 <= response.status < 500:
                                console.print(f"[red]❌ Telegram error {response.status}: {error}[/red]")
                                return False
                            console.print(f"[yellow]⚠️ Telegram {response.status} (attempt {attempt}/{retries})[/yellow]")

            except Exception as e:
                console.print(f"[yellow]⚠️ Telegram connect failed (attempt {attempt}/{retries}): {e}[/yellow]")

            if attempt < retries:
                await asyncio.sleep(2 * attempt)  # backoff: 2s, 4s

        console.print("[red]❌ Telegram send failed after retries[/red]")
        return False

    def format_opportunity_alert(self, opportunity: Dict) -> str:
        """Format a single opportunity as Telegram HTML"""
        analysis = opportunity.get("ai_analysis", {})
        score = opportunity.get("total_score", 0)

        # Score emoji
        if score >= 8:
            score_emoji = "🔥"
        elif score >= 6:
            score_emoji = "⭐"
        else:
            score_emoji = "📌"

        return f"""
{score_emoji} <b>{opportunity.get('title', 'Unknown')[:100]}</b>

💰 <b>Value:</b> {opportunity.get('value', 'TBD')}
🏛️ <b>Dept:</b> {opportunity.get('department', 'N/A')}
📍 <b>Location:</b> {opportunity.get('location', 'N/A')}
⏰ <b>Deadline:</b> {opportunity.get('deadline', 'N/A')}
⭐ <b>AI Score:</b> {score}/10
🏷️ <b>Sector:</b> {opportunity.get('sector', 'N/A')}

💡 <i>{analysis.get('key_insight', 'Strong opportunity')}</i>

✅ <b>Action:</b> {analysis.get('action_required', 'Review bid requirements')}
🔗 <a href="{opportunity.get('url', '#')}">View Full Tender</a>
""".strip()

    def format_daily_digest(self, top_opportunities: List[Dict], sector_insights: str) -> List[str]:
        """Format complete daily digest as multiple messages (Telegram 4096 char limit)"""
        today = datetime.now().strftime("%d %B %Y, %I:%M %p")
        messages = []

        # Header message
        header = f"""🎯 <b>OPPORTUNITY SCOUT DAILY DIGEST</b>
📅 {today}

📊 <b>SECTOR PULSE:</b>
{sector_insights[:800]}

━━━━━━━━━━━━━━━━━━━━━━
🏆 <b>TOP {len(top_opportunities)} OPPORTUNITIES TODAY</b>
━━━━━━━━━━━━━━━━━━━━━━"""
        messages.append(header)

        # Individual opportunity messages
        for i, opp in enumerate(top_opportunities, 1):
            opp_msg = f"<b>#{i} of {len(top_opportunities)}</b>\n\n" + self.format_opportunity_alert(opp)
            messages.append(opp_msg)

        # Footer
        footer = """━━━━━━━━━━━━━━━━━━━━━━
🤖 <i>Powered by Opportunity Scout AI</i>
💼 <i>Build. Learn. Profit.</i>
━━━━━━━━━━━━━━━━━━━━━━"""
        messages.append(footer)

        return messages

    async def send_daily_digest(self, top_opportunities: List[Dict], sector_insights: str) -> bool:
        """Send complete daily digest"""
        messages = self.format_daily_digest(top_opportunities, sector_insights)

        success = True
        for msg in messages:
            result = await self.send_message(msg)
            if not result and self.enabled:
                success = False
            await asyncio.sleep(0.5)  # Rate limit

        return success

    async def send_urgent_alert(self, opportunity: Dict) -> bool:
        """Send urgent alert for high-score opportunity"""
        alert = f"""🚨 <b>HIGH PRIORITY ALERT</b> 🚨

{self.format_opportunity_alert(opportunity)}

⚡ <b>ACT NOW</b> - This opportunity closes soon!"""

        return await self.send_message(alert)

    def send_digest_sync(self, top_opportunities: List[Dict], sector_insights: str) -> bool:
        """Synchronous wrapper for sending digest"""
        return asyncio.run(self.send_daily_digest(top_opportunities, sector_insights))

    def test_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.enabled:
            console.print("[yellow]Telegram not configured. Skipping test.[/yellow]")
            return False

        async def _test():
            return await self.send_message("🤖 Opportunity Scout Agent is online and monitoring!")

        return asyncio.run(_test())


class FileNotifier:
    """
    Backup notifier - saves reports to file when Telegram isn't configured
    """

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        import os
        os.makedirs(output_dir, exist_ok=True)

    def save_report(self, report: str) -> str:
        """Save report to timestamped file"""
        filename = f"{self.output_dir}/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        console.print(f"[green]💾 Report saved: {filename}[/green]")
        return filename

    def save_json_report(self, data: Dict, name: str = "opportunities") -> str:
        """Save structured data as JSON"""
        import json
        filename = f"{self.output_dir}/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        console.print(f"[green]💾 JSON saved: {filename}[/green]")
        return filename


if __name__ == "__main__":
    # Test notifier
    notifier = TelegramNotifier()
    notifier.test_connection()

    # Test file notifier
    file_notifier = FileNotifier()
    file_notifier.save_report("Test report content")
