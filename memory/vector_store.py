"""
memory/vector_store.py
ChromaDB-powered memory for storing tender opportunities and enabling semantic search
"""

import chromadb
from chromadb.config import Settings
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from rich.console import Console

console = Console()


class OpportunityMemory:
    """
    Vector memory for storing and semantically searching tender opportunities.
    Uses ChromaDB (runs 100% locally, no API needed)
    """

    def __init__(self, persist_path: str = "./data/chroma_db"):
        self.persist_path = persist_path
        self.client = chromadb.PersistentClient(path=persist_path)

        # Collections
        self.tenders_collection = self.client.get_or_create_collection(
            name="tenders",
            metadata={"hnsw:space": "cosine"}
        )
        self.news_collection = self.client.get_or_create_collection(
            name="news_intel",
            metadata={"hnsw:space": "cosine"}
        )
        self.patterns_collection = self.client.get_or_create_collection(
            name="winning_patterns",
            metadata={"hnsw:space": "cosine"}
        )

        console.print(f"[green]✅ Memory initialized at {persist_path}[/green]")

    def _generate_id(self, text: str) -> str:
        """Generate unique ID from content"""
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def store_tender(self, tender: Dict) -> str:
        """Store a tender opportunity in vector memory"""
        # Build rich text for embedding
        text = f"""
        Title: {tender.get('title', '')}
        Department: {tender.get('department', '')}
        Sector: {tender.get('sector', '')}
        Location: {tender.get('location', '')}
        Value: {tender.get('value', '')}
        Description: {tender.get('description', '')}
        Deadline: {tender.get('deadline', '')}
        """

        doc_id = tender.get("id") or self._generate_id(text)

        try:
            self.tenders_collection.upsert(
                ids=[str(doc_id)],
                documents=[text.strip()],
                metadatas=[{
                    "title": tender.get("title", "")[:200],
                    "sector": tender.get("sector", ""),
                    "value": tender.get("value", ""),
                    "deadline": tender.get("deadline", ""),
                    "source": tender.get("source", ""),
                    "url": tender.get("url", ""),
                    "location": tender.get("location", ""),
                    "stored_at": datetime.now().isoformat()
                }]
            )
            return doc_id
        except Exception as e:
            console.print(f"[yellow]⚠️ Store error: {e}[/yellow]")
            return ""

    def store_news(self, news: Dict) -> str:
        """Store news intelligence"""
        text = f"""
        Headline: {news.get('title', '')}
        Summary: {news.get('description', '')}
        Source: {news.get('source', '')}
        """

        doc_id = self._generate_id(text)

        try:
            self.news_collection.upsert(
                ids=[doc_id],
                documents=[text.strip()],
                metadatas=[{
                    "title": news.get("title", "")[:200],
                    "url": news.get("url", ""),
                    "source": news.get("source", ""),
                    "published": news.get("published", ""),
                    "stored_at": datetime.now().isoformat()
                }]
            )
            return doc_id
        except Exception as e:
            console.print(f"[yellow]⚠️ News store error: {e}[/yellow]")
            return ""

    def store_bulk(self, scraped_data: Dict) -> Dict:
        """Store all scraped data in bulk"""
        stored = {"tenders": 0, "news": 0, "bids": 0}

        for tender in scraped_data.get("tenders", []):
            if self.store_tender(tender):
                stored["tenders"] += 1

        for bid in scraped_data.get("gem_bids", []):
            if self.store_tender(bid):
                stored["bids"] += 1

        for news in scraped_data.get("news", []):
            if self.store_news(news):
                stored["news"] += 1

        console.print(f"[green]💾 Stored: {stored['tenders']} tenders, {stored['bids']} bids, {stored['news']} news[/green]")
        return stored

    def search_opportunities(self, query: str, n_results: int = 10) -> List[Dict]:
        """Semantic search across all tenders"""
        try:
            results = self.tenders_collection.query(
                query_texts=[query],
                n_results=min(n_results, self.tenders_collection.count() or 1)
            )

            opportunities = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    relevance = round((1 - distance) * 100, 1)

                    opportunities.append({
                        "content": doc,
                        "metadata": meta,
                        "relevance_score": relevance
                    })

            return sorted(opportunities, key=lambda x: x["relevance_score"], reverse=True)

        except Exception as e:
            console.print(f"[yellow]⚠️ Search error: {e}[/yellow]")
            return []

    def search_news(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search news intelligence"""
        try:
            count = self.news_collection.count()
            if count == 0:
                return []

            results = self.news_collection.query(
                query_texts=[query],
                n_results=min(n_results, count)
            )

            news_items = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    news_items.append({
                        "content": doc,
                        "metadata": meta
                    })

            return news_items

        except Exception as e:
            console.print(f"[yellow]⚠️ News search error: {e}[/yellow]")
            return []

    def get_stats(self) -> Dict:
        """Get memory statistics"""
        return {
            "total_tenders": self.tenders_collection.count(),
            "total_news": self.news_collection.count(),
            "total_patterns": self.patterns_collection.count(),
            "db_path": self.persist_path
        }

    def get_recent_tenders(self, limit: int = 20) -> List[Dict]:
        """Get most recently stored tenders"""
        try:
            count = self.tenders_collection.count()
            if count == 0:
                return []

            results = self.tenders_collection.get(
                limit=min(limit, count),
                include=["documents", "metadatas"]
            )

            tenders = []
            for i, doc in enumerate(results["documents"]):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                tenders.append({"content": doc, "metadata": meta})

            return tenders

        except Exception as e:
            console.print(f"[yellow]⚠️ Get recent error: {e}[/yellow]")
            return []


if __name__ == "__main__":
    # Test memory
    memory = OpportunityMemory("./test_db")

    # Store sample
    memory.store_tender({
        "id": "TEST-001",
        "title": "Solar Power Plant 500MW Telangana",
        "department": "TSGENCO",
        "sector": "Renewable Energy",
        "value": "₹2500 Crore",
        "location": "Telangana",
        "description": "Large scale solar power generation project",
        "deadline": "2024-12-31"
    })

    # Search
    results = memory.search_opportunities("renewable energy solar power")
    print(f"Found {len(results)} results")
    print(json.dumps(memory.get_stats(), indent=2))
