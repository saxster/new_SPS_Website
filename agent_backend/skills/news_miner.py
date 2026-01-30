import urllib.request
import xml.etree.ElementTree as ET
import datetime
import ssl
import re
import argparse
import json
import sys


class NewsMiner:
    def __init__(self):
        # Only filter entertainment/sports - allow political figures in incident context
        self.ignore_keywords = [
            "cricket",
            "movie",
            "gossip",
            "bollywood",
            "ipl",
            "celebrity",
        ]
        # Incident keywords that override ignore filter
        self.incident_keywords = [
            "crash",
            "accident",
            "fire",
            "blast",
            "explosion",
            "death",
            "killed",
            "injured",
            "attack",
            "breach",
        ]

    def clean_html(self, raw_html):
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", raw_html)
        return cleantext

    def fetch_signals(self, query=None, sector="General", limit=3):
        signals = []

        # Default security queries if none provided
        if not query:
            search_query = (
                f"cybersecurity breach OR factory fire OR bank fraud India when:24h"
            )
        else:
            search_query = f"{query} India when:24h"

        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_query)}&hl=en-IN&gl=IN&ceid=IN:en"

        # SSL Context to avoid cert errors
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            with urllib.request.urlopen(rss_url, context=ctx, timeout=15) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)

                count = 0
                for item in root.findall("./channel/item"):
                    if count >= limit:
                        break

                    title = item.find("title").text
                    link = item.find("link").text
                    pub_date = item.find("pubDate").text
                    description = (
                        self.clean_html(item.find("description").text)
                        if item.find("description") is not None
                        else ""
                    )

                    title_lower = title.lower()
                    # Skip entertainment/sports unless it's an incident
                    has_ignore = any(kw in title_lower for kw in self.ignore_keywords)
                    has_incident = any(
                        kw in title_lower for kw in self.incident_keywords
                    )
                    if has_ignore and not has_incident:
                        continue

                    signals.append(
                        {
                            "title": title,
                            "summary": description[:250] + "...",
                            "url": link,
                            "published_at": pub_date,
                            "sector": sector,
                            "query_used": search_query,
                        }
                    )
                    count += 1

        except Exception as e:
            # For n8n, we return an empty list or error object rather than crashing
            return [{"error": str(e), "status": "failed"}]

        return signals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPS News Miner CLI")
    parser.add_argument("--query", type=str, help="Specific search terms")
    parser.add_argument(
        "--sector", type=str, default="General", help="Industry vertical"
    )
    parser.add_argument("--limit", type=int, default=3, help="Max results")
    parser.add_argument("--json", action="store_true", help="Output raw JSON for n8n")

    args = parser.parse_args()

    miner = NewsMiner()
    results = miner.fetch_signals(
        query=args.query, sector=args.sector, limit=args.limit
    )

    if args.json:
        # Structured output for automation nodes
        print(json.dumps(results))
    else:
        # Human readable output
        print(
            f"--- [MINER] Mission: {args.sector} | Query: {args.query or 'Default'} ---"
        )
        for idx, s in enumerate(results):
            if "error" in s:
                print(f"  [!] FAILED: {s['error']}")
            else:
                print(f"  {idx + 1}. {s['title']}")
                print(f"     URL: {s['url']}\n")
