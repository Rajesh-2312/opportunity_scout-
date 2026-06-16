"""
dashboard/run_dashboard.py
One-command launcher: starts API server + serves dashboard HTML
Usage: python dashboard/run_dashboard.py
"""
import os, sys, uvicorn
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.staticfiles import StaticFiles
from dashboard.api_server import app

STATIC = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC, exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Opportunity Scout — Full System Dashboard")
    print("="*55)
    print("  Dashboard: http://localhost:8000")
    print("  API Docs:  http://localhost:8000/docs")
    print("  Stop:      Ctrl+C")
    print("="*55 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
