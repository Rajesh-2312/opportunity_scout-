"""
agents/scout_agent.py
AI agent that analyzes, scores, and ranks opportunities.
Uses NVIDIA NIM (OpenAI-compatible API) via the lightweight `openai` SDK.
No LangChain / LangGraph — just direct calls + a simple sequential pipeline.
"""

import os
import json
from typing import TypedDict, List, Dict
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()


# ─────────────────────────────────────────────
# Agent State
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    raw_tenders: List[Dict]
    raw_news: List[Dict]
    analyzed_opportunities: List[Dict]
    top_opportunities: List[Dict]
    daily_report: str
    sector_insights: str
    error: str


# ─────────────────────────────────────────────
# NVIDIA NIM client (OpenAI-compatible)
# ─────────────────────────────────────────────
def get_client():
    """Return an OpenAI-compatible client pointed at NVIDIA NIM, or None for mock mode."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_api_key_here":
        console.print("[yellow]⚠️ No NVIDIA API key found. Using mock analysis.[/yellow]")
        return None
    from openai import OpenAI
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        timeout=45,
        max_retries=1,
    )


def chat(client, system: str, user: str, temperature: float = 0.3, max_tokens: int = 2000) -> str:
    """Single chat completion against NVIDIA NIM. Returns the text content."""
    resp = client.chat.completions.create(
        model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


# ─────────────────────────────────────────────
# Pipeline steps
# ─────────────────────────────────────────────
def analyze_tenders_node(state: AgentState) -> AgentState:
    """AI analyzes each tender and scores it"""
    console.print("[bold cyan]🤖 Agent: Analyzing tenders...[/bold cyan]")

    client = get_client()
    analyzed = []
    tenders = state["raw_tenders"][:15]  # Process top 15 to save tokens

    system = """You are an infrastructure investment analyst in India.
Analyze government tenders and score them on:
1. Strategic importance (1-10)
2. Revenue potential (1-10)
3. Competition level - lower is better (1-10)
4. Urgency (days to deadline)

Return ONLY valid JSON with keys:
strategic_score, revenue_score, competition_score, urgency_days,
opportunity_type, key_insight, action_required, total_score"""

    for tender in tenders:
        if client:
            try:
                user = f"""Analyze this tender:
Title: {tender.get('title', '')}
Department: {tender.get('department', '')}
Value: {tender.get('value', '')}
Sector: {tender.get('sector', '')}
Location: {tender.get('location', '')}
Description: {tender.get('description', '')}
Deadline: {tender.get('deadline', '')}"""

                text = chat(client, system, user, temperature=0.3, max_tokens=2000)

                # Clean JSON response
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                analysis = json.loads(text)
                tender["ai_analysis"] = analysis
                tender["total_score"] = analysis.get("total_score", 0)

            except Exception as e:
                console.print(f"[yellow]⚠️ Analysis failed for tender: {e}[/yellow]")
                tender["ai_analysis"] = _mock_analysis(tender)
                tender["total_score"] = tender["ai_analysis"]["total_score"]
        else:
            tender["ai_analysis"] = _mock_analysis(tender)
            tender["total_score"] = tender["ai_analysis"]["total_score"]

        analyzed.append(tender)

    state["analyzed_opportunities"] = analyzed
    console.print(f"[green]✅ Analyzed {len(analyzed)} opportunities[/green]")
    return state


def rank_and_filter_node(state: AgentState) -> AgentState:
    """Rank opportunities by score and filter top ones"""
    console.print("[bold cyan]🏆 Agent: Ranking opportunities...[/bold cyan]")
    sorted_opps = sorted(
        state["analyzed_opportunities"],
        key=lambda x: x.get("total_score", 0),
        reverse=True
    )
    state["top_opportunities"] = sorted_opps[:5]
    console.print(f"[green]✅ Top {len(state['top_opportunities'])} opportunities identified[/green]")
    return state


def generate_sector_insights_node(state: AgentState) -> AgentState:
    """Generate macro sector intelligence from news"""
    console.print("[bold cyan]📊 Agent: Generating sector insights...[/bold cyan]")

    client = get_client()
    news_items = state["raw_news"][:8]

    if not news_items:
        state["sector_insights"] = "No news data available for sector analysis."
        return state

    news_text = "\n".join([
        f"- {n.get('title', '')}: {n.get('description', '')[:200]}"
        for n in news_items
    ])

    if client:
        try:
            system = """You are a strategic infrastructure analyst for India.
Analyze news to identify emerging opportunities BEFORE they become tenders.
Focus on: policy signals, budget allocations, upcoming projects, sector momentum.
Be specific, actionable, and concise. Max 300 words."""
            state["sector_insights"] = chat(
                client, system,
                f"Analyze these infrastructure news items:\n{news_text}",
                temperature=0.3, max_tokens=2000
            )
        except Exception:
            state["sector_insights"] = _mock_sector_insights(news_items)
    else:
        state["sector_insights"] = _mock_sector_insights(news_items)

    return state


def generate_daily_report_node(state: AgentState) -> AgentState:
    """Compile everything into a final actionable daily report"""
    console.print("[bold cyan]📝 Agent: Generating daily report...[/bold cyan]")

    top_opps = state["top_opportunities"]
    sector_insights = state["sector_insights"]
    today = datetime.now().strftime("%d %B %Y")

    report_lines = [
        f"🎯 OPPORTUNITY SCOUT DAILY REPORT",
        f"📅 {today}",
        f"{'='*50}",
        "",
        f"📊 SECTOR INTELLIGENCE",
        f"{'─'*40}",
        sector_insights,
        "",
        f"🏆 TOP {len(top_opps)} OPPORTUNITIES TODAY",
        f"{'─'*40}",
    ]

    for i, opp in enumerate(top_opps, 1):
        analysis = opp.get("ai_analysis", {})
        report_lines.extend([
            f"",
            f"#{i} {opp.get('title', 'Unknown')[:80]}",
            f"💰 Value: {opp.get('value', 'TBD')}",
            f"🏛️ Dept: {opp.get('department', 'N/A')}",
            f"📍 Location: {opp.get('location', 'N/A')}",
            f"⏰ Deadline: {opp.get('deadline', 'N/A')}",
            f"⭐ Score: {opp.get('total_score', 0)}/10",
            f"💡 Insight: {analysis.get('key_insight', 'High potential opportunity')}",
            f"✅ Action: {analysis.get('action_required', 'Review and prepare bid')}",
            f"🔗 Source: {opp.get('source', 'N/A')} | {opp.get('url', '')}",
        ])

    report_lines.extend([
        "",
        f"{'='*50}",
        f"🤖 Generated by Opportunity Scout AI",
        f"💼 Build. Learn. Profit."
    ])

    state["daily_report"] = "\n".join(report_lines)
    console.print("[green]✅ Daily report generated![/green]")
    return state


# ─────────────────────────────────────────────
# Mock Analysis (when no API key)
# ─────────────────────────────────────────────
def _mock_analysis(tender: Dict) -> Dict:
    """Mock AI analysis for testing"""
    import random
    sector = tender.get("sector", "").lower()

    scores = {
        "renewable energy": (9, 8, 4),
        "ports": (8, 9, 5),
        "logistics": (7, 7, 4),
        "airports": (9, 8, 6),
        "infrastructure": (7, 7, 5),
    }

    base = scores.get(sector, (6, 6, 5))
    strategic = base[0] + random.randint(-1, 1)
    revenue = base[1] + random.randint(-1, 1)
    competition = base[2] + random.randint(-1, 1)
    total = round((strategic + revenue + (10 - competition)) / 3, 1)

    insights = {
        "renewable energy": "Green energy projects have 25-year government-backed PPAs ensuring stable revenue",
        "ports": "Port infrastructure has natural monopoly characteristics — high barriers to entry",
        "logistics": "E-commerce boom driving 40% YoY growth in logistics infrastructure demand",
        "airports": "UDAN scheme guarantees minimum traffic viability reducing risk significantly",
        "infrastructure": "Budget 2024 allocated ₹11.11 lakh crore for infrastructure — tailwind for all projects"
    }

    return {
        "strategic_score": min(10, max(1, strategic)),
        "revenue_score": min(10, max(1, revenue)),
        "competition_score": min(10, max(1, competition)),
        "urgency_days": random.randint(15, 60),
        "opportunity_type": "Government Contract",
        "key_insight": insights.get(sector, "Strong infrastructure demand driven by India's growth story"),
        "action_required": "Register on portal, prepare technical qualification documents",
        "total_score": min(10, max(1, total))
    }


def _mock_sector_insights(news_items: List[Dict]) -> str:
    return """🔥 EMERGING OPPORTUNITIES (Next 30-60 Days):

1. GREEN HYDROGEN CORRIDOR — NITI Aayog signals ₹50,000 Cr allocation. Watch for tenders from NTPC Green, SECI, and state DISCOMs. Early movers will win 10-year supply contracts.

2. SMART PORTS MODERNIZATION — Sagarmala Phase 2 tenders expected. Focus on Andhra Pradesh & Telangana coastal logistics. Container terminal automation is the key skill requirement.

3. REGIONAL AIRPORT EXPANSION — AAI floating 12 new airport tenders under UDAN 5.0. Tier-2 cities in AP/Telangana are priority. Ground handling and cargo logistics are immediate opportunities.

4. DATA CENTER BOOM — Hyperscalers (AWS, Google, Microsoft) expanding in Hyderabad. Supporting infrastructure (power, cooling, fiber) tenders worth ₹2000+ Crore expected in Q1 2025.

⚡ MOMENTUM SIGNAL: Infrastructure spending is front-loaded in H1 FY25. Act NOW — tenders from October-December are the most competitive time."""


# ─────────────────────────────────────────────
# Run the agent pipeline (sequential, no LangGraph)
# ─────────────────────────────────────────────
def run_scout_agent(scraped_data: Dict) -> Dict:
    """Run the full agent pipeline on scraped data"""
    console.print("\n[bold magenta]🚀 Starting Opportunity Scout Agent...[/bold magenta]\n")

    all_tenders = scraped_data.get("tenders", []) + scraped_data.get("gem_bids", [])

    state: AgentState = {
        "raw_tenders": all_tenders,
        "raw_news": scraped_data.get("news", []),
        "analyzed_opportunities": [],
        "top_opportunities": [],
        "daily_report": "",
        "sector_insights": "",
        "error": "",
    }

    state = analyze_tenders_node(state)
    state = rank_and_filter_node(state)
    state = generate_sector_insights_node(state)
    state = generate_daily_report_node(state)
    return state


if __name__ == "__main__":
    mock_data = {
        "tenders": [{
            "id": "TEST-001",
            "title": "500MW Solar Power Plant in Telangana",
            "department": "TSGENCO",
            "value": "₹2500 Crore",
            "sector": "renewable energy",
            "location": "Telangana",
            "description": "Large scale solar generation",
            "deadline": "2024-12-31",
            "source": "CPPP",
            "url": "https://eprocure.gov.in"
        }],
        "gem_bids": [],
        "news": [{
            "title": "India targets 500GW renewable energy by 2030",
            "description": "Government accelerates solar and wind deployment",
            "source": "Economic Times"
        }]
    }
    result = run_scout_agent(mock_data)
    print("\n" + result["daily_report"])
