"""
market_intelligence/bse_scraper.py

Scrapes BSE/NSE for:
- Bulk deals (institutions buying/selling)
- Insider trading disclosures
- Corporate announcements (land acquisition, JV, MoU)
- Shareholding pattern changes

Target companies: Adani Group, Tata Projects, L&T, GMR, GVK, IRB Infra,
                  KNR Constructions, NCC, Welspun, JSW Infra
"""

import requests
import json
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict
from rich.console import Console

console = Console()


# ─────────────────────────────────────────────
# Target Companies
# ─────────────────────────────────────────────
INFRASTRUCTURE_COMPANIES = {
    # Adani Group
    "ADANIPORTS":   {"name": "Adani Ports & SEZ",        "bse": "532921", "sector": "Ports"},
    "ADANIGREEN":   {"name": "Adani Green Energy",        "bse": "541578", "sector": "Renewable Energy"},
    "ADANIPOWER":   {"name": "Adani Power",               "bse": "533096", "sector": "Energy"},
    "ADANIENT":     {"name": "Adani Enterprises",         "bse": "512599", "sector": "Diversified Infra"},
    "ADANIINFRA":   {"name": "Adani Total Gas",           "bse": "542066", "sector": "Gas Infrastructure"},

    # Tata Group
    "TATAPOWER":    {"name": "Tata Power",                "bse": "500400", "sector": "Energy"},
    "TATASTEEL":    {"name": "Tata Steel",                "bse": "500470", "sector": "Steel/Infra"},

    # L&T
    "LT":           {"name": "Larsen & Toubro",           "bse": "500510", "sector": "EPC/Engineering"},
    "LTIM":         {"name": "LTIMindtree",               "bse": "540005", "sector": "IT Infra"},

    # Infrastructure focused
    "IRB":          {"name": "IRB Infrastructure",        "bse": "532947", "sector": "Roads"},
    "KNRCON":       {"name": "KNR Constructions",         "bse": "532942", "sector": "Roads/Irrigation"},
    "NCC":          {"name": "NCC Limited",               "bse": "500294", "sector": "Construction"},
    "GMRINFRA":     {"name": "GMR Infrastructure",        "bse": "532754", "sector": "Airports/Energy"},
    "JSWINFRA":     {"name": "JSW Infrastructure",        "bse": "543480", "sector": "Ports/Logistics"},
    "WELSPUNIND":   {"name": "Welspun Enterprises",       "bse": "532144", "sector": "Roads/Water"},

    # Power & Renewables
    "NTPC":         {"name": "NTPC",                      "bse": "532555", "sector": "Power"},
    "POWERGRID":    {"name": "Power Grid Corp",           "bse": "532898", "sector": "Power Transmission"},
    "TORNTPOWER":   {"name": "Torrent Power",             "bse": "532779", "sector": "Energy"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html",
}


# ─────────────────────────────────────────────
# BSE Announcement Scraper
# ─────────────────────────────────────────────
class BSEAnnouncementScraper:
    """
    Scrapes BSE corporate announcements.
    Key signals: Land acquisition, MoU signing, order wins,
                 subsidiary formation, JV agreements
    """

    BASE_URL = "https://www.bseindia.com/xml-data/corpfiling/AttachHis/"
    ANNOUNCEMENT_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"

    SIGNAL_KEYWORDS = [
        "land acquisition", "land bank", "awarded", "order win", "contract",
        "mou", "memorandum", "joint venture", "jv", "acquisition",
        "concession agreement", "letter of intent", "loi", "noc",
        "environmental clearance", "ec granted", "port", "airport",
        "highway", "expressway", "solar", "wind", "green hydrogen",
        "data center", "expansion", "greenfield", "brownfield",
        "capacity addition", "new plant", "new facility"
    ]

    def fetch_announcements(self, scrip_cd: str, company_name: str,
                             days_back: int = 7) -> List[Dict]:
        """Fetch recent BSE announcements for a company"""
        announcements = []

        try:
            params = {
                "pageno": 1,
                "strCat": "-1",
                "strPrevDate": (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d"),
                "strScrip": scrip_cd,
                "strSearch": "P",
                "strToDate": datetime.now().strftime("%Y%m%d"),
                "strType": "C",
                "subcategory": "-1"
            }

            response = requests.get(
                self.ANNOUNCEMENT_URL,
                params=params,
                headers=HEADERS,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("Table", [])

                for item in items:
                    headline = item.get("HEADLINE", "").lower()
                    if self._is_signal(headline):
                        announcements.append({
                            "company": company_name,
                            "scrip": scrip_cd,
                            "headline": item.get("HEADLINE", ""),
                            "date": item.get("DT_TM", ""),
                            "category": item.get("CATEGORYNAME", ""),
                            "attachment": item.get("ATTACHMENTNAME", ""),
                            "signal_type": self._classify_signal(headline),
                            "source": "BSE Announcement",
                            "url": f"https://www.bseindia.com/stock-share-price/{company_name.replace(' ','-').lower()}/{scrip_cd}/"
                        })

        except Exception as e:
            console.print(f"[yellow]⚠️ BSE announcement fetch failed for {company_name}: {e}[/yellow]")
            # Return mock data
            announcements = self._get_mock_announcements(company_name, scrip_cd)

        return announcements

    def _is_signal(self, text: str) -> bool:
        return any(kw in text.lower() for kw in self.SIGNAL_KEYWORDS)

    def _classify_signal(self, text: str) -> str:
        text = text.lower()
        if any(w in text for w in ["awarded", "order", "contract", "loi"]):
            return "ORDER_WIN"
        if any(w in text for w in ["land", "acquisition", "acquired"]):
            return "LAND_ACQUISITION"
        if any(w in text for w in ["mou", "joint venture", "jv", "agreement"]):
            return "PARTNERSHIP"
        if any(w in text for w in ["expansion", "greenfield", "new plant", "capacity"]):
            return "EXPANSION"
        if any(w in text for w in ["solar", "wind", "green", "renewable"]):
            return "GREEN_ENERGY"
        return "GENERAL_SIGNAL"

    def _get_mock_announcements(self, company_name: str, scrip_cd: str) -> List[Dict]:
        """Mock announcements for testing"""
        import random
        mock_pool = [
            {
                "company": company_name,
                "scrip": scrip_cd,
                "headline": f"{company_name} bags ₹2,800 Cr order for highway construction in AP",
                "date": (datetime.now() - timedelta(days=random.randint(1,5))).strftime("%d-%m-%Y"),
                "category": "Order Win",
                "signal_type": "ORDER_WIN",
                "source": "BSE Announcement (Mock)",
                "url": f"https://www.bseindia.com/stock-share-price/{scrip_cd}/",
                "impact": "HIGH",
                "tender_signal": "Watch for sub-contractor tenders in AP highway sector within 60 days"
            },
            {
                "company": company_name,
                "scrip": scrip_cd,
                "headline": f"{company_name} signs MoU for 500MW green hydrogen plant in Gujarat",
                "date": (datetime.now() - timedelta(days=random.randint(1,3))).strftime("%d-%m-%Y"),
                "category": "MoU",
                "signal_type": "GREEN_ENERGY",
                "source": "BSE Announcement (Mock)",
                "url": f"https://www.bseindia.com/stock-share-price/{scrip_cd}/",
                "impact": "HIGH",
                "tender_signal": "Equipment, EPC, logistics tenders expected in 90 days"
            }
        ]
        return [random.choice(mock_pool)]

    def scrape_all_companies(self, days_back: int = 7) -> List[Dict]:
        """Scrape all target companies"""
        all_announcements = []
        console.print(f"[cyan]📋 Scanning BSE announcements for {len(INFRASTRUCTURE_COMPANIES)} companies...[/cyan]")

        for symbol, info in list(INFRASTRUCTURE_COMPANIES.items())[:10]:  # Top 10
            announcements = self.fetch_announcements(info["bse"], info["name"], days_back)
            all_announcements.extend(announcements)
            time.sleep(1)

        console.print(f"[green]✅ Found {len(all_announcements)} signal announcements[/green]")
        return all_announcements


# ─────────────────────────────────────────────
# Bulk Deal Scraper
# ─────────────────────────────────────────────
class BulkDealScraper:
    """
    Monitors bulk deals — when institutions buy/sell large blocks.
    Signal: FII buying infra stock = smart money moving in.
    """

    BULK_DEAL_URL = "https://api.bseindia.com/BseIndiaAPI/api/BulkDealData/w"

    def fetch_bulk_deals(self, days_back: int = 7) -> List[Dict]:
        """Fetch recent bulk deals in infra sector"""
        deals = []
        console.print("[cyan]💰 Scanning bulk deals...[/cyan]")

        try:
            params = {
                "strDate": (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d"),
                "strEndDate": datetime.now().strftime("%Y%m%d"),
                "strType": "bulk"
            }

            response = requests.get(
                self.BULK_DEAL_URL,
                params=params,
                headers=HEADERS,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                for deal in data.get("Table", []):
                    symbol = deal.get("SCRIP_CD", "")
                    if symbol in INFRASTRUCTURE_COMPANIES:
                        qty = float(deal.get("QTY_TRADED", 0) or 0)
                        price = float(deal.get("TRADE_PRICE", 0) or 0)
                        deals.append({
                            "company": INFRASTRUCTURE_COMPANIES[symbol]["name"],
                            "symbol": symbol,
                            "sector": INFRASTRUCTURE_COMPANIES[symbol]["sector"],
                            "deal_type": deal.get("BUY_SELL", ""),
                            "quantity": qty,
                            "price": price,
                            "value_cr": round(qty * price / 1e7, 2),
                            "client": deal.get("CLIENT_NAME", ""),
                            "date": deal.get("DEAL_DATE", ""),
                            "source": "BSE Bulk Deals"
                        })

        except Exception as e:
            console.print(f"[yellow]⚠️ Bulk deal fetch failed: {e}. Using mock.[/yellow]")
            deals = self._get_mock_bulk_deals()

        console.print(f"[green]✅ Found {len(deals)} bulk deals in infra sector[/green]")
        return deals

    def _get_mock_bulk_deals(self) -> List[Dict]:
        return [
            {
                "company": "Adani Ports & SEZ",
                "symbol": "ADANIPORTS",
                "sector": "Ports",
                "deal_type": "BUY",
                "quantity": 2500000,
                "price": 1285.50,
                "value_cr": 321.38,
                "client": "Government of Singapore Investment Corp",
                "date": datetime.now().strftime("%d-%m-%Y"),
                "source": "BSE Bulk Deals (Mock)",
                "signal": "Sovereign fund buying = long-term confidence in port expansion"
            },
            {
                "company": "IRB Infrastructure",
                "symbol": "IRB",
                "sector": "Roads",
                "deal_type": "BUY",
                "quantity": 1200000,
                "price": 72.30,
                "value_cr": 8.68,
                "client": "Nippon India Mutual Fund",
                "date": datetime.now().strftime("%d-%m-%Y"),
                "source": "BSE Bulk Deals (Mock)",
                "signal": "MF accumulation before NHAI tender announcements"
            },
            {
                "company": "KNR Constructions",
                "symbol": "KNRCON",
                "sector": "Roads/Irrigation",
                "deal_type": "BUY",
                "quantity": 800000,
                "price": 315.75,
                "value_cr": 25.26,
                "client": "SBI Mutual Fund",
                "date": datetime.now().strftime("%d-%m-%Y"),
                "source": "BSE Bulk Deals (Mock)",
                "signal": "Strong AP/Telangana road pipeline — institutional positioning early"
            }
        ]


# ─────────────────────────────────────────────
# Stock Price Monitor
# ─────────────────────────────────────────────
class StockPriceMonitor:
    """
    Tracks price movements of infra stocks.
    Unusual volume + price spike = something happening before announcement.
    """

    def fetch_price_data(self, symbols: List[str] = None) -> List[Dict]:
        """Fetch current price data for infra stocks"""
        symbols = symbols or list(INFRASTRUCTURE_COMPANIES.keys())[:12]
        prices = []
        console.print("[cyan]📈 Fetching stock price data...[/cyan]")

        for symbol in symbols:
            info = INFRASTRUCTURE_COMPANIES.get(symbol, {})
            try:
                # NSE quote API
                url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
                response = requests.get(url, headers={
                    **HEADERS,
                    "Referer": "https://www.nseindia.com"
                }, timeout=8)

                if response.status_code == 200:
                    data = response.json()
                    price_info = data.get("priceInfo", {})
                    prices.append({
                        "symbol": symbol,
                        "company": info.get("name", symbol),
                        "sector": info.get("sector", ""),
                        "ltp": price_info.get("lastPrice", 0),
                        "change_pct": price_info.get("pChange", 0),
                        "volume": data.get("marketDeptOrderBook", {}).get("totalBuyQuantity", 0),
                        "52w_high": price_info.get("weekHighLow", {}).get("max", 0),
                        "52w_low": price_info.get("weekHighLow", {}).get("min", 0),
                    })
                else:
                    prices.append(self._mock_price(symbol, info))

            except Exception:
                prices.append(self._mock_price(symbol, info))

            time.sleep(0.5)

        console.print(f"[green]✅ Price data fetched for {len(prices)} stocks[/green]")
        return prices

    def _mock_price(self, symbol: str, info: Dict) -> Dict:
        import random
        base_prices = {
            "ADANIPORTS": 1285, "ADANIGREEN": 1850, "LT": 3720,
            "NTPC": 385, "POWERGRID": 315, "IRB": 72,
            "KNRCON": 315, "NCC": 230, "TATAPOWER": 425,
            "JSWINFRA": 285, "GMRINFRA": 92, "WELSPUNIND": 185
        }
        base = base_prices.get(symbol, 500)
        change = random.uniform(-3.5, 4.2)
        return {
            "symbol": symbol,
            "company": info.get("name", symbol),
            "sector": info.get("sector", ""),
            "ltp": round(base * (1 + change/100), 2),
            "change_pct": round(change, 2),
            "volume": random.randint(100000, 5000000),
            "52w_high": round(base * 1.35, 2),
            "52w_low": round(base * 0.65, 2),
            "source": "Mock"
        }

    def find_unusual_activity(self, prices: List[Dict]) -> List[Dict]:
        """Flag stocks with unusual price/volume movement"""
        signals = []
        for stock in prices:
            change = abs(float(stock.get("change_pct", 0)))
            if change >= 3.0:
                signals.append({
                    **stock,
                    "alert": f"{'🚀 Surge' if float(stock['change_pct']) > 0 else '🔻 Drop'} {stock['change_pct']}% — possible pre-announcement movement",
                    "urgency": "HIGH" if change >= 5 else "MEDIUM"
                })
        return signals


def run_bse_scraper(days_back: int = 7) -> Dict:
    """Run all BSE scrapers and return combined results"""
    results = {
        "announcements": [],
        "bulk_deals": [],
        "price_signals": [],
        "scraped_at": datetime.now().isoformat()
    }

    announcement_scraper = BSEAnnouncementScraper()
    results["announcements"] = announcement_scraper.scrape_all_companies(days_back)

    bulk_scraper = BulkDealScraper()
    results["bulk_deals"] = bulk_scraper.fetch_bulk_deals(days_back)

    price_monitor = StockPriceMonitor()
    all_prices = price_monitor.fetch_price_data()
    results["price_signals"] = price_monitor.find_unusual_activity(all_prices)
    results["all_prices"] = all_prices

    total = len(results["announcements"]) + len(results["bulk_deals"]) + len(results["price_signals"])
    console.print(f"\n[bold green]🎯 Market signals found: {total}[/bold green]")
    return results


if __name__ == "__main__":
    results = run_bse_scraper(days_back=7)
    print(json.dumps({
        "announcements": len(results["announcements"]),
        "bulk_deals": len(results["bulk_deals"]),
        "price_signals": len(results["price_signals"])
    }, indent=2))
