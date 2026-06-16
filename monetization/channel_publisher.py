"""
monetization/channel_publisher.py

Auto-publishes daily opportunity intel to a public Telegram channel.
Free tier: 1 opportunity (teaser)
Paid tier: All 5 + full AI analysis (subscribers only)

Setup:
  1. Create a PUBLIC Telegram channel (e.g. @IndiaInfraScout)
  2. Add your bot as admin to the channel
  3. Set TELEGRAM_CHANNEL_ID in .env (e.g. @IndiaInfraScout or -100xxxxxxxxx)
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict
import aiohttp
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()


class ChannelPublisher:
    """
    Publishes intel to public Telegram channel.
    Drives organic growth → paid subscribers.
    """

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "")  # e.g. @IndiaInfraScout
        self.private_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.razorpay_link = os.getenv("RAZORPAY_PAYMENT_LINK", "https://razorpay.me/your-link")
        self.enabled = bool(self.token and self.channel_id and
                           self.token != "your_telegram_bot_token_here")

        if not self.enabled:
            console.print("[yellow]⚠️  Channel publisher not configured. Will simulate output.[/yellow]")

    async def _send(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """Core send method"""
        if not self.enabled:
            console.print(f"\n[dim]── SIMULATED CHANNEL POST ──[/dim]")
            console.print(text[:600])
            console.print("[dim]── END SIMULATED POST ──[/dim]\n")
            return True

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text[:4096],
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    return resp.status == 200
        except Exception as e:
            console.print(f"[red]Send error: {e}[/red]")
            return False

    def _format_free_teaser(self, top_opportunity: Dict, total_count: int,
                             sector_headline: str) -> str:
        """
        Free public post — one opportunity + strong CTA to subscribe.
        Goal: curiosity + FOMO → paid conversion.
        """
        opp = top_opportunity
        analysis = opp.get("ai_analysis", {})
        score = opp.get("total_score", 0)
        today = datetime.now().strftime("%d %b %Y")

        score_bar = "🟢" * int(score) + "⬜" * (10 - int(score))

        return f"""📡 <b>INDIA INFRA INTELLIGENCE</b> | {today}

🏆 <b>TODAY'S #1 OPPORTUNITY</b>

<b>{opp.get('title', 'N/A')[:90]}</b>

💰 <b>Value:</b> {opp.get('value', 'TBD')}
🏛️ <b>Dept:</b> {opp.get('department', 'N/A')[:50]}
📍 <b>Location:</b> {opp.get('location', 'N/A')}
⏰ <b>Deadline:</b> {opp.get('deadline', 'N/A')}
🏷️ <b>Sector:</b> {opp.get('sector', 'N/A')}

⭐ <b>AI Score:</b> {score}/10  {score_bar}

💡 <i>"{analysis.get('key_insight', 'High strategic value opportunity')}"</i>

━━━━━━━━━━━━━━━━━━━━━━
🔒 <b>+{total_count - 1} MORE opportunities</b> analyzed today — including:
  • Full AI scoring breakdown
  • Exact action steps to bid
  • Sector momentum signals
  • Early warning on upcoming tenders

💼 <b>Unlock Premium — ₹299/month</b>
👇 Subscribe now:
{self.razorpay_link}

━━━━━━━━━━━━━━━━━━━━━━
🤖 <i>Powered by Opportunity Scout AI</i>
📢 Share this channel → @IndiaInfraScout"""

    def _format_premium_post(self, top_opportunities: List[Dict],
                              sector_insights: str) -> str:
        """
        Full premium digest — sent to paid subscribers' private group.
        """
        today = datetime.now().strftime("%d %B %Y, %I:%M %p")

        lines = [
            f"💎 <b>PREMIUM INTELLIGENCE DIGEST</b>",
            f"📅 {today}",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"📊 <b>SECTOR PULSE (AI Analysis)</b>",
            f"",
            sector_insights[:600],
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"🏆 <b>ALL {len(top_opportunities)} OPPORTUNITIES — FULL ANALYSIS</b>",
            f"━━━━━━━━━━━━━━━━━━━━━━",
        ]

        for i, opp in enumerate(top_opportunities, 1):
            analysis = opp.get("ai_analysis", {})
            score = opp.get("total_score", 0)

            lines += [
                f"",
                f"{'🔥' if score >= 8 else '⭐'} <b>#{i} — {opp.get('title', '')[:70]}</b>",
                f"",
                f"💰 {opp.get('value', 'TBD')}  |  📍 {opp.get('location', 'N/A')}",
                f"🏛️ {opp.get('department', 'N/A')[:50]}",
                f"⏰ Deadline: {opp.get('deadline', 'N/A')}",
                f"⭐ Score: {score}/10",
                f"",
                f"🧠 <b>Strategic Score:</b> {analysis.get('strategic_score', 'N/A')}/10",
                f"💵 <b>Revenue Potential:</b> {analysis.get('revenue_score', 'N/A')}/10",
                f"🏁 <b>Competition Level:</b> {analysis.get('competition_score', 'N/A')}/10",
                f"",
                f"💡 {analysis.get('key_insight', 'Strong opportunity')}",
                f"✅ <b>Action:</b> {analysis.get('action_required', 'Review and prepare')}",
                f"🔗 <a href=\"{opp.get('url', '#')}\">View Tender →</a>",
            ]

        lines += [
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"💎 <i>Premium Intelligence by Opportunity Scout AI</i>",
            f"📩 Questions? Reply to this message.",
        ]

        return "\n".join(lines)

    async def publish_daily(self, top_opportunities: List[Dict],
                            sector_insights: str) -> Dict:
        """
        Main publish method.
        1. Post teaser to public channel
        2. Post full report to premium/private chat
        """
        results = {"public_post": False, "premium_post": False}

        if not top_opportunities:
            console.print("[yellow]No opportunities to publish.[/yellow]")
            return results

        console.print("[bold cyan]📢 Publishing to channel...[/bold cyan]")

        # ── Public teaser post ──────────────────────────
        teaser = self._format_free_teaser(
            top_opportunities[0],
            len(top_opportunities),
            sector_insights[:200]
        )

        target = self.channel_id if self.channel_id else self.private_chat_id
        results["public_post"] = await self._send(target, teaser)

        if results["public_post"]:
            console.print("[green]✅ Public teaser posted![/green]")

        # ── Premium full report ─────────────────────────
        await asyncio.sleep(1)
        premium = self._format_premium_post(top_opportunities, sector_insights)
        results["premium_post"] = await self._send(self.private_chat_id, premium)

        if results["premium_post"]:
            console.print("[green]✅ Premium digest sent to subscribers![/green]")

        return results

    def publish_sync(self, top_opportunities: List[Dict],
                     sector_insights: str) -> Dict:
        """Sync wrapper"""
        return asyncio.run(self.publish_daily(top_opportunities, sector_insights))


if __name__ == "__main__":
    # Test with mock data
    mock_opps = [
        {
            "title": "500MW Solar Power Plant Telangana",
            "department": "TSGENCO",
            "value": "₹2500 Crore",
            "sector": "Renewable Energy",
            "location": "Telangana",
            "deadline": "31-12-2024",
            "url": "https://eprocure.gov.in",
            "total_score": 9.2,
            "ai_analysis": {
                "strategic_score": 9,
                "revenue_score": 9,
                "competition_score": 4,
                "key_insight": "25-year PPA guarantees stable revenue stream",
                "action_required": "Register on portal, prepare technical docs"
            }
        }
    ]
    publisher = ChannelPublisher()
    publisher.publish_sync(mock_opps, "Green energy boom incoming — act fast.")
