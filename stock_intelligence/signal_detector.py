"""
stock_intelligence/signal_detector.py

Converts tender intelligence into stock market signals.

The Logic:
  Tender awarded to company → Revenue increase → Stock goes up
  
  But we want to PREDICT before announcement, not react after.
  
  Signal chain:
    Tender published → Company bids → Award expected in 30-60 days
    ↓
    Buy stock NOW → Award announced → Stock pops → Sell
  
  Better signal chain (Phase 3 output feeds this):
    BSE filing: "Company won order" → Sub-contractor tenders incoming
    ↓
    Buy sub-contractor stocks → Tenders confirmed → Stocks rise

Tracks: Direct beneficiaries + indirect (material suppliers, logistics)
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict
from rich.console import Console

console = Console()

# ─────────────────────────────────────────────
# Tender → Stock Beneficiary Map
# ─────────────────────────────────────────────

TENDER_STOCK_MAP = {
    # If this sector/keyword appears in tender...
    "solar": {
        "direct": [
            {"symbol": "ADANIGREEN",  "name": "Adani Green Energy",    "reason": "Largest solar developer in India"},
            {"symbol": "TATAPOWER",   "name": "Tata Power",            "reason": "Major solar EPC player"},
            {"symbol": "SJVN",        "name": "SJVN Ltd",              "reason": "PSU solar developer"},
        ],
        "indirect": [
            {"symbol": "WAAREEENER",  "name": "Waaree Energies",       "reason": "Solar panel manufacturer"},
            {"symbol": "PREMIERENE",  "name": "Premier Energies",      "reason": "Solar cell & module maker"},
            {"symbol": "INSOLATION",  "name": "Insolation Energy",     "reason": "Solar panel supplier"},
        ],
        "material": [
            {"symbol": "JINDALSTEL",  "name": "Jindal Steel",          "reason": "Steel for mounting structures"},
        ]
    },
    "port": {
        "direct": [
            {"symbol": "ADANIPORTS",  "name": "Adani Ports & SEZ",     "reason": "Largest private port operator"},
            {"symbol": "JSWINFRA",    "name": "JSW Infrastructure",    "reason": "Port developer & operator"},
            {"symbol": "ESAFEIND",    "name": "Essar Ports",           "reason": "Port operator"},
        ],
        "indirect": [
            {"symbol": "CONCOR",      "name": "Container Corp India",  "reason": "Container logistics"},
            {"symbol": "GATEWAY",     "name": "Gateway Distriparks",   "reason": "Port logistics"},
        ],
        "material": [
            {"symbol": "WELSPUNIND",  "name": "Welspun Enterprises",   "reason": "Pipeline & marine infra"},
        ]
    },
    "highway": {
        "direct": [
            {"symbol": "IRB",         "name": "IRB Infrastructure",    "reason": "Largest highway BOT player"},
            {"symbol": "KNRCON",      "name": "KNR Constructions",     "reason": "Road construction specialist"},
            {"symbol": "NCC",         "name": "NCC Limited",           "reason": "Road & infra contractor"},
            {"symbol": "ASHOKA",      "name": "Ashoka Buildcon",       "reason": "Highway developer"},
        ],
        "indirect": [
            {"symbol": "ULTRACEMCO",  "name": "UltraTech Cement",     "reason": "Cement for roads"},
            {"symbol": "SHREECEM",    "name": "Shree Cement",          "reason": "Cement supplier"},
        ],
        "material": [
            {"symbol": "HINDCOPPER",  "name": "Hindustan Copper",      "reason": "Cable & wiring"},
            {"symbol": "SAIL",        "name": "SAIL",                  "reason": "Steel for bridges"},
        ]
    },
    "airport": {
        "direct": [
            {"symbol": "GMRINFRA",    "name": "GMR Infrastructure",    "reason": "Airport developer"},
            {"symbol": "ADANIENT",    "name": "Adani Enterprises",     "reason": "Airport operator via AAHL"},
        ],
        "indirect": [
            {"symbol": "INTERGLOBE",  "name": "IndiGo",                "reason": "Traffic growth beneficiary"},
            {"symbol": "SPICEJET",    "name": "SpiceJet",              "reason": "Low cost carrier beneficiary"},
        ],
        "material": [
            {"symbol": "SIEMENS",     "name": "Siemens India",         "reason": "Airport systems & automation"},
        ]
    },
    "power": {
        "direct": [
            {"symbol": "NTPC",        "name": "NTPC",                  "reason": "Largest power generator"},
            {"symbol": "POWERGRID",   "name": "Power Grid Corp",       "reason": "Transmission network"},
            {"symbol": "TATAPOWER",   "name": "Tata Power",            "reason": "Integrated power company"},
            {"symbol": "TORNTPOWER",  "name": "Torrent Power",         "reason": "Distribution utility"},
        ],
        "indirect": [
            {"symbol": "ABB",         "name": "ABB India",             "reason": "Power equipment"},
            {"symbol": "BHEL",        "name": "BHEL",                  "reason": "Power plant equipment"},
            {"symbol": "CUMMINSIND",  "name": "Cummins India",         "reason": "Generators & engines"},
        ],
        "material": [
            {"symbol": "POLYCAB",     "name": "Polycab India",         "reason": "Cables & wires"},
            {"symbol": "KEI",         "name": "KEI Industries",        "reason": "Cables for power infra"},
        ]
    },
    "green hydrogen": {
        "direct": [
            {"symbol": "ADANIGREEN",  "name": "Adani Green Energy",    "reason": "Green H2 production leader"},
            {"symbol": "NTPC",        "name": "NTPC Green",            "reason": "PSU green H2 initiative"},
            {"symbol": "RELIANCE",    "name": "Reliance Industries",   "reason": "New Energy division"},
        ],
        "indirect": [
            {"symbol": "CEAT",        "name": "CEAT Ltd",              "reason": "Specialty tyres for H2 vehicles"},
            {"symbol": "THERMAX",     "name": "Thermax Ltd",           "reason": "Heat exchangers for H2"},
        ],
        "material": []
    },
    "data center": {
        "direct": [
            {"symbol": "ADANIENT",    "name": "Adani Enterprises",     "reason": "AdaniConneX data centers"},
            {"symbol": "NXTDIGITAL",  "name": "NXT Digital",           "reason": "Digital infrastructure"},
        ],
        "indirect": [
            {"symbol": "DIXON",       "name": "Dixon Technologies",    "reason": "Electronics & servers"},
            {"symbol": "TATAELXSI",   "name": "Tata Elxsi",            "reason": "IT infrastructure services"},
        ],
        "material": [
            {"symbol": "POLYCAB",     "name": "Polycab India",         "reason": "High capacity cables"},
            {"symbol": "HAVELLS",     "name": "Havells India",         "reason": "Electrical equipment"},
        ]
    },
    "logistics": {
        "direct": [
            {"symbol": "DELHIVERY",   "name": "Delhivery",             "reason": "Logistics tech leader"},
            {"symbol": "BLUEDART",    "name": "Blue Dart Express",     "reason": "Express logistics"},
            {"symbol": "MAHLOG",      "name": "Mahindra Logistics",    "reason": "3PL provider"},
        ],
        "indirect": [
            {"symbol": "CONCOR",      "name": "Container Corp India",  "reason": "Rail logistics"},
            {"symbol": "GATEWAY",     "name": "Gateway Distriparks",   "reason": "Cold chain logistics"},
        ],
        "material": []
    }
}


class SignalDetector:
    """
    Scans tender database and market signals,
    outputs ranked buy/watch/avoid signals for stocks.
    """

    def detect_from_tenders(self, tenders: List[Dict]) -> List[Dict]:
        """
        For each tender, identify stocks that will benefit.
        Returns ranked list of stock signals.
        """
        signals = []
        console.print(f"[cyan]📡 Detecting stock signals from {len(tenders)} tenders...[/cyan]")

        for tender in tenders:
            title = tender.get("title", "").lower()
            sector = tender.get("sector", "").lower()
            value_str = tender.get("value", "0")
            score = tender.get("total_score", 5)

            # Extract tender value in crores
            value_cr = self._parse_value(value_str)

            # Match to sector map
            matched_sector = self._match_sector(title + " " + sector)
            if not matched_sector:
                continue

            beneficiaries = TENDER_STOCK_MAP.get(matched_sector, {})

            # Direct beneficiaries — stronger signal
            for stock in beneficiaries.get("direct", []):
                signals.append(self._build_signal(
                    stock, tender, matched_sector,
                    signal_type="DIRECT",
                    strength=min(10, score * 1.2),
                    value_cr=value_cr,
                    reasoning=f"Direct beneficiary — {stock['reason']}"
                ))

            # Indirect — weaker but still actionable
            for stock in beneficiaries.get("indirect", [])[:2]:
                signals.append(self._build_signal(
                    stock, tender, matched_sector,
                    signal_type="INDIRECT",
                    strength=min(10, score * 0.8),
                    value_cr=value_cr,
                    reasoning=f"Indirect beneficiary — {stock['reason']}"
                ))

        # Deduplicate and aggregate by symbol
        aggregated = self._aggregate_signals(signals)
        console.print(f"[green]✅ Generated {len(aggregated)} stock signals[/green]")
        return aggregated

    def detect_from_market_intel(self, early_warnings: List[Dict]) -> List[Dict]:
        """
        Convert market intelligence predictions into stock signals.
        Earlier warning = bigger opportunity.
        """
        signals = []
        console.print(f"[cyan]📡 Converting {len(early_warnings)} market warnings to stock signals...[/cyan]")

        for warning in early_warnings:
            title = warning.get("predicted_tender_title", "").lower()
            company = warning.get("company", "")
            timeline = warning.get("timeline_days", 60)
            opp_score = warning.get("opportunity_score", 5)

            # Earlier the signal, bigger the alpha
            time_bonus = max(0, (90 - timeline) / 90) * 2

            matched_sector = self._match_sector(title)
            if not matched_sector:
                continue

            beneficiaries = TENDER_STOCK_MAP.get(matched_sector, {})
            for stock in beneficiaries.get("direct", []):
                # If the company in the warning IS the stock — strong signal
                is_exact_match = (
                    company.split()[0].lower() in stock["name"].lower() or
                    stock["name"].split()[0].lower() in company.lower()
                )
                strength = min(10, opp_score + time_bonus + (2 if is_exact_match else 0))

                signals.append(self._build_signal(
                    stock, {"title": warning.get("predicted_tender_title", ""),
                             "sector": matched_sector,
                             "value": f"₹{warning.get('estimated_value_cr', 'TBD')} Cr",
                             "source": "Market Intelligence Prediction"},
                    matched_sector,
                    signal_type="PREDICTIVE",
                    strength=strength,
                    value_cr=warning.get("estimated_value_cr", 0),
                    reasoning=f"Pre-announcement signal — {timeline} days early. {stock['reason']}"
                ))

        aggregated = self._aggregate_signals(signals)
        console.print(f"[green]✅ {len(aggregated)} predictive stock signals[/green]")
        return aggregated

    def _build_signal(self, stock: Dict, tender: Dict, sector: str,
                       signal_type: str, strength: float,
                       value_cr: float, reasoning: str) -> Dict:
        return {
            "symbol": stock["symbol"],
            "company_name": stock["name"],
            "sector": sector,
            "signal_type": signal_type,
            "strength": round(strength, 1),
            "action": self._determine_action(strength, signal_type),
            "reasoning": reasoning,
            "tender_title": tender.get("title", "")[:80],
            "tender_value_cr": value_cr,
            "source": tender.get("source", "Tender Database"),
            "generated_at": datetime.now().isoformat(),
            "hold_days": self._estimate_hold_days(signal_type),
        }

    def _determine_action(self, strength: float, signal_type: str) -> str:
        if signal_type == "PREDICTIVE" and strength >= 8:
            return "🟢 STRONG BUY — Pre-announcement alpha"
        elif strength >= 8:
            return "🟢 BUY — Strong direct beneficiary"
        elif strength >= 6:
            return "🟡 WATCH — Add on dips"
        elif strength >= 4:
            return "⬜ MONITOR — Weak signal"
        return "🔴 AVOID — Insufficient signal"

    def _estimate_hold_days(self, signal_type: str) -> int:
        return {"PREDICTIVE": 90, "DIRECT": 60, "INDIRECT": 30}.get(signal_type, 45)

    def _match_sector(self, text: str) -> str:
        text = text.lower()
        sector_keywords = {
            "solar":        ["solar", "photovoltaic", "pv plant"],
            "port":         ["port", "jetty", "berth", "harbour", "maritime"],
            "highway":      ["highway", "road", "expressway", "nhai", "bridge"],
            "airport":      ["airport", "aviation", "airstrip", "aai", "udan"],
            "power":        ["power", "electricity", "thermal", "hydro", "substation"],
            "green hydrogen": ["green hydrogen", "hydrogen", "electrolyser"],
            "data center":  ["data center", "datacenter", "cloud infra", "server"],
            "logistics":    ["logistics", "warehouse", "cold chain", "3pl", "freight"],
        }
        for sector, keywords in sector_keywords.items():
            if any(kw in text for kw in keywords):
                return sector
        return ""

    def _parse_value(self, value_str: str) -> float:
        import re
        nums = re.findall(r"[\d,]+\.?\d*", str(value_str).replace(",", ""))
        if nums:
            val = float(nums[0])
            if "lakh" in value_str.lower():
                return val / 100
            return val
        return 0.0

    def _aggregate_signals(self, signals: List[Dict]) -> List[Dict]:
        """Merge signals for same stock, boost strength if multiple sources"""
        aggregated = {}
        for sig in signals:
            sym = sig["symbol"]
            if sym not in aggregated:
                aggregated[sym] = {**sig, "source_count": 1, "tenders": [sig["tender_title"]]}
            else:
                existing = aggregated[sym]
                existing["strength"] = min(10, existing["strength"] + sig["strength"] * 0.3)
                existing["source_count"] += 1
                existing["tenders"].append(sig["tender_title"])
                # Upgrade to stronger signal type
                type_rank = {"PREDICTIVE": 3, "DIRECT": 2, "INDIRECT": 1}
                if type_rank.get(sig["signal_type"], 0) > type_rank.get(existing["signal_type"], 0):
                    existing["signal_type"] = sig["signal_type"]
                existing["action"] = self._determine_action(
                    existing["strength"], existing["signal_type"]
                )

        result = list(aggregated.values())
        result.sort(key=lambda x: x["strength"], reverse=True)
        return result


if __name__ == "__main__":
    mock_tenders = [
        {"title": "500MW Solar Power Plant", "sector": "renewable energy",
         "value": "₹2500 Crore", "total_score": 9.0, "source": "CPPP"},
        {"title": "Greenfield Port Development Vizag", "sector": "ports",
         "value": "₹8000 Crore", "total_score": 8.5, "source": "CPPP"},
    ]
    detector = SignalDetector()
    signals = detector.detect_from_tenders(mock_tenders)
    for s in signals[:5]:
        print(f"{s['symbol']:15} {s['action']:30} Score:{s['strength']} | {s['reasoning'][:50]}")
