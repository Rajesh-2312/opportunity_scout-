"""
market_intelligence/intelligence_agent.py

LangGraph agent that:
1. Reads BSE announcements + bulk deals + price signals
2. Cross-references with existing tender database
3. Predicts: "This company move = tender incoming in X days"
4. Generates early warning alerts

The Adani Playbook:
  Land acquired → Environmental clearance → Tender floated → Construction begins
  (30-60 days)    (60-90 days)              (90-120 days)

We intercept at step 1.
"""

import os
import json
from typing import TypedDict, List, Dict
from datetime import datetime, timedelta
from dotenv import load_dotenv

from rich.console import Console

load_dotenv()
console = Console()


# ─────────────────────────────────────────────
# Agent State
# ─────────────────────────────────────────────
class MarketAgentState(TypedDict):
    announcements: List[Dict]
    bulk_deals: List[Dict]
    price_signals: List[Dict]
    existing_tenders: List[Dict]        # From Phase 1 memory
    pattern_matches: List[Dict]         # Announcement → tender correlation
    predictions: List[Dict]             # Predicted future tenders
    early_warnings: List[Dict]          # High confidence alerts
    market_report: str
    error: str


# ─────────────────────────────────────────────
# Known Patterns (Adani/Tata playbook)
# ─────────────────────────────────────────────
COMPANY_PLAYBOOKS = {
    "Adani": {
        "pattern": "Adani acquires land/MoU → tender within 60-90 days",
        "sectors": ["Ports", "Airports", "Green Energy", "Data Centers"],
        "typical_lag_days": 75,
        "sub_tender_types": [
            "Civil construction", "Equipment supply", "EPC contracts",
            "O&M contracts", "Logistics setup"
        ]
    },
    "L&T": {
        "pattern": "L&T wins large order → sub-contractor tenders within 30 days",
        "sectors": ["Roads", "Buildings", "Power", "Water"],
        "typical_lag_days": 30,
        "sub_tender_types": [
            "Civil works", "Steel fabrication", "Electrical works",
            "Plumbing & MEP", "Labour contracts"
        ]
    },
    "NTPC": {
        "pattern": "NTPC capacity addition announcement → equipment tenders in 45 days",
        "sectors": ["Power Generation", "Renewable Energy"],
        "typical_lag_days": 45,
        "sub_tender_types": [
            "Turbine supply", "Solar panels", "Transformer supply",
            "Civil works", "Grid connectivity"
        ]
    },
    "GMR": {
        "pattern": "GMR airport concession → supply chain tenders in 60 days",
        "sectors": ["Airports"],
        "typical_lag_days": 60,
        "sub_tender_types": [
            "Ground handling equipment", "IT systems",
            "Food & beverage concessions", "Retail spaces", "Security systems"
        ]
    },
    "IRB": {
        "pattern": "IRB highway award → material supply tenders in 21 days",
        "sectors": ["Roads", "Highways"],
        "typical_lag_days": 21,
        "sub_tender_types": [
            "Bitumen supply", "Aggregates", "Construction equipment rental",
            "Survey & mapping", "Safety equipment"
        ]
    }
}


# ─────────────────────────────────────────────
# Agent Nodes
# ─────────────────────────────────────────────

def pattern_matching_node(state: MarketAgentState) -> MarketAgentState:
    """Node: Match announcements to known company playbooks"""
    console.print("[bold cyan]🔍 Agent: Pattern matching...[/bold cyan]")

    pattern_matches = []
    announcements = state["announcements"]
    bulk_deals = state["bulk_deals"]

    for announcement in announcements:
        headline = announcement.get("headline", "").lower()
        company = announcement.get("company", "")
        signal_type = announcement.get("signal_type", "")

        # Match to company playbook
        matched_playbook = None
        for brand, playbook in COMPANY_PLAYBOOKS.items():
            if brand.lower() in company.lower():
                matched_playbook = {**playbook, "brand": brand}
                break

        if matched_playbook or signal_type in ["ORDER_WIN", "LAND_ACQUISITION", "EXPANSION"]:
            lag_days = matched_playbook["typical_lag_days"] if matched_playbook else 60
            expected_date = datetime.now() + timedelta(days=lag_days)

            match = {
                "announcement": announcement,
                "playbook": matched_playbook,
                "signal_strength": _calculate_signal_strength(announcement, bulk_deals, company),
                "expected_tender_date": expected_date.strftime("%d-%m-%Y"),
                "expected_tender_types": matched_playbook["sub_tender_types"][:3] if matched_playbook else [],
                "confidence": "HIGH" if matched_playbook else "MEDIUM"
            }
            pattern_matches.append(match)

    state["pattern_matches"] = pattern_matches
    console.print(f"[green]✅ Found {len(pattern_matches)} pattern matches[/green]")
    return state


def predict_tenders_node(state: MarketAgentState) -> MarketAgentState:
    """Node: AI predicts specific upcoming tenders based on patterns"""
    console.print("[bold cyan]🔮 Agent: Predicting upcoming tenders...[/bold cyan]")

    client = _get_client()
    predictions = []

    system = """You are an infrastructure investment analyst in India.
Given a company announcement, predict specific upcoming government/private tenders.
Focus on: what sub-tenders will be floated, estimated value, timeline, who can bid.
Return ONLY valid JSON with keys:
predicted_tender_title, estimated_value_cr, timeline_days,
eligible_bidders, action_for_small_contractor, opportunity_score (1-10)"""

    for match in state["pattern_matches"][:8]:  # Process top 8
        announcement = match["announcement"]
        playbook = match.get("playbook", {})

        if client:
            try:
                user = f"""Company: {announcement.get('company')}
Announcement: {announcement.get('headline')}
Signal Type: {announcement.get('signal_type')}
Company Pattern: {playbook.get('pattern', 'Infrastructure company activity')}
Expected tender types: {playbook.get('sub_tender_types', [])}

Predict the specific tender that will follow this announcement."""
                text = _chat(client, system, user)
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                prediction = json.loads(text)
                prediction["source_announcement"] = announcement.get("headline", "")
                prediction["company"] = announcement.get("company", "")
                prediction["confidence"] = match["confidence"]
                prediction["signal_strength"] = match["signal_strength"]
                predictions.append(prediction)

            except Exception as e:
                predictions.append(_mock_prediction(announcement, playbook))
        else:
            predictions.append(_mock_prediction(announcement, playbook))

    # Sort by opportunity score
    predictions.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
    state["predictions"] = predictions
    console.print(f"[green]✅ Generated {len(predictions)} tender predictions[/green]")
    return state


def generate_early_warnings_node(state: MarketAgentState) -> MarketAgentState:
    """Node: Flag highest confidence predictions as early warnings"""
    console.print("[bold cyan]🚨 Agent: Generating early warnings...[/bold cyan]")

    early_warnings = []

    # High scoring predictions
    for pred in state["predictions"]:
        score = pred.get("opportunity_score", 0)
        confidence = pred.get("confidence", "MEDIUM")
        if score >= 7 or confidence == "HIGH":
            early_warnings.append({
                **pred,
                "warning_level": "🔴 CRITICAL" if score >= 9 else "🟡 HIGH",
                "act_by": (datetime.now() + timedelta(
                    days=pred.get("timeline_days", 60) - 14
                )).strftime("%d-%m-%Y")
            })

    # Unusual bulk deals as warnings
    for deal in state["bulk_deals"]:
        if deal.get("deal_type") == "BUY" and float(deal.get("value_cr", 0)) > 50:
            early_warnings.append({
                "warning_level": "🟡 HIGH",
                "type": "INSTITUTIONAL_ACCUMULATION",
                "company": deal["company"],
                "predicted_tender_title": f"Smart money entering {deal['company']} — {deal['sector']} tender expected",
                "estimated_value_cr": deal.get("value_cr", 0) * 10,
                "timeline_days": 45,
                "action_for_small_contractor": f"Monitor {deal['company']} BSE filings daily. Prepare pre-qualification documents for {deal['sector']} contracts.",
                "opportunity_score": 7.5,
                "signal": deal.get("signal", ""),
                "client": deal.get("client", "")
            })

    state["early_warnings"] = sorted(
        early_warnings,
        key=lambda x: x.get("opportunity_score", 0),
        reverse=True
    )[:8]

    console.print(f"[green]✅ {len(state['early_warnings'])} early warnings generated[/green]")
    return state


def generate_market_report_node(state: MarketAgentState) -> MarketAgentState:
    """Node: Compile everything into actionable market intelligence report"""
    console.print("[bold cyan]📝 Agent: Generating market report...[/bold cyan]")

    today = datetime.now().strftime("%d %B %Y")
    warnings = state["early_warnings"]
    predictions = state["predictions"]
    bulk_deals = state["bulk_deals"]
    price_signals = state["price_signals"]

    lines = [
        f"🧠 MARKET INTELLIGENCE REPORT",
        f"📅 {today}",
        f"{'='*55}",
        "",
        f"📊 SIGNAL SUMMARY",
        f"  📋 BSE Announcements analyzed: {len(state['announcements'])}",
        f"  💰 Bulk deals tracked: {len(bulk_deals)}",
        f"  📈 Price signals detected: {len(price_signals)}",
        f"  🔮 Tender predictions: {len(predictions)}",
        f"  🚨 Early warnings: {len(warnings)}",
        "",
        f"{'='*55}",
        f"🚨 EARLY WARNINGS — ACT NOW",
        f"{'─'*40}",
    ]

    for i, warning in enumerate(warnings[:5], 1):
        lines.extend([
            f"",
            f"{warning.get('warning_level', '🟡')} WARNING #{i}",
            f"🏢 Company: {warning.get('company', 'N/A')}",
            f"📌 Predicted: {warning.get('predicted_tender_title', 'N/A')[:80]}",
            f"💰 Est. Value: ₹{warning.get('estimated_value_cr', 'TBD')} Crore",
            f"⏳ Timeline: {warning.get('timeline_days', 60)} days",
            f"📅 Act by: {warning.get('act_by', 'ASAP')}",
            f"✅ Action: {warning.get('action_for_small_contractor', 'Monitor closely')}",
        ])

    lines.extend([
        "",
        f"{'='*55}",
        f"💰 SMART MONEY MOVEMENTS",
        f"{'─'*40}",
    ])

    for deal in bulk_deals[:3]:
        deal_emoji = "🟢" if deal.get("deal_type") == "BUY" else "🔴"
        lines.append(
            f"{deal_emoji} {deal.get('company', 'N/A')} | "
            f"{deal.get('deal_type')} ₹{deal.get('value_cr', 0)} Cr | "
            f"{deal.get('client', 'N/A')[:40]}"
        )
        if deal.get("signal"):
            lines.append(f"   💡 {deal['signal']}")

    if price_signals:
        lines.extend([
            "",
            f"{'='*55}",
            f"📈 UNUSUAL PRICE ACTIVITY",
            f"{'─'*40}",
        ])
        for sig in price_signals[:3]:
            lines.append(
                f"  {sig.get('symbol')} {sig.get('change_pct', 0):+.1f}% — "
                f"{sig.get('alert', '')[:60]}"
            )

    lines.extend([
        "",
        f"{'='*55}",
        f"🤖 Generated by Market Intelligence Agent",
        f"⚡ Powered by BSE Data + Groq AI"
    ])

    state["market_report"] = "\n".join(lines)
    console.print("[green]✅ Market report generated![/green]")
    return state


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _get_client():
    """OpenAI-compatible client for NVIDIA NIM, or None for mock mode."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_api_key_here":
        return None
    from openai import OpenAI
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        timeout=45,
        max_retries=1,
    )


def _chat(client, system: str, user: str) -> str:
    resp = client.chat.completions.create(
        model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"),
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=1500,
    )
    return (resp.choices[0].message.content or "").strip()


def _calculate_signal_strength(announcement: Dict, bulk_deals: List[Dict], company: str) -> str:
    """Higher if both announcement AND bulk deal exist for same company"""
    has_bulk_deal = any(company.split()[0].lower() in d.get("company", "").lower()
                       for d in bulk_deals)
    signal_type = announcement.get("signal_type", "")
    high_signals = ["ORDER_WIN", "LAND_ACQUISITION", "EXPANSION"]

    if has_bulk_deal and signal_type in high_signals:
        return "VERY_HIGH"
    elif has_bulk_deal or signal_type in high_signals:
        return "HIGH"
    return "MEDIUM"


def _mock_prediction(announcement: Dict, playbook: Dict) -> Dict:
    """Mock prediction when no LLM"""
    import random
    company = announcement.get("company", "Unknown")
    signal = announcement.get("signal_type", "GENERAL")

    template_map = {
        "ORDER_WIN": {
            "title": f"Sub-contractor civil works for {company} project",
            "value": random.randint(50, 500),
            "days": 30,
            "action": "Register as vendor with company. Prepare PQ documents. Visit site."
        },
        "LAND_ACQUISITION": {
            "title": f"Site development and earthworks contract — {company}",
            "value": random.randint(100, 800),
            "days": 60,
            "action": "Monitor company website for vendor registration. Prepare capability statement."
        },
        "GREEN_ENERGY": {
            "title": f"EPC contract for renewable energy facility — {company}",
            "value": random.randint(200, 2000),
            "days": 75,
            "action": "Get MNRE empanelment. Tie up with equipment suppliers. Prepare bid bond."
        },
        "PARTNERSHIP": {
            "title": f"JV project supply chain and logistics tenders — {company}",
            "value": random.randint(80, 400),
            "days": 45,
            "action": "Identify which partner is the lead. Contact their procurement team."
        }
    }

    template = template_map.get(signal, template_map["ORDER_WIN"])
    return {
        "predicted_tender_title": template["title"],
        "estimated_value_cr": template["value"],
        "timeline_days": template["days"],
        "eligible_bidders": "SME contractors, EPC firms, equipment suppliers",
        "action_for_small_contractor": template["action"],
        "opportunity_score": random.uniform(6.5, 9.2),
        "source_announcement": announcement.get("headline", ""),
        "company": company,
        "confidence": "MEDIUM",
        "signal_strength": "HIGH"
    }


# ─────────────────────────────────────────────
# Build Agent
# ─────────────────────────────────────────────

def run_market_agent(bse_data: Dict, existing_tenders: List[Dict] = None) -> Dict:
    """Run the market intelligence agent (sequential pipeline, no LangGraph)"""
    console.print("\n[bold magenta]🧠 Starting Market Intelligence Agent...[/bold magenta]\n")

    state: MarketAgentState = {
        "announcements": bse_data.get("announcements", []),
        "bulk_deals": bse_data.get("bulk_deals", []),
        "price_signals": bse_data.get("price_signals", []),
        "existing_tenders": existing_tenders or [],
        "pattern_matches": [],
        "predictions": [],
        "early_warnings": [],
        "market_report": "",
        "error": "",
    }

    state = pattern_matching_node(state)
    state = predict_tenders_node(state)
    state = generate_early_warnings_node(state)
    state = generate_market_report_node(state)
    return state


if __name__ == "__main__":
    from bse_scraper import run_bse_scraper
    bse_data = run_bse_scraper(days_back=7)
    result = run_market_agent(bse_data)
    print("\n" + result["market_report"])
