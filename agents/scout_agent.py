"""
agents/scout_agent.py
LangGraph-powered AI agent that analyzes, scores, and ranks opportunities
Uses FREE Groq LLM (llama-3.1-70b) for intelligence
"""

import os
import json
from typing import TypedDict, List, Dict, Annotated
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
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
# Initialize LLM (FREE via Groq)
# ─────────────────────────────────────────────
def get_llm():
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_api_key_here":
        console.print("[yellow]⚠️ No NVIDIA API key found. Using mock analysis.[/yellow]")
        return None

    return ChatOpenAI(
        api_key=api_key,
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
        temperature=0.3,
        max_tokens=2000,
        timeout=45,
        max_retries=1
    )


# ─────────────────────────────────────────────
# Agent Nodes
# ─────────────────────────────────────────────

def analyze_tenders_node(state: AgentState) -> AgentState:
    """Node: AI analyzes each tender and scores it"""
    console.print("[bold cyan]🤖 Agent: Analyzing tenders...[/bold cyan]")

    llm = get_llm()
    analyzed = []

    tenders = state["raw_tenders"][:15]  # Process top 15 to save tokens

    for tender in tenders:
        if llm:
            try:
                messages = [
                    SystemMessage(content="""You are an infrastructure investment analyst in India.
                    Analyze government tenders and score them on:
                    1. Strategic importance (1-10)
                    2. Revenue potential (1-10)  
                    3. Competition level - lower is better (1-10)
                    4. Urgency (days to deadline)
                    
                    Return ONLY valid JSON with keys: 
                    strategic_score, revenue_score, competition_score, urgency_days, 
                    opportunity_type, key_insight, action_required, total_score
                    """),
                    HumanMessage(content=f"""
                    Analyze this tender:
                    Title: {tender.get('title', '')}
                    Department: {tender.get('department', '')}
                    Value: {tender.get('value', '')}
                    Sector: {tender.get('sector', '')}
                    Location: {tender.get('location', '')}
                    Description: {tender.get('description', '')}
                    Deadline: {tender.get('deadline', '')}
                    """)
                ]

                response = llm.invoke(messages)
                text = response.content.strip()

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
    """Node: Rank opportunities by score and filter top ones"""
    console.print("[bold cyan]🏆 Agent: Ranking opportunities...[/bold cyan]")

    opportunities = state["analyzed_opportunities"]

    # Sort by total score
    sorted_opps = sorted(
        opportunities,
        key=lambda x: x.get("total_score", 0),
        reverse=True
    )

    # Top 5 high-priority opportunities
    top_5 = sorted_opps[:5]
    state["top_opportunities"] = top_5

    console.print(f"[green]✅ Top {len(top_5)} opportunities identified[/green]")
    return state


def generate_sector_insights_node(state: AgentState) -> AgentState:
    """Node: Generate macro sector intelligence from news"""
    console.print("[bold cyan]📊 Agent: Generating sector insights...[/bold cyan]")

    llm = get_llm()
    news_items = state["raw_news"][:8]

    if not news_items:
        state["sector_insights"] = "No news data available for sector analysis."
        return state

    news_text = "\n".join([
        f"- {n.get('title', '')}: {n.get('description', '')[:200]}"
        for n in news_items
    ])

    if llm:
        try:
            messages = [
                SystemMessage(content="""You are a strategic infrastructure analyst for India.
                Analyze news to identify emerging opportunities BEFORE they become tenders.
                Focus on: policy signals, budget allocations, upcoming projects, sector momentum.
                Be specific, actionable, and concise. Max 300 words."""),
                HumanMessage(content=f"Analyze these infrastructure news items:\n{news_text}")
            ]
            response = llm.invoke(messages)
            state["sector_insights"] = response.content
        except Exception as e:
            state["sector_insights"] = _mock_sector_insights(news_items)
    else:
        state["sector_insights"] = _mock_sector_insights(news_items)

    return state


def generate_daily_report_node(state: AgentState) -> AgentState:
    """Node: Compile everything into a final actionable daily report"""
    console.print("[bold cyan]📝 Agent: Generating daily report...[/bold cyan]")

    top_opps = state["top_opportunities"]
    sector_insights = state["sector_insights"]
    today = datetime.now().strftime("%d %B %Y")

    # Build report
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
# Build LangGraph Agent
# ─────────────────────────────────────────────

def build_scout_agent():
    """Build the LangGraph agent pipeline"""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("analyze_tenders", analyze_tenders_node)
    workflow.add_node("rank_filter", rank_and_filter_node)
    workflow.add_node("sector_insights", generate_sector_insights_node)
    workflow.add_node("generate_report", generate_daily_report_node)

    # Define flow
    workflow.set_entry_point("analyze_tenders")
    workflow.add_edge("analyze_tenders", "rank_filter")
    workflow.add_edge("rank_filter", "sector_insights")
    workflow.add_edge("sector_insights", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


def run_scout_agent(scraped_data: Dict) -> Dict:
    """Run the full agent pipeline on scraped data"""
    console.print("\n[bold magenta]🚀 Starting Opportunity Scout Agent...[/bold magenta]\n")

    agent = build_scout_agent()

    # Combine tenders and bids
    all_tenders = scraped_data.get("tenders", []) + scraped_data.get("gem_bids", [])

    initial_state = AgentState(
        raw_tenders=all_tenders,
        raw_news=scraped_data.get("news", []),
        analyzed_opportunities=[],
        top_opportunities=[],
        daily_report="",
        sector_insights="",
        error=""
    )

    final_state = agent.invoke(initial_state)
    return final_state


if __name__ == "__main__":
    # Test with mock data
    mock_data = {
        "tenders": [
            {
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
            }
        ],
        "gem_bids": [],
        "news": [
            {
                "title": "India targets 500GW renewable energy by 2030",
                "description": "Government accelerates solar and wind deployment",
                "source": "Economic Times"
            }
        ]
    }

    result = run_scout_agent(mock_data)
    print("\n" + result["daily_report"])
