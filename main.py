
"""
main.py
Opportunity Scout Agent - Master Orchestrator
All 5 Phases: Scrape → Store → Analyze → Report → Notify → Monetize → Market Intel → Stocks → Dashboard

Usage:
    python main.py                  # Phase 1: Scout tenders
    python main.py --monetize       # Phase 2: Publish + leads + newsletter
    python main.py --market         # Phase 3: BSE signals + predictions
    python main.py --stocks         # Phase 4: Stock signals + paper trades
    python main.py --full           # ALL phases in sequence
    python main.py --dashboard      # Revenue dashboard terminal
    python main.py --portfolio      # Paper trading portfolio
    python main.py --leads          # Lead generation only
    python main.py --search "solar" # Search tender memory
    python main.py --schedule       # Run every 6 hours
    python dashboard/run_dashboard.py  # Phase 5: Web dashboard
"""

import os
import sys

# Force UTF-8 console so emoji-rich output never crashes on legacy Windows code pages
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import json
import time
import asyncio
import schedule
import argparse
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── All Phase Imports ──────────────────────────────────────
from scrapers.tender_scraper import run_all_scrapers
from memory.vector_store import OpportunityMemory
from agents.scout_agent import run_scout_agent
from notifier.telegram_bot import TelegramNotifier, FileNotifier
from notifier.seen_store import SeenStore
from monetization.channel_publisher import ChannelPublisher
from monetization.lead_generator import run_lead_generation
from monetization.newsletter_formatter import NewsletterFormatter
from monetization.payment_tracker import RevenueDashboard, SubscriberTracker
from market_intelligence.bse_scraper import run_bse_scraper, StockPriceMonitor
from market_intelligence.intelligence_agent import run_market_agent
from market_intelligence.correlation_engine import run_correlation_analysis
from stock_intelligence.signal_detector import SignalDetector
from stock_intelligence.paper_trader import run_paper_trading, TradingSignalExecutor
from stock_intelligence.stock_dashboard import StockDashboard, run_stock_dashboard
from stock_intelligence.investment_advisor import run_investment_recommendations, run_investment_monitor

console = Console()


# ─────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────
def print_banner():
    console.print(Panel.fit(
        "[bold cyan]OPPORTUNITY SCOUT[/bold cyan]\n"
        "[green]India Infrastructure Intelligence System[/green]\n"
        "[dim]Phases 1-5 | Zero Cost | Powered by AI[/dim]",
        border_style="cyan"
    ))


# ─────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────
def load_config() -> dict:
    sectors_raw = os.getenv("TARGET_SECTORS", "infrastructure,energy,ports,logistics,airports,green hydrogen")
    states_raw  = os.getenv("TARGET_STATES",  "Telangana,Andhra Pradesh,Karnataka")
    return {
        "target_sectors":    [s.strip() for s in sectors_raw.split(",")],
        "target_states":     [s.strip() for s in states_raw.split(",")],
        "min_value_lakhs":   int(os.getenv("MIN_TENDER_VALUE_LAKHS", "10")),
        "scan_interval_hours": int(os.getenv("SCAN_INTERVAL_HOURS", "6")),
    }


# ─────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────
def display_results_table(top_opportunities: list):
    table = Table(title="Top Opportunities", box=box.ROUNDED,
                  show_header=True, header_style="bold cyan")
    table.add_column("#",        style="dim",  width=4)
    table.add_column("Title",    max_width=40)
    table.add_column("Value",    style="green",  width=15)
    table.add_column("Sector",   style="yellow", width=15)
    table.add_column("Score",    style="bold red", width=8)
    table.add_column("Deadline", width=12)

    for i, opp in enumerate(top_opportunities, 1):
        score = opp.get("total_score", 0)
        emoji = "🔥" if score >= 8 else "⭐" if score >= 6 else "📌"
        table.add_row(
            str(i),
            str(opp.get("title", "N/A"))[:40],
            str(opp.get("value", "TBD"))[:15],
            str(opp.get("sector", "N/A"))[:15],
            f"{emoji} {score}",
            str(opp.get("deadline", "N/A"))[:12]
        )
    console.print(table)


def save_pipeline_result(result: dict):
    """Save combined pipeline result for dashboard to read"""
    os.makedirs("./data", exist_ok=True)
    fn = f"./data/pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn, "w") as f:
        json.dump(result, f, indent=2, default=str)
    return fn


# ─────────────────────────────────────────────────────────
# PHASE 1: Opportunity Scout
# ─────────────────────────────────────────────────────────
def run_pipeline(config: dict, use_mock: bool = False) -> dict:
    """Phase 1 — Scrape → Store → Analyze → Report → Notify"""
    start = datetime.now()
    console.print(f"\n[bold]Pipeline started at {start.strftime('%H:%M:%S')}[/bold]\n")

    # Step 1: Scrape
    console.print(Panel("Step 1/4: Scraping Opportunities", style="cyan"))
    scraped = run_all_scrapers(config)

    # Step 2: Store
    console.print(Panel("Step 2/4: Storing in Vector Memory", style="cyan"))
    memory = OpportunityMemory("./data/chroma_db")
    memory.store_bulk(scraped)

    # Step 3: AI Analysis
    console.print(Panel("Step 3/4: AI Agent Analyzing...", style="cyan"))
    agent_result = run_scout_agent(scraped)
    top_opps       = agent_result.get("top_opportunities", [])
    sector_insights = agent_result.get("sector_insights", "")
    daily_report    = agent_result.get("daily_report", "")

    # Step 4: Notify
    console.print(Panel("Step 4/4: Sending Report", style="cyan"))
    display_results_table(top_opps)
    console.print(f"\n[bold yellow]SECTOR INSIGHTS:[/bold yellow]\n{sector_insights}")

    file_notifier = FileNotifier("./reports")
    report_file   = file_notifier.save_report(daily_report)
    file_notifier.save_json_report({
        "top_opportunities": top_opps,
        "sector_insights":   sector_insights,
        "scraped_summary": {
            "tenders":  len(scraped.get("tenders", [])),
            "gem_bids": len(scraped.get("gem_bids", [])),
            "news":     len(scraped.get("news", []))
        }
    })

    # Notify ONLY about new opportunities (never seen / alerted before)
    analyzed = agent_result.get("analyzed_opportunities", []) or top_opps
    seen = SeenStore("./data/notified.json")
    new_opps = sorted(
        seen.filter_new(analyzed),
        key=lambda x: x.get("total_score", 0),
        reverse=True
    )

    telegram = TelegramNotifier()
    if new_opps:
        console.print(Panel(
            f"[bold green]{len(new_opps)} NEW opportunit{'y' if len(new_opps)==1 else 'ies'} "
            f"detected → sending Telegram alert[/bold green]",
            style="green"
        ))
        telegram.send_digest_sync(new_opps[:8], sector_insights)
        seen.mark(new_opps)
    else:
        console.print(Panel(
            "[dim]No new opportunities since last scan — no Telegram alert sent.[/dim]",
            style="dim"
        ))

    # Step 5 (optional): Monetization
    if config.get("run_monetization", False):
        run_monetization_step(top_opps, sector_insights)

    duration = (datetime.now() - start).seconds
    console.print(Panel(
        f"[bold green]PIPELINE COMPLETE[/bold green]\n\n"
        f"Tenders scraped:   {len(scraped.get('tenders', []))}\n"
        f"GeM bids found:    {len(scraped.get('gem_bids', []))}\n"
        f"News items:        {len(scraped.get('news', []))}\n"
        f"Top opportunities: {len(top_opps)}\n"
        f"Duration:          {duration}s\n"
        f"Report saved:      {report_file}",
        style="green"
    ))

    # Save combined result for dashboard
    save_pipeline_result({
        "top_opportunities": top_opps,
        "sector_insights":   sector_insights
    })

    return agent_result


# ─────────────────────────────────────────────────────────
# PHASE 2: Monetization Engine
# ─────────────────────────────────────────────────────────
def run_monetization_step(top_opps: list, sector_insights: str):
    """Phase 2 — Publish → Newsletter → Leads"""
    console.print(Panel("Monetization Engine", style="magenta"))

    # Publish to Telegram channel
    publisher = ChannelPublisher()
    publisher.publish_sync(top_opps, sector_insights)

    # Generate newsletter formats (Substack HTML + LinkedIn + WhatsApp)
    formatter = NewsletterFormatter()
    files = formatter.save_all_formats(top_opps, sector_insights)
    console.print(f"[green]Newsletter formats saved: {len(files)} files[/green]")

    # Generate leads (Monday only to avoid spam)
    if datetime.now().weekday() == 0:
        result = run_lead_generation(top_opps)
        console.print(f"[green]Leads: {len(result.get('leads',[]))} found, {len(result.get('emails',[]))} emails drafted[/green]")


def run_monetization_pipeline():
    """Standalone Phase 2 pipeline"""
    config  = load_config()
    scraped = run_all_scrapers(config)
    all_tenders = scraped.get("tenders", []) + scraped.get("gem_bids", [])

    # Quick AI analysis for insights
    agent_result    = run_scout_agent(scraped)
    top_opps        = agent_result.get("top_opportunities", [])
    sector_insights = agent_result.get("sector_insights", "")

    run_monetization_step(top_opps, sector_insights)


# ─────────────────────────────────────────────────────────
# PHASE 3: Market Intelligence
# ─────────────────────────────────────────────────────────
def run_market_intelligence_pipeline() -> dict:
    """Phase 3 — BSE signals → AI predictions → Correlation"""
    console.print(Panel("Market Intelligence Agent", style="magenta"))

    # Step 1: Scrape BSE data
    console.print(Panel("Step 1/3: Scanning BSE/NSE Signals", style="cyan"))
    bse_data = run_bse_scraper(days_back=7)

    # Step 2: AI analysis
    console.print(Panel("Step 2/3: AI Analyzing Market Signals", style="cyan"))
    market_result = run_market_agent(bse_data)

    # Step 3: Correlate with tender database
    console.print(Panel("Step 3/3: Correlating with Tender Database", style="cyan"))
    memory   = OpportunityMemory("./data/chroma_db")
    recent   = memory.get_recent_tenders(30)
    existing = [r.get("metadata", {}) for r in recent]

    correlation_result = run_correlation_analysis(
        market_result.get("predictions", []),
        existing,
        market_result.get("early_warnings", [])
    )

    # Save report
    report       = market_result.get("market_report", "")
    file_notifier = FileNotifier("./reports")
    file_notifier.save_report("MARKET INTELLIGENCE\n" + report)

    # Send top 3 Telegram alerts
    telegram = TelegramNotifier()
    for alert in correlation_result.get("telegram_alerts", [])[:3]:
        asyncio.run(telegram.send_message(alert))

    # Save for dashboard
    save_pipeline_result({
        "early_warnings": market_result.get("early_warnings", []),
        "predictions":    market_result.get("predictions", []),
        "bulk_deals":     bse_data.get("bulk_deals", []),
        "price_signals":  bse_data.get("price_signals", [])
    })

    console.print(Panel(
        f"[bold green]Market Intelligence Complete[/bold green]\n\n"
        f"Announcements: {len(bse_data.get('announcements', []))}\n"
        f"Bulk deals:    {len(bse_data.get('bulk_deals', []))}\n"
        f"Predictions:   {len(market_result.get('predictions', []))}\n"
        f"Warnings:      {len(market_result.get('early_warnings', []))}\n"
        f"Correlations:  {len(correlation_result.get('correlations', []))}",
        style="green"
    ))

    return {"market_result": market_result, "correlations": correlation_result}


# ─────────────────────────────────────────────────────────
# PHASE 4: Stock Intelligence
# ─────────────────────────────────────────────────────────
def run_stock_intelligence_pipeline() -> dict:
    """Phase 4 — Tender signals → Stock picks → Paper trades"""
    console.print(Panel("Stock Intelligence Layer", style="yellow"))

    # Step 1: Load tenders from memory
    console.print(Panel("Step 1/3: Loading Tender & Market Data", style="cyan"))
    memory = OpportunityMemory("./data/chroma_db")
    recent  = memory.get_recent_tenders(50)
    tenders = [r.get("metadata", {}) for r in recent]

    # Scrape fresh if memory is empty
    if len(tenders) < 5:
        config  = load_config()
        scraped = run_all_scrapers(config)
        tenders = scraped.get("tenders", []) + scraped.get("gem_bids", [])

    # Step 2: Detect signals from tenders
    console.print(Panel("Step 2/3: Detecting Stock Signals", style="cyan"))
    detector = SignalDetector()
    signals  = detector.detect_from_tenders(tenders)

    # Add signals from market intelligence early warnings
    try:
        bse_data      = run_bse_scraper(days_back=7)
        market_result = run_market_agent(bse_data)
        market_sigs   = detector.detect_from_market_intel(
            market_result.get("early_warnings", [])
        )
        signals = sorted(signals + market_sigs,
                         key=lambda x: x.get("strength", 0), reverse=True)
    except Exception as e:
        console.print(f"[yellow]Market intel unavailable: {e}[/yellow]")

    # Step 3: Paper trade + display
    console.print(Panel("Step 3/3: Paper Trading + Dashboard", style="cyan"))
    symbols    = list({s["symbol"] for s in signals[:10]})
    price_data = StockPriceMonitor().fetch_price_data(symbols)

    trading_result = run_paper_trading(signals, price_data)
    portfolio      = trading_result["portfolio"]
    open_trades    = trading_result.get("executed_trades", [])

    run_stock_dashboard(signals, portfolio, open_trades)

    # Save + Telegram
    dashboard    = StockDashboard()
    report_file  = dashboard.save_report(signals, portfolio)
    telegram_msg = dashboard.generate_telegram_report(signals, portfolio)
    telegram     = TelegramNotifier()
    asyncio.run(telegram.send_message(telegram_msg))

    # Save for dashboard
    save_pipeline_result({"stock_signals": signals, "portfolio": portfolio})

    console.print(Panel(
        f"[bold green]Stock Intelligence Complete[/bold green]\n\n"
        f"Signals generated: {len(signals)}\n"
        f"Trades executed:   {len(open_trades)}\n"
        f"Win rate:          {portfolio.get('win_rate', 0)}%",
        style="green"
    ))
    return {"signals": signals, "portfolio": portfolio}


# ─────────────────────────────────────────────────────────
# FULL PIPELINE: All Phases
# ─────────────────────────────────────────────────────────
def run_full_pipeline(config: dict):
    """Run all 4 active phases in sequence"""
    console.print(Panel(
        "[bold cyan]FULL PIPELINE — All 5 Phases[/bold cyan]\n"
        "[dim]Scout → Monetize → Market Intel → Stocks[/dim]",
        style="cyan"
    ))

    # Phase 1: Scout
    config["run_monetization"] = False
    agent_result    = run_pipeline(config)
    top_opps        = agent_result.get("top_opportunities", [])
    sector_insights = agent_result.get("sector_insights", "")

    # Phase 2: Monetize
    run_monetization_step(top_opps, sector_insights)

    # Phase 3: Market Intel
    market_data = run_market_intelligence_pipeline()

    # Phase 4: Stocks
    run_stock_intelligence_pipeline()

    console.print(Panel(
        "[bold green]ALL PHASES COMPLETE[/bold green]\n\n"
        "[dim]Check ./reports for all saved files\n"
        "Run: python dashboard/run_dashboard.py for the web UI[/dim]",
        style="green"
    ))


# ─────────────────────────────────────────────────────────
# Scheduled runner
# ─────────────────────────────────────────────────────────
def _safe_pipeline(config: dict):
    """Run one scan, never letting an error kill the 24/7 loop."""
    try:
        run_pipeline(config)
    except Exception as e:
        console.print(f"[red]⚠️ Scan failed (will retry next cycle): {e}[/red]")


def run_scheduled(config: dict):
    interval = config.get("scan_interval_hours", 6)
    console.print(f"[bold green]24/7 mode: scanning every {interval} hours[/bold green]")
    console.print("[dim]Only NEW opportunities trigger a Telegram alert. Press Ctrl+C to stop.[/dim]\n")

    _safe_pipeline(config)  # run immediately on start
    schedule.every(interval).hours.do(_safe_pipeline, config=config)

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped by user.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Scheduler error (continuing): {e}[/red]")
            time.sleep(30)


# ─────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────
def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Opportunity Scout — India Infrastructure Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run Phase 1 (scout tenders)
  python main.py --market           # Run Phase 3 (market intel)
  python main.py --stocks           # Run Phase 4 (stock signals)
  python main.py --monetize         # Run Phase 2 (monetization)
  python main.py --full             # Run all phases
  python main.py --search "solar"   # Search tender database
  python main.py --dashboard        # Revenue dashboard
  python main.py --portfolio        # Paper trading portfolio
  python main.py --schedule         # Run every 6 hours
  python dashboard/run_dashboard.py # Phase 5: Web UI
        """
    )

    parser.add_argument("--schedule",  action="store_true", help="Run on schedule (every 6 hrs)")
    parser.add_argument("--test",      action="store_true", help="Test with mock data")
    parser.add_argument("--search",    type=str,            help="Semantic search over tender database")
    parser.add_argument("--monetize",  action="store_true", help="Phase 2: Publish channel + leads + newsletter")
    parser.add_argument("--dashboard", action="store_true", help="Show revenue dashboard in terminal")
    parser.add_argument("--leads",     action="store_true", help="Generate contractor leads only")
    parser.add_argument("--market",    action="store_true", help="Phase 3: Market intelligence agent")
    parser.add_argument("--stocks",    action="store_true", help="Phase 4: Stock signals + paper trades")
    parser.add_argument("--portfolio", action="store_true", help="Show paper trading portfolio")
    parser.add_argument("--invest",    action="store_true", help="Suggest Indian stocks to invest for profit (+Telegram)")
    parser.add_argument("--monitor",   action="store_true", help="Monitor invested stocks; alert to SELL on loss / book profit")
    parser.add_argument("--listen",    action="store_true", help="Run interactive Telegram command bot (/latest, /invest, etc.)")
    parser.add_argument("--full",      action="store_true", help="Run ALL phases in sequence")

    args   = parser.parse_args()
    config = load_config()

    console.print(
        f"[dim]Sectors: {', '.join(config['target_sectors'][:3])}... | "
        f"States: {', '.join(config['target_states'][:2])}...[/dim]\n"
    )

    # ── Route to correct pipeline ──────────────────────────
    if args.search:
        memory  = OpportunityMemory("./data/chroma_db")
        results = memory.search_opportunities(args.search)
        console.print(f"\n[bold]Search Results for: '{args.search}'[/bold]")
        for i, r in enumerate(results[:5], 1):
            meta = r.get("metadata", {})
            console.print(f"\n{i}. [bold]{meta.get('title', 'N/A')}[/bold]")
            console.print(f"   Score: {r.get('relevance_score')}% | {meta.get('value','')} | {meta.get('source','')}")

    elif args.dashboard:
        RevenueDashboard().display()

    elif args.portfolio:
        executor    = TradingSignalExecutor()
        portfolio   = executor.get_portfolio()
        open_trades = executor.get_open_trades()
        StockDashboard().display_portfolio(portfolio, open_trades)

    elif args.leads:
        scraped     = run_all_scrapers(config)
        all_tenders = scraped.get("tenders", []) + scraped.get("gem_bids", [])
        run_lead_generation(all_tenders)

    elif args.monetize:
        run_monetization_pipeline()

    elif args.market:
        run_market_intelligence_pipeline()

    elif args.stocks:
        run_stock_intelligence_pipeline()

    elif args.invest:
        run_investment_recommendations(top_n=6)

    elif args.monitor:
        run_investment_monitor()

    elif args.listen:
        from notifier.telegram_listener import run_listener
        run_listener()

    elif args.full:
        run_full_pipeline(config)

    elif args.schedule:
        run_scheduled(config)

    else:
        # Default: Phase 1
        run_pipeline(config, use_mock=args.test)


if __name__ == "__main__":
    main()
