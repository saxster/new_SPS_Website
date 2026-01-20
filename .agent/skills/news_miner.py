import urllib.request
import xml.etree.ElementTree as ET
import datetime
import ssl
import re

class NewsMiner:
    def __init__(self):
        self.sources = [
            {
                "name": "Google News - Cyber India",
                "url": "https://news.google.com/rss/search?q=cybersecurity+breach+india+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
                "sector": "Cyber"
            },
            {
                "name": "Google News - Industrial India",
                "url": "https://news.google.com/rss/search?q=factory+fire+accident+india+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
                "sector": "Industrial"
            },
            {
                "name": "Google News - Banking Fraud",
                "url": "https://news.google.com/rss/search?q=bank+fraud+rbi+penalty+india+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
                "sector": "Banking"
            }
        ]
        # Ignore generic crime or irrelevant noise
        self.ignore_keywords = ["cricket", "movie", "gossip", "politics", "election"]

    def clean_html(self, raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    def fetch_signals(self):
        signals = []
        print("--- [MINER] Starting Patrol... ---")
        
        # SSL Context to avoid cert errors in some environments
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for source in self.sources:
            print(f"--- Scanning Sector: {source['sector']} via {source['name']} ---")
            try:
                with urllib.request.urlopen(source['url'], context=ctx, timeout=10) as response:
                    xml_data = response.read()
                    root = ET.fromstring(xml_data)
                    
                    # Parse RSS Items
                    # Structure: channel -> item -> title, link, pubDate, description
                    count = 0
                    for item in root.findall('./channel/item'):
                        if count >= 2: # Limit to top 2 per source to avoid flood
                            break
                            
                        title = item.find('title').text
                        link = item.find('link').text
                        pub_date = item.find('pubDate').text
                        description = self.clean_html(item.find('description').text) if item.find('description') is not None else ""

                        # Quality Filter
                        if any(keyword in title.lower() for keyword in self.ignore_keywords):
                            continue

                        # Construct Signal Object
                        signal = {
                            "title": title,
                            "summary": description[:200] + "...", # Truncate for analysis
                            "url": link,
                            "published_at": pub_date,
                            "source_name": source['name'],
                            "sector": source['sector'],
                            "location": "India (Derived)", # Placeholder
                            "pattern": "Emerging Threat" # Placeholder for Analyst to refine
                        }
                        
                        signals.append(signal)
                        count += 1
                        print(f"  > Signal Detected: {title[:50]}...")

            except Exception as e:
                print(f"  [ERROR] Failed to fetch {source['name']}: {e}")
                # Fallback Mock Signal for Demo purposes if network fails
                print("  [FALLBACK] Generating Synthetic Signal for demo.")
                signals.append({
                    "title": f"Simulated: Critical Infrastructure Alert in {source['sector']}",
                    "summary": "This is a synthetic signal generated because the RSS feed could not be reached. Real-world impact analysis required.",
                    "url": "https://example.com",
                    "published_at": datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                    "source_name": "SPS Synthetic Stream",
                    "sector": source['sector'],
                    "location": "Mumbai/Delhi",
                    "pattern": "Synthetic Data Injection"
                })

        print(f"--- [MINER] Patrol Complete. {len(signals)} signals collected. ---")
        return signals

if __name__ == "__main__":
    miner = NewsMiner()
    data = miner.fetch_signals()
    # print(data)