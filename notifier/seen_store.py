"""
notifier/seen_store.py
Persistent tracker of opportunities we have ALREADY notified about,
so the system only sends a Telegram alert when a *new* opportunity appears.

Dedup is based on a stable content signature (normalized title + source),
NOT the tender id — scraped/mock ids change on every run.
"""

import os
import re
import json
import hashlib
from datetime import datetime
from typing import List, Dict
from rich.console import Console

console = Console()


class SeenStore:
    def __init__(self, path: str = "./data/notified.json"):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.seen: Dict[str, Dict] = self._load()

    def _load(self) -> Dict[str, Dict]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.seen, f, indent=2, ensure_ascii=False)

    @staticmethod
    def signature(opp: Dict) -> str:
        """Stable fingerprint for an opportunity: normalized title + source."""
        title = re.sub(r"\s+", " ", str(opp.get("title", "")).strip().lower())
        source = str(opp.get("source", "")).strip().lower()
        raw = f"{title}|{source}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]

    def is_new(self, opp: Dict) -> bool:
        return bool(opp.get("title")) and self.signature(opp) not in self.seen

    def filter_new(self, opps: List[Dict]) -> List[Dict]:
        """Return only opportunities not seen before (dedup within batch too)."""
        out, batch_sigs = [], set()
        for o in opps:
            sig = self.signature(o)
            if self.is_new(o) and sig not in batch_sigs:
                out.append(o)
                batch_sigs.add(sig)
        return out

    def mark(self, opps: List[Dict]):
        ts = datetime.now().isoformat(timespec="seconds")
        for o in opps:
            if o.get("title"):
                self.seen[self.signature(o)] = {
                    "title": str(o.get("title", ""))[:140],
                    "source": str(o.get("source", "")),
                    "score": o.get("total_score", 0),
                    "first_seen": ts,
                }
        self._save()

    def count(self) -> int:
        return len(self.seen)
