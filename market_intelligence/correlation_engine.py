"""
market_intelligence/correlation_engine.py

Cross-references market signals WITH existing tender database.
Finds hidden connections:
  "Adani won order in Vizag" + "Port tender in Vizag" = SAME PROJECT
  "L&T bags highway contract" + "Highway civil works tender" = SUB-OPPORTUNITY

Also builds a learning database of patterns that proved correct.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Tuple
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

PATTERNS_FILE = "./data/proven_patterns.json"


class CorrelationEngine:
    """
    Links corporate signals to tender opportunities.
    Learns which predictions came true over time.
    """

    def __init__(self):
        self.proven_patterns = self._load_patterns()

    def _load_patterns(self) -> List[Dict]:
        if os.path.exists(PATTERNS_FILE):
            with open(PATTERNS_FILE) as f:
                return json.load(f)
        return []

    def _save_patterns(self):
        os.makedirs("./data", exist_ok=True)
        with open(PATTERNS_FILE, "w") as f:
            json.dump(self.proven_patterns, f, indent=2, default=str)

    def correlate(self, predictions: List[Dict],
                  existing_tenders: List[Dict]) -> List[Dict]:
        """
        Find predictions that match existing tenders —
        confirms signal accuracy and reveals deeper opportunity.
        """
        correlations = []
        console.print("[cyan]🔗 Correlating market signals with tender database...[/cyan]")

        for pred in predictions:
            pred_title = pred.get("predicted_tender_title", "").lower()
            pred_company = pred.get("company", "").lower()

            for tender in existing_tenders:
                tender_title = tender.get("title", "").lower()
                tender_sector = tender.get("sector", "").lower()
                tender_location = tender.get("location", "").lower()

                # Calculate correlation score
                score, reasons = self._similarity_score(
                    pred_title, pred_company,
                    tender_title, tender_sector, tender_location
                )

                if score >= 0.4:
                    correlations.append({
                        "prediction": pred,
                        "matched_tender": tender,
                        "correlation_score": round(score, 2),
                        "match_reasons": reasons,
                        "insight": self._generate_insight(pred, tender, score),
                        "action": self._generate_action(pred, tender)
                    })

        # Sort by correlation score
        correlations.sort(key=lambda x: x["correlation_score"], reverse=True)
        console.print(f"[green]✅ Found {len(correlations)} correlations[/green]")
        return correlations

    def _similarity_score(self, pred_title: str, pred_company: str,
                           tender_title: str, tender_sector: str,
                           tender_location: str) -> Tuple[float, List[str]]:
        """Calculate how well a prediction matches a tender"""
        score = 0.0
        reasons = []

        # Keyword overlap
        pred_words = set(pred_title.split())
        tender_words = set(tender_title.split())
        common = pred_words & tender_words
        stop_words = {"the", "a", "an", "for", "of", "in", "at", "to", "and", "or"}
        meaningful = common - stop_words

        if len(meaningful) >= 3:
            score += 0.4
            reasons.append(f"Keyword match: {', '.join(list(meaningful)[:4])}")
        elif len(meaningful) >= 2:
            score += 0.2
            reasons.append(f"Partial match: {', '.join(list(meaningful)[:2])}")

        # Sector correlation
        sector_pairs = [
            (["port", "shipping", "maritime"], ["logistics", "port"]),
            (["solar", "renewable", "green"], ["energy", "renewable"]),
            (["highway", "road", "expressway"], ["roads", "infrastructure"]),
            (["airport", "aviation"], ["airports"]),
            (["power", "electricity"], ["energy", "power"]),
        ]
        for pred_kws, tender_kws in sector_pairs:
            if any(kw in pred_title for kw in pred_kws) and \
               any(kw in tender_sector for kw in tender_kws):
                score += 0.3
                reasons.append(f"Sector aligned: {tender_sector}")
                break

        # Company name in tender
        company_short = pred_company.split()[0].lower() if pred_company else ""
        if company_short and len(company_short) > 3 and company_short in tender_title:
            score += 0.2
            reasons.append(f"Company mentioned in tender")

        return score, reasons

    def _generate_insight(self, pred: Dict, tender: Dict, score: float) -> str:
        company = pred.get("company", "Company")
        tender_title = tender.get("title", "")[:60]
        if score >= 0.7:
            return (f"STRONG MATCH: {company}'s activity directly connected to "
                    f"'{tender_title}' — this is the sub-opportunity. BID NOW.")
        elif score >= 0.5:
            return (f"LIKELY MATCH: {company}'s announcement suggests "
                    f"'{tender_title}' is part of the same project ecosystem.")
        return (f"POSSIBLE CONNECTION: Monitor '{tender_title}' — "
                f"may expand as {company}'s project develops.")

    def _generate_action(self, pred: Dict, tender: Dict) -> str:
        days = pred.get("timeline_days", 60)
        value = tender.get("value", "TBD")
        deadline = tender.get("deadline", "Check portal")
        return (f"Deadline: {deadline} | Est. value: {value} | "
                f"Prepare bid in next {min(days, 21)} days. "
                f"{pred.get('action_for_small_contractor', 'Review requirements.')}")

    def record_pattern(self, prediction: Dict, actual_tender: Dict,
                       proved_correct: bool):
        """Record whether a prediction came true — builds learning database"""
        pattern = {
            "company": prediction.get("company"),
            "signal_type": prediction.get("signal_type", ""),
            "predicted": prediction.get("predicted_tender_title"),
            "actual": actual_tender.get("title", ""),
            "proved_correct": proved_correct,
            "lag_days_predicted": prediction.get("timeline_days"),
            "recorded_at": datetime.now().isoformat()
        }
        self.proven_patterns.append(pattern)
        self._save_patterns()
        console.print(f"[green]📚 Pattern recorded ({'✅' if proved_correct else '❌'})[/green]")

    def get_accuracy_stats(self) -> Dict:
        """Get prediction accuracy over time"""
        if not self.proven_patterns:
            return {"total": 0, "correct": 0, "accuracy_pct": 0}
        correct = sum(1 for p in self.proven_patterns if p.get("proved_correct"))
        return {
            "total_predictions": len(self.proven_patterns),
            "correct_predictions": correct,
            "accuracy_pct": round(correct / len(self.proven_patterns) * 100, 1),
            "patterns_by_company": self._group_by_company()
        }

    def _group_by_company(self) -> Dict:
        groups = {}
        for p in self.proven_patterns:
            company = p.get("company", "Unknown")
            if company not in groups:
                groups[company] = {"total": 0, "correct": 0}
            groups[company]["total"] += 1
            if p.get("proved_correct"):
                groups[company]["correct"] += 1
        return groups


class MarketIntelligenceReporter:
    """
    Formats market intelligence data for Telegram, newsletter, and terminal.
    """

    def format_telegram_alert(self, warning: Dict) -> str:
        return f"""🚨 <b>MARKET INTELLIGENCE ALERT</b>

{warning.get('warning_level', '🟡 HIGH')}

🏢 <b>Company:</b> {warning.get('company', 'N/A')}
📌 <b>Signal:</b> {warning.get('source_announcement', '')[:100]}

🔮 <b>Prediction:</b>
{warning.get('predicted_tender_title', 'N/A')[:100]}

💰 <b>Est. Value:</b> ₹{warning.get('estimated_value_cr', 'TBD')} Crore
⏳ <b>Expected in:</b> {warning.get('timeline_days', 60)} days
📅 <b>Prepare by:</b> {warning.get('act_by', 'ASAP')}

✅ <b>Your Action:</b>
{warning.get('action_for_small_contractor', 'Monitor closely')}

⭐ <b>Confidence:</b> {warning.get('confidence', 'MEDIUM')}
🎯 <b>Score:</b> {warning.get('opportunity_score', 'N/A')}/10"""

    def display_terminal_table(self, warnings: List[Dict], correlations: List[Dict]):
        """Rich terminal display of market intelligence"""

        # Warnings table
        if warnings:
            table = Table(
                title="🚨 Market Intelligence — Early Warnings",
                box=box.ROUNDED,
                header_style="bold red"
            )
            table.add_column("Level", width=10)
            table.add_column("Company", width=20)
            table.add_column("Predicted Tender", max_width=40)
            table.add_column("₹ Cr", width=10)
            table.add_column("Days", width=6)
            table.add_column("Score", width=6)

            for w in warnings[:6]:
                table.add_row(
                    w.get("warning_level", "🟡")[:12],
                    w.get("company", "N/A")[:20],
                    w.get("predicted_tender_title", "N/A")[:40],
                    str(w.get("estimated_value_cr", "TBD")),
                    str(w.get("timeline_days", "?")),
                    str(round(w.get("opportunity_score", 0), 1))
                )
            console.print(table)

        # Correlations table
        if correlations:
            ctable = Table(
                title="🔗 Signal ↔ Tender Correlations",
                box=box.ROUNDED,
                header_style="bold cyan"
            )
            ctable.add_column("Match %", width=8)
            ctable.add_column("Prediction", max_width=35)
            ctable.add_column("Matched Tender", max_width=35)
            ctable.add_column("Action", max_width=30)

            for c in correlations[:5]:
                ctable.add_row(
                    f"{int(c['correlation_score']*100)}%",
                    c["prediction"].get("predicted_tender_title", "")[:35],
                    c["matched_tender"].get("title", "")[:35],
                    c["action"][:30]
                )
            console.print(ctable)


def run_correlation_analysis(predictions: List[Dict],
                              existing_tenders: List[Dict],
                              early_warnings: List[Dict]) -> Dict:
    """Full correlation analysis pipeline"""
    engine = CorrelationEngine()
    reporter = MarketIntelligenceReporter()

    correlations = engine.correlate(predictions, existing_tenders)
    reporter.display_terminal_table(early_warnings, correlations)

    return {
        "correlations": correlations,
        "accuracy_stats": engine.get_accuracy_stats(),
        "telegram_alerts": [
            reporter.format_telegram_alert(w)
            for w in early_warnings[:3]
        ]
    }


if __name__ == "__main__":
    # Test
    mock_predictions = [{
        "predicted_tender_title": "Solar power plant EPC contract Telangana",
        "company": "Adani Green Energy",
        "timeline_days": 60,
        "estimated_value_cr": 800,
        "opportunity_score": 8.5,
        "confidence": "HIGH",
        "action_for_small_contractor": "Register on Adani vendor portal"
    }]
    mock_tenders = [{
        "title": "500MW Solar Power Plant Telangana",
        "sector": "Renewable Energy",
        "location": "Telangana",
        "value": "₹2500 Crore",
        "deadline": "31-12-2024"
    }]
    engine = CorrelationEngine()
    result = engine.correlate(mock_predictions, mock_tenders)
    print(f"Correlations found: {len(result)}")
    if result:
        print(result[0]["insight"])
