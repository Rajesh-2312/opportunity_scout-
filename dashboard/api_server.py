"""
dashboard/api_server.py
FastAPI backend powering the web dashboard.
Run: python dashboard/api_server.py  →  open http://localhost:8000
"""

import os, sys, json, glob
from datetime import datetime
from typing import Dict, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="Opportunity Scout API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

pipeline_status = {"is_running": False, "last_run": None, "current_step": "Idle"}

# ── Models ────────────────────────────────────────────────
class SearchReq(BaseModel):
    query: str
    limit: int = 10

class SubCreate(BaseModel):
    name: str
    contact: str
    tier: str = "basic"
    source: str = "manual"

class TradeClose(BaseModel):
    trade_id: str
    exit_price: float
    reason: str = "Manual"

# ── Helpers ───────────────────────────────────────────────
def load_latest() -> Dict:
    files = sorted(glob.glob("./data/pipeline_results_*.json"), reverse=True)
    if files:
        try:
            return json.load(open(files[0]))
        except:
            pass
    return {}

def save_result(result: Dict):
    os.makedirs("./data", exist_ok=True)
    fn = f"./data/pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json.dump(result, open(fn, "w"), indent=2, default=str)

# ── Overview ──────────────────────────────────────────────
@app.get("/api/overview")
def overview():
    try:
        from memory.vector_store import OpportunityMemory
        from monetization.payment_tracker import SubscriberTracker
        from stock_intelligence.paper_trader import TradingSignalExecutor
        from dotenv import load_dotenv; load_dotenv()

        mem   = OpportunityMemory("./data/chroma_db")
        track = SubscriberTracker()
        exe   = TradingSignalExecutor()
        rep   = load_latest()

        return {
            "timestamp": datetime.now().isoformat(),
            "pipeline": pipeline_status,
            "tenders": {
                "total_tracked": mem.get_stats()["total_tenders"],
                "top_opportunities": rep.get("top_opportunities", [])[:5],
                "sector_insights": rep.get("sector_insights", "")
            },
            "market": {
                "early_warnings": rep.get("early_warnings", [])[:4],
                "bulk_deals": rep.get("bulk_deals", [])[:3],
            },
            "stocks": {
                "signals": rep.get("stock_signals", [])[:8],
                "portfolio": exe.get_portfolio(),
                "open_trades": exe.get_open_trades()
            },
            "revenue": {
                **track.get_metrics(),
                "subscribers": track.data["subscribers"][-10:]
            }
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}

# ── Tenders ───────────────────────────────────────────────
@app.get("/api/tenders")
def get_tenders(limit: int = 20):
    from memory.vector_store import OpportunityMemory
    mem = OpportunityMemory("./data/chroma_db")
    return {"tenders": mem.get_recent_tenders(limit)}

@app.post("/api/tenders/search")
def search(req: SearchReq):
    from memory.vector_store import OpportunityMemory
    mem = OpportunityMemory("./data/chroma_db")
    return {"results": mem.search_opportunities(req.query, req.limit)}

# ── Market ─────────────────────────────────────────────────
@app.get("/api/market/warnings")
def warnings():
    rep = load_latest()
    return {"warnings": rep.get("early_warnings", []), "bulk_deals": rep.get("bulk_deals", [])}

# ── Stocks ─────────────────────────────────────────────────
@app.get("/api/stocks/portfolio")
def portfolio():
    from stock_intelligence.paper_trader import TradingSignalExecutor
    exe = TradingSignalExecutor()
    return {"summary": exe.get_portfolio(), "open_trades": exe.get_open_trades(),
            "closed_trades": exe.trader.data.get("closed_trades", [])}

@app.post("/api/stocks/close")
def close(req: TradeClose):
    from stock_intelligence.paper_trader import TradingSignalExecutor
    exe = TradingSignalExecutor()
    r = exe.trader.close_trade(req.trade_id, req.exit_price, req.reason)
    if r: return {"status": "closed", "trade": r}
    raise HTTPException(404, "Trade not found")

# ── Invest (stocks to invest for profit) ──────────────────
@app.get("/api/invest/positions")
def invest_positions():
    """Live status of recommended stocks with current P/L (no Telegram)."""
    from stock_intelligence.investment_advisor import InvestmentAdvisor
    adv = InvestmentAdvisor()
    return {"positions": adv.live_status()}

@app.post("/api/invest/recommend")
def invest_recommend(bg: BackgroundTasks):
    """Generate fresh recommendations + send Telegram digest (runs in background)."""
    if pipeline_status["is_running"]:
        return {"status": "busy"}
    bg.add_task(_bg_invest_recommend)
    return {"status": "started"}

@app.post("/api/invest/monitor")
def invest_monitor():
    """Check positions now; send SELL/PROFIT Telegram alerts on threshold cross."""
    from stock_intelligence.investment_advisor import InvestmentAdvisor
    adv = InvestmentAdvisor()
    r = adv.monitor_and_alert()
    return {"sell_alerts": len(r["sell_alerts"]), "profit_alerts": len(r["profit_alerts"]),
            "checked": r["checked"]}

def _bg_invest_recommend():
    global pipeline_status
    pipeline_status["is_running"] = True
    pipeline_status["current_step"] = "Analyzing stocks to invest..."
    try:
        from stock_intelligence.investment_advisor import run_investment_recommendations
        run_investment_recommendations(top_n=6)
    except Exception as e:
        pipeline_status["current_step"] = f"Error: {e}"
    finally:
        pipeline_status["is_running"] = False
        pipeline_status["current_step"] = "Idle"

# ── Revenue ────────────────────────────────────────────────
@app.get("/api/revenue/metrics")
def revenue():
    from monetization.payment_tracker import SubscriberTracker
    t = SubscriberTracker()
    return {"metrics": t.get_metrics(), "subscribers": t.data["subscribers"]}

@app.post("/api/revenue/subscriber")
def add_sub(sub: SubCreate):
    from monetization.payment_tracker import SubscriberTracker
    t = SubscriberTracker()
    r = t.add_subscriber(sub.name, sub.contact, sub.tier, sub.source)
    return {"status": "added", "subscriber": r}

# ── Pipeline ───────────────────────────────────────────────
@app.post("/api/pipeline/run")
def run(bg: BackgroundTasks, mode: str = "scout"):
    if pipeline_status["is_running"]:
        return {"status": "already_running"}
    bg.add_task(_bg_run, mode)
    return {"status": "started", "mode": mode}

@app.get("/api/pipeline/status")
def status():
    return pipeline_status

@app.get("/api/setup/status")
def setup():
    from dotenv import load_dotenv; load_dotenv()
    def ok(k, bad): return bool(os.getenv(k) and os.getenv(k) != bad)
    return {
        "nvidia_api_key": ok("NVIDIA_API_KEY","your_nvidia_api_key_here"),
        "telegram_bot": ok("TELEGRAM_BOT_TOKEN","your_telegram_bot_token_here"),
        "telegram_channel": ok("TELEGRAM_CHANNEL_ID","@your_channel_here"),
        "razorpay": ok("RAZORPAY_PAYMENT_LINK","https://razorpay.me/your-link"),
        "chroma_db": os.path.exists("./data/chroma_db"),
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

def _bg_run(mode: str):
    global pipeline_status
    pipeline_status["is_running"] = True
    try:
        from scrapers.tender_scraper import run_all_scrapers
        from memory.vector_store import OpportunityMemory
        from agents.scout_agent import run_scout_agent
        from dotenv import load_dotenv; load_dotenv()

        cfg = {"target_sectors": ["infrastructure","energy","ports","logistics","airports","green hydrogen"],
               "target_states": ["Telangana","Andhra Pradesh"]}
        result = {}

        if mode in ["scout","full"]:
            pipeline_status["current_step"] = "Scraping tenders..."
            scraped = run_all_scrapers(cfg)
            mem = OpportunityMemory("./data/chroma_db")
            mem.store_bulk(scraped)
            pipeline_status["current_step"] = "AI analyzing..."
            ar = run_scout_agent(scraped)
            result.update({"top_opportunities": ar.get("top_opportunities",[]),
                           "sector_insights": ar.get("sector_insights","")})

        if mode in ["market","full"]:
            pipeline_status["current_step"] = "Scanning BSE..."
            from market_intelligence.bse_scraper import run_bse_scraper
            from market_intelligence.intelligence_agent import run_market_agent
            bse = run_bse_scraper(7)
            mr  = run_market_agent(bse)
            result.update({"early_warnings": mr.get("early_warnings",[]),
                           "predictions": mr.get("predictions",[]),
                           "bulk_deals": bse.get("bulk_deals",[])})

        if mode in ["stocks","full"]:
            pipeline_status["current_step"] = "Stock signals..."
            from stock_intelligence.signal_detector import SignalDetector
            from stock_intelligence.paper_trader import run_paper_trading
            from market_intelligence.bse_scraper import StockPriceMonitor
            det = SignalDetector()
            sigs = det.detect_from_tenders(result.get("top_opportunities",[]))
            prices = StockPriceMonitor().fetch_price_data()
            tr = run_paper_trading(sigs, prices)
            result.update({"stock_signals": sigs, "portfolio": tr.get("portfolio",{})})

        save_result(result)
        pipeline_status["last_run"] = datetime.now().isoformat()
    except Exception as e:
        pipeline_status["current_step"] = f"Error: {e}"
    finally:
        pipeline_status["is_running"] = False
        pipeline_status["current_step"] = "Idle"

if __name__ == "__main__":
    print("\n🚀 Opportunity Scout API  →  http://localhost:8000")
    print("📚 API Docs              →  http://localhost:8000/docs\n")
    uvicorn.run("dashboard.api_server:app", host="0.0.0.0", port=8000, reload=True)
