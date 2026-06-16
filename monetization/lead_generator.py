"""
monetization/lead_generator.py

Finds small contractors & infrastructure companies on IndiaMart/Justdial
who are missing government tenders that match their capabilities.
Generates personalised pitch emails offering your intelligence service.

Revenue model: ₹5,000–₹15,000/month per contractor client
"""

import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()


# ─────────────────────────────────────────────
# Lead Data Model
# ─────────────────────────────────────────────
class Lead:
    def __init__(self, **kwargs):
        self.company_name = kwargs.get("company_name", "")
        self.contact_person = kwargs.get("contact_person", "")
        self.email = kwargs.get("email", "")
        self.phone = kwargs.get("phone", "")
        self.business_type = kwargs.get("business_type", "")
        self.location = kwargs.get("location", "")
        self.source = kwargs.get("source", "")
        self.relevant_sectors = kwargs.get("relevant_sectors", [])
        self.matched_tenders = kwargs.get("matched_tenders", [])
        self.generated_at = datetime.now().isoformat()

    def to_dict(self):
        return self.__dict__


# ─────────────────────────────────────────────
# IndiaMart Scraper
# ─────────────────────────────────────────────
class IndiaMartScraper:
    """
    Finds contractors on IndiaMart who need tender intelligence.
    Targets: civil contractors, EPC companies, logistics firms,
             solar installers, infra consultants
    """

    BASE_URL = "https://www.indiamart.com/search.mp"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    TARGET_QUERIES = [
        "civil construction contractor Hyderabad",
        "infrastructure EPC company Telangana",
        "solar energy contractor Andhra Pradesh",
        "logistics company Hyderabad",
        "road construction contractor Vijayawada",
        "building construction Hyderabad",
        "electrical contractor government projects",
        "port logistics company Vizag",
    ]

    def search_leads(self, query: str, max_results: int = 10) -> List[Lead]:
        """Search IndiaMart for potential leads"""
        leads = []
        console.print(f"[cyan]🔍 Searching IndiaMart: {query}[/cyan]")

        try:
            params = {"ss": query, "prdsrc": 1}
            response = requests.get(
                self.BASE_URL, params=params,
                headers=self.HEADERS, timeout=15
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")

                # IndiaMart company cards
                cards = soup.find_all("div", class_=["p-card-wrpr", "prod-info"])

                for card in cards[:max_results]:
                    company = card.find(["h2", "a"], class_=["lcname", "company-name"])
                    location_elem = card.find("span", class_=["lctgry", "location"])

                    if company:
                        lead = Lead(
                            company_name=company.get_text(strip=True),
                            location=location_elem.get_text(strip=True) if location_elem else "India",
                            business_type=query.split(" ")[0],
                            source="IndiaMart",
                            relevant_sectors=self._detect_sectors(query)
                        )
                        leads.append(lead)

            console.print(f"[green]✅ Found {len(leads)} leads for '{query}'[/green]")

        except Exception as e:
            console.print(f"[yellow]⚠️ IndiaMart scrape failed: {e}. Using mock leads.[/yellow]")
            leads = self._get_mock_leads(query)

        return leads

    def _detect_sectors(self, query: str) -> List[str]:
        query_lower = query.lower()
        sectors = []
        if any(w in query_lower for w in ["solar", "energy", "electrical"]):
            sectors.append("Renewable Energy")
        if any(w in query_lower for w in ["civil", "construction", "road", "building"]):
            sectors.append("Infrastructure")
        if any(w in query_lower for w in ["logistics", "port", "freight"]):
            sectors.append("Logistics")
        if any(w in query_lower for w in ["epc", "infrastructure"]):
            sectors.append("EPC Projects")
        return sectors or ["Infrastructure"]

    def _get_mock_leads(self, query: str) -> List[Lead]:
        """Mock leads for testing"""
        mock = [
            {
                "company_name": "Sri Venkateswara Civil Contractors",
                "contact_person": "Ravi Kumar",
                "email": "ravi@svcivil.com",
                "phone": "+91-9876543210",
                "business_type": "Civil Contractor",
                "location": "Hyderabad, Telangana",
                "source": "IndiaMart (Mock)",
                "relevant_sectors": ["Infrastructure", "Roads"]
            },
            {
                "company_name": "Andhra EPC Solutions Pvt Ltd",
                "contact_person": "Prasad Rao",
                "email": "prasad@andhraEPC.com",
                "phone": "+91-9876543211",
                "business_type": "EPC Company",
                "location": "Vijayawada, Andhra Pradesh",
                "source": "IndiaMart (Mock)",
                "relevant_sectors": ["Energy", "Infrastructure"]
            },
            {
                "company_name": "Green Power Installers",
                "contact_person": "Suresh Reddy",
                "email": "suresh@greenpowerap.com",
                "phone": "+91-9876543212",
                "business_type": "Solar Contractor",
                "location": "Vizag, Andhra Pradesh",
                "source": "IndiaMart (Mock)",
                "relevant_sectors": ["Renewable Energy", "Solar"]
            },
        ]
        return [Lead(**m) for m in mock]

    def scrape_all(self) -> List[Lead]:
        """Scrape all target queries"""
        all_leads = []
        for query in self.TARGET_QUERIES[:4]:  # Start with 4
            leads = self.search_leads(query, max_results=5)
            all_leads.extend(leads)
            time.sleep(2)

        # Deduplicate by company name
        seen = set()
        unique_leads = []
        for lead in all_leads:
            if lead.company_name not in seen:
                seen.add(lead.company_name)
                unique_leads.append(lead)

        console.print(f"[bold green]📋 Total unique leads: {len(unique_leads)}[/bold green]")
        return unique_leads


# ─────────────────────────────────────────────
# Email Generator (AI-powered)
# ─────────────────────────────────────────────
class PitchEmailGenerator:
    """
    Generates personalised pitch emails for each lead.
    Uses matching tenders to make email hyper-relevant.
    """

    def generate_email(self, lead: Lead, matching_tenders: List[Dict]) -> Dict:
        """Generate a personalised pitch email"""

        tender_lines = ""
        for i, t in enumerate(matching_tenders[:3], 1):
            tender_lines += f"\n  {i}. {t.get('title', 'N/A')[:60]} — {t.get('value', 'TBD')} ({t.get('location', 'N/A')})"

        subject = f"3 Government Tenders Matching {lead.company_name}'s Profile — This Week"

        body = f"""Dear {lead.contact_person or 'Sir/Madam'},

I came across {lead.company_name} on IndiaMart and noticed your expertise in {', '.join(lead.relevant_sectors[:2])}.

I run an AI-powered government tender intelligence service that monitors CPPP, GeM, and state portals daily. This week, I found {len(matching_tenders)} tenders that match your company's capabilities exactly:
{tender_lines}

Most contractors miss these because:
✗ They don't monitor all portals daily
✗ Tenders close before they find them
✗ They lack strategic analysis on which ones to prioritise

What I offer:
✅ Daily alerts for tenders matching YOUR business type
✅ AI analysis: which tenders have lowest competition
✅ Deadline reminders so you never miss a bid
✅ Strategic brief on how to position your bid

Investment: ₹5,000/month (less than missing one tender)

I'd like to share this week's full report with you — free, no strings attached — so you can judge the value yourself.

Shall I send it over?

Best regards,
Rajesh M.
Opportunity Scout Intelligence
📱 [Your Phone]
🔗 [Your LinkedIn]

P.S. — The ₹{matching_tenders[0].get('value', '100 Crore') if matching_tenders else '100 Crore'} tender above closes in {matching_tenders[0].get('deadline', '30 days') if matching_tenders else '30 days'}. Happy to walk you through it on a quick call."""

        return {
            "to": lead.email,
            "subject": subject,
            "body": body,
            "company": lead.company_name,
            "generated_at": datetime.now().isoformat()
        }

    def generate_bulk(self, leads: List[Lead],
                      available_tenders: List[Dict]) -> List[Dict]:
        """Generate emails for all leads, matching relevant tenders"""
        emails = []
        console.print(f"[cyan]✉️  Generating {len(leads)} pitch emails...[/cyan]")

        for lead in leads:
            # Match tenders to this lead's sectors
            matching = [
                t for t in available_tenders
                if any(
                    sector.lower() in t.get("sector", "").lower() or
                    t.get("sector", "").lower() in sector.lower()
                    for sector in lead.relevant_sectors
                )
            ]

            # If no sector match, use top 3 by score
            if not matching:
                matching = sorted(
                    available_tenders,
                    key=lambda x: x.get("total_score", 0),
                    reverse=True
                )[:3]

            lead.matched_tenders = [t.get("title", "") for t in matching[:3]]
            email = self.generate_email(lead, matching[:3])
            emails.append(email)

        console.print(f"[green]✅ Generated {len(emails)} personalised emails[/green]")
        return emails


# ─────────────────────────────────────────────
# Lead Manager — saves and tracks leads
# ─────────────────────────────────────────────
class LeadManager:
    """Saves leads and email drafts to files for manual review before sending"""

    def __init__(self, output_dir: str = "./leads"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save_leads(self, leads: List[Lead]) -> str:
        """Save leads to JSON"""
        filename = f"{self.output_dir}/leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        data = [l.to_dict() for l in leads]
        with open(filename, "w") as f:
            json.dump(data, f, indent=2, default=str)
        console.print(f"[green]💾 Leads saved: {filename}[/green]")
        return filename

    def save_emails(self, emails: List[Dict]) -> str:
        """Save email drafts for review"""
        filename = f"{self.output_dir}/email_drafts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w") as f:
            for i, email in enumerate(emails, 1):
                f.write(f"{'='*60}\n")
                f.write(f"EMAIL #{i} — {email['company']}\n")
                f.write(f"TO: {email['to']}\n")
                f.write(f"SUBJECT: {email['subject']}\n")
                f.write(f"{'─'*60}\n")
                f.write(email['body'])
                f.write(f"\n\n")

        console.print(f"[green]💾 Email drafts saved: {filename}[/green]")
        console.print("[yellow]⚠️  REVIEW EMAILS BEFORE SENDING — check leads/email_drafts_*.txt[/yellow]")
        return filename

    def get_stats(self) -> Dict:
        """Get lead generation stats"""
        import glob
        lead_files = glob.glob(f"{self.output_dir}/leads_*.json")
        email_files = glob.glob(f"{self.output_dir}/email_drafts_*.txt")

        total_leads = 0
        for f in lead_files:
            try:
                data = json.load(open(f))
                total_leads += len(data)
            except:
                pass

        return {
            "total_lead_batches": len(lead_files),
            "total_emails_generated": len(email_files),
            "estimated_leads": total_leads
        }


# ─────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────
def run_lead_generation(available_tenders: List[Dict]) -> Dict:
    """Full lead generation pipeline"""
    console.print("\n[bold magenta]💼 Starting Lead Generation Engine...[/bold magenta]\n")

    # Scrape leads
    scraper = IndiaMartScraper()
    leads = scraper.scrape_all()

    # Generate emails
    generator = PitchEmailGenerator()
    emails = generator.generate_bulk(leads, available_tenders)

    # Save everything
    manager = LeadManager()
    leads_file = manager.save_leads(leads)
    emails_file = manager.save_emails(emails)

    stats = manager.get_stats()

    console.print(f"\n[bold green]💼 Lead Generation Complete![/bold green]")
    console.print(f"   📋 Leads found: {len(leads)}")
    console.print(f"   ✉️  Emails drafted: {len(emails)}")
    console.print(f"   💰 Revenue potential: ₹{len(leads) * 5000:,}/month (if all convert)")

    return {
        "leads": [l.to_dict() for l in leads],
        "emails": emails,
        "leads_file": leads_file,
        "emails_file": emails_file,
        "stats": stats
    }


if __name__ == "__main__":
    mock_tenders = [
        {
            "title": "Solar Power Plant 500MW Telangana",
            "value": "₹2500 Crore",
            "sector": "Renewable Energy",
            "location": "Telangana",
            "deadline": "31-12-2024",
            "total_score": 9.0
        }
    ]
    result = run_lead_generation(mock_tenders)
    print(f"\nGenerated {len(result['emails'])} emails")
