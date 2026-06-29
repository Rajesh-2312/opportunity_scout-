"""
monetization/newsletter_formatter.py

Converts daily opportunity reports into:
1. Substack-ready HTML newsletter
2. LinkedIn post (drives followers to subscribe)
3. WhatsApp broadcast message

Publish weekly → builds audience → converts to paid subscribers
"""

import os
from datetime import datetime
from typing import List, Dict
from rich.console import Console

console = Console()


class NewsletterFormatter:
    """
    Transforms raw opportunity data into polished newsletter content.
    One input → three output formats.
    """

    def __init__(self):
        self.author_name = os.getenv("AUTHOR_NAME", "Rajesh M.")
        self.newsletter_name = os.getenv("NEWSLETTER_NAME", "India Infra Intelligence")
        self.substack_url = os.getenv("SUBSTACK_URL", "https://indiainfra.substack.com")
        self.linkedin_url = os.getenv("LINKEDIN_URL", "https://linkedin.com/in/rajesh-maroju-754a65332")
        self.razorpay_link = os.getenv("RAZORPAY_PAYMENT_LINK", "https://https://razorpay.me/@marojurajesh")

    def format_substack_html(self, top_opportunities: List[Dict],
                              sector_insights: str,
                              edition_number: int = 1) -> str:
        """
        Generate a beautiful HTML newsletter for Substack.
        Just paste this into Substack's HTML editor.
        """
        today = datetime.now().strftime("%d %B %Y")
        week_num = datetime.now().isocalendar()[1]

        opp_cards = ""
        for i, opp in enumerate(top_opportunities, 1):
            analysis = opp.get("ai_analysis", {})
            score = opp.get("total_score", 0)
            score_pct = int(score * 10)

            opp_cards += f"""
            <div style="background:#f8f9fa;border-left:4px solid #{"FF6B35" if score >= 8 else "4ECDC4"};
                        padding:20px;margin:20px 0;border-radius:0 8px 8px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="background:{"#FF6B35" if score >= 8 else "#4ECDC4"};color:white;
                                 padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold;">
                        {"🔥 HIGH PRIORITY" if score >= 8 else "⭐ STRONG"}
                    </span>
                    <span style="font-size:13px;color:#666;">Score: {score}/10</span>
                </div>
                <h3 style="color:#1a1a2e;margin:12px 0 8px;font-size:16px;line-height:1.4;">
                    {opp.get('title', 'N/A')[:100]}
                </h3>
                <table style="width:100%;font-size:13px;color:#555;border-collapse:collapse;">
                    <tr>
                        <td style="padding:3px 0;">💰 <strong>Value</strong></td>
                        <td style="padding:3px 0;">{opp.get('value', 'TBD')}</td>
                        <td style="padding:3px 0;">📍 <strong>Location</strong></td>
                        <td style="padding:3px 0;">{opp.get('location', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding:3px 0;">🏛️ <strong>Dept</strong></td>
                        <td style="padding:3px 0;" colspan="3">{opp.get('department', 'N/A')[:50]}</td>
                    </tr>
                    <tr>
                        <td style="padding:3px 0;">⏰ <strong>Deadline</strong></td>
                        <td style="padding:3px 0;">{opp.get('deadline', 'N/A')}</td>
                        <td style="padding:3px 0;">🏷️ <strong>Sector</strong></td>
                        <td style="padding:3px 0;">{opp.get('sector', 'N/A')}</td>
                    </tr>
                </table>
                <div style="background:white;padding:12px;margin-top:12px;border-radius:6px;
                            border:1px solid #e0e0e0;font-size:13px;font-style:italic;color:#444;">
                    💡 {analysis.get('key_insight', 'High strategic value opportunity')}
                </div>
                <div style="margin-top:10px;font-size:13px;">
                    ✅ <strong>Action:</strong> {analysis.get('action_required', 'Review bid requirements')}
                </div>
                <a href="{opp.get('url', '#')}"
                   style="display:inline-block;margin-top:10px;color:#4361ee;font-size:13px;
                          text-decoration:none;font-weight:500;">
                    View Full Tender →
                </a>
            </div>"""

        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             max-width:680px;margin:0 auto;padding:20px;color:#1a1a2e;background:#fff;">

  <!-- Header -->
  <div style="text-align:center;padding:30px 20px;background:linear-gradient(135deg,#1a1a2e,#16213e);
              border-radius:12px;margin-bottom:30px;">
    <div style="font-size:11px;letter-spacing:3px;color:#4ECDC4;text-transform:uppercase;
                font-weight:600;margin-bottom:8px;">EDITION #{edition_number}</div>
    <h1 style="color:white;margin:0 0 8px;font-size:26px;font-weight:800;">
      🎯 {self.newsletter_name}
    </h1>
    <p style="color:#aaa;margin:0;font-size:14px;">{today} | India Infrastructure Intelligence</p>
  </div>

  <!-- Sector Pulse -->
  <div style="background:#fff9f0;border:1px solid #ffe0b2;padding:20px;
              border-radius:8px;margin-bottom:25px;">
    <h2 style="color:#e65100;margin:0 0 12px;font-size:16px;">
      📊 SECTOR PULSE — What's Moving This Week
    </h2>
    <p style="color:#555;font-size:14px;line-height:1.7;margin:0;">
      {sector_insights[:500].replace(chr(10), '<br>')}
    </p>
  </div>

  <!-- Opportunities -->
  <h2 style="color:#1a1a2e;font-size:18px;margin:0 0 5px;">
    🏆 Top {len(top_opportunities)} Opportunities This Week
  </h2>
  <p style="color:#888;font-size:13px;margin:0 0 15px;">
    Ranked by AI score — strategic value × revenue potential ÷ competition
  </p>

  {opp_cards}

  <!-- CTA -->
  <div style="background:linear-gradient(135deg,#4361ee,#3a0ca3);padding:30px;
              border-radius:12px;text-align:center;margin:30px 0;">
    <h3 style="color:white;margin:0 0 8px;font-size:18px;">
      💎 Get the Full Daily Report
    </h3>
    <p style="color:#c8d0ff;margin:0 0 20px;font-size:14px;">
      5 opportunities daily · Full AI analysis · Early warning signals<br>
      <strong style="color:white;">Only ₹299/month</strong>
    </p>
    <a href="{self.razorpay_link}"
       style="background:#FF6B35;color:white;padding:14px 32px;border-radius:6px;
              text-decoration:none;font-weight:700;font-size:15px;display:inline-block;">
      Subscribe Now →
    </a>
  </div>

  <!-- Footer -->
  <div style="border-top:1px solid #eee;padding-top:20px;text-align:center;
              font-size:12px;color:#999;">
    <p>{self.newsletter_name} by <strong>{self.author_name}</strong></p>
    <p>
      <a href="{self.substack_url}" style="color:#4361ee;">Substack</a> ·
      <a href="{self.linkedin_url}" style="color:#4361ee;">LinkedIn</a>
    </p>
    <p style="margin-top:10px;">
      🤖 Powered by AI · Scraping 100+ sources daily · Zero human bias
    </p>
  </div>

</body>
</html>"""

        return html

    def format_linkedin_post(self, top_opportunities: List[Dict],
                              sector_insights: str) -> str:
        """
        LinkedIn post that drives followers to subscribe.
        Hook → Value → CTA structure.
        """
        top = top_opportunities[0] if top_opportunities else {}
        today = datetime.now().strftime("%d %B %Y")

        return f"""🎯 INDIA INFRA INTELLIGENCE — {today}

Most contractors miss ₹{top.get('value', '100+ Crore')} in government tenders every week.

Not because the tenders don't exist.
Because they find out too late.

This week I tracked {len(top_opportunities)} high-value infrastructure opportunities using AI — here's the top one:

📌 {top.get('title', 'Infrastructure Opportunity')[:70]}
💰 Value: {top.get('value', 'TBD')}
📍 {top.get('location', 'India')}
⏰ Deadline: {top.get('deadline', 'Soon')}

Sector signal from this week:
{sector_insights[:280]}...

I publish this every week — tenders, sector intelligence, and exactly which ones have the lowest competition.

→ Full report in my newsletter (link in bio)
→ Premium daily alerts: ₹299/month

Follow me for weekly infrastructure intelligence.

#InfrastructureIndia #GovernmentTenders #SmartInvesting #AIIntelligence #IndiaGrowth #StartupIndia"""

    def format_whatsapp_broadcast(self, top_opportunities: List[Dict]) -> str:
        """
        WhatsApp-friendly format for broadcast lists.
        Short, punchy, mobile-first.
        """
        today = datetime.now().strftime("%d %b")
        lines = [f"🎯 *INFRA INTEL* — {today}\n"]

        for i, opp in enumerate(top_opportunities[:3], 1):
            score = opp.get("total_score", 0)
            lines.append(
                f"*#{i}* {'🔥' if score >= 8 else '⭐'} {opp.get('title', '')[:55]}...\n"
                f"💰 {opp.get('value', 'TBD')} | 📍 {opp.get('location', 'N/A')}\n"
                f"⏰ Deadline: {opp.get('deadline', 'N/A')}\n"
            )

        lines.append(
            f"━━━━━━━━━━━━━\n"
            f"💎 *Full analysis + 2 more tenders*\n"
            f"Subscribe: ₹299/month\n"
            f"{os.getenv('RAZORPAY_PAYMENT_LINK', 'https://razorpay.me/@marojurajesh')}"
        )

        return "\n".join(lines)

    def save_all_formats(self, top_opportunities: List[Dict],
                          sector_insights: str,
                          output_dir: str = "./newsletter") -> Dict:
        """Save all newsletter formats to files"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        files = {}

        # Substack HTML
        html = self.format_substack_html(top_opportunities, sector_insights)
        html_file = f"{output_dir}/substack_{timestamp}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
        files["substack_html"] = html_file
        console.print(f"[green]💾 Substack HTML: {html_file}[/green]")

        # LinkedIn post
        li_post = self.format_linkedin_post(top_opportunities, sector_insights)
        li_file = f"{output_dir}/linkedin_{timestamp}.txt"
        with open(li_file, "w", encoding="utf-8") as f:
            f.write(li_post)
        files["linkedin_post"] = li_file
        console.print(f"[green]💾 LinkedIn post: {li_file}[/green]")

        # WhatsApp broadcast
        wa_msg = self.format_whatsapp_broadcast(top_opportunities)
        wa_file = f"{output_dir}/whatsapp_{timestamp}.txt"
        with open(wa_file, "w", encoding="utf-8") as f:
            f.write(wa_msg)
        files["whatsapp_broadcast"] = wa_file
        console.print(f"[green]💾 WhatsApp broadcast: {wa_file}[/green]")

        return files


if __name__ == "__main__":
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
                "key_insight": "25-year PPA ensures guaranteed revenue stream",
                "action_required": "Register on CPPP portal immediately"
            }
        }
    ]
    formatter = NewsletterFormatter()
    files = formatter.save_all_formats(
        mock_opps,
        "Green energy boom — ₹50,000 Cr NITI Aayog allocation incoming",
        "./test_newsletter"
    )
    print("Files generated:", files)
