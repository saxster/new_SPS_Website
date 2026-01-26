import os
import datetime
import re
import json
import argparse
import sys

# boto3 is optional - only needed for R2 upload
try:
    import boto3
    from botocore.exceptions import NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    NoCredentialsError = Exception
    BOTO3_AVAILABLE = False

class ConsensusEngine:
    def __init__(self):
        self.sector_context = {
            "Industrial": "Factories Act 1948, PSARA 2005",
            "Cyber": "DPDP Act 2023, IT Act 2000, CERT-In Directions",
            "Healthcare": "NABH Standards, Code Violet",
            "Banking": "RBI Master Directions, IS 1550"
        }
        
        # R2 Configuration
        self.r2_client = None
        if BOTO3_AVAILABLE and os.getenv("R2_ACCESS_KEY"):
            self.r2_client = boto3.client(
                's3',
                endpoint_url=os.getenv("R2_ENDPOINT"),
                aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("R2_SECRET_KEY")
            )

    def upload_to_r2(self, filepath, object_name):
        """Uploads the briefing to Cloudflare R2"""
        if not self.r2_client:
            return {"status": "skipped", "message": "No R2 credentials"}
            
        try:
            bucket = os.getenv("R2_BUCKET", "sps-intel-archive")
            self.r2_client.upload_file(filepath, bucket, object_name)
            public_url = f"{os.getenv('R2_PUBLIC_URL')}/{object_name}"
            return {"status": "success", "url": public_url}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def process_pipeline(self, signal):
        """
        The Full Editorial Pipeline:
        Signal -> Editor (Filter) -> Analyst (Thesis) -> Red Team (Antithesis) -> Strategist (Synthesis)
        """
        # Step 0: The Editor (Gatekeeper)
        editorial_verdict = self._agent_editor(signal)
        if not editorial_verdict['approved']:
            return {"status": "rejected", "reason": editorial_verdict['reason']}
        
        # Step 1: Thesis
        thesis = self._agent_analyst(signal)
        
        # Step 2: Antithesis
        antithesis = self._agent_red_team(thesis, signal)
        
        # Step 3: Synthesis
        final_report = self._agent_strategist(thesis, antithesis, signal, editorial_verdict)
        
        return {"status": "approved", "report": final_report}

    def _agent_editor(self, signal):
        """
        Role: Editor-in-Chief. Decides newsworthiness.
        Criteria: Strategic Impact, Regulatory Relevance, Dot-Connecting Potential.
        """
        score = 0
        reasons = []
        
        title_lower = signal.get('title', '').lower()
        summary_lower = signal.get('summary', '').lower()
        sector = signal.get('sector', 'General')

        # High Impact / Regulatory Keywords
        high_impact_terms = ["breach", "fire", "explosion", "rbi", "sebi", "fine", "arrest", "policy", "act", "shutdown", "compliance", "law", "scam", "fraud", "ransomware", "malware", "sabotage", "leak", "vulnerability"]
        # Trend / Dot-Connecting Keywords
        trend_terms = ["syndicate", "pattern", "systemic", "nationwide", "series", "nexus", "linked", "across", "multiple", "surge", "evolution"]
        
        # 1. Base Impact Score
        if any(x in title_lower for x in high_impact_terms):
            score += 40
            reasons.append("High strategic keywords")
        
        # 2. Sector Weight
        if sector in ["Cyber", "Banking", "Industrial"]:
            score += 20
            reasons.append(f"Critical sector ({sector})")

        # 3. DOT-CONNECTING REWARD (Broad Trends)
        if any(x in title_lower or x in summary_lower for x in trend_terms):
            score += 30
            reasons.append("High dot-connecting potential (Trend Indicator)")

        # 4. Local Noise Penalty
        low_value_terms = ["theft", "robbery", "caught", "minor", "local", "individual"]
        if any(x in title_lower for x in low_value_terms) and score < 60:
            score -= 40
            reasons.append("Potential local noise")

        # Threshold
        is_approved = score >= 50
        
        return {
            "approved": is_approved,
            "score": min(100, score),
            "reason": ", ".join(reasons) if reasons else "Insufficient strategic weight"
        }

    def _agent_analyst(self, signal):
        sector = signal.get('sector', 'Unknown')
        location = signal.get('location', 'India')
        title = signal.get('title', 'Unknown Event')
        
        return {
            "focus": "Strategic Impact",
            "content": f"The incident regarding '{title}' indicates a systemic risk in the {sector} sector. This event should not be viewed in isolation; it correlates with an evolving risk profile in {location} and signals a maturation of threats targeting Indian infrastructure."
        }

    def _agent_red_team(self, thesis, signal):
        sector = signal.get('sector', 'General')
        context = self.sector_context.get(sector, "General Liability Laws")
        return {
            "challenge": "Regulatory & Legal Blindspots",
            "content": f"The analysis must explicitly address the **{context}**. Most commentators will focus on the immediate loss, but the long-term risk is the 'Compliance Debt' this exposes. Failure to maintain 'Process Integrity' is a direct path to criminal negligence charges for the leadership."
        }

    def _agent_strategist(self, thesis, antithesis, signal, editorial_data):
        sector = signal.get('sector', 'General')
        summary = signal.get('summary', 'No summary available.')
        pattern = signal.get('pattern', 'Operational Failures')
        title = signal.get('title', 'Untitled')
        url = signal.get('url', '#')

        content = f"""
## The Signal
{summary}

## Strategic Synthesis: Connecting the Dots
This incident is a symptom of a larger, often overlooked trend in the {sector} sector. While the media reports the immediate event, the hidden meaning lies in the **convergence of {sector} vulnerabilities with systemic operational oversight.** 

**The Macro View**: We are seeing a "Dot-Connecting" pattern where {pattern} are increasingly exploited by organized syndicates rather than lone actors. This shifts the risk from "Unfortunate Accident" to "Strategic Targeted Attack."

**Editor's Note**: This event was promoted by the SPS Editorial Engine (Score: {editorial_data['score']}) because it provides a clear window into {editorial_data['reason']}.

## Regulatory Implications & The Hidden Risk
{antithesis['content']}

## Operational Recommendations for Leadership
1. **Trend Check**: Map this incident against your own internal logs for the last 18 months to identify 'Micro-Patterns'.
2. **Structural Defense**: Move beyond point-solutions; implement a "Zero Trust" architecture that assumes the vendor or perimeter is already compromised.
"""
        return {
            "title": f"Strategic Briefing: {title}",
            "body": content,
            "confidence": 90 + int(editorial_data['score'] / 10),
            "sector": sector,
            "url": url,
            "severity": "Critical" if editorial_data['score'] > 80 else "High"
        }

    def generate_markdown(self, report, filename):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        md_content = f"""
---
title: \"{report['title']}\"
pubDate: {date_str}
severity: \"{report['severity']}\"
sector: \"{report['sector']}\"
tags: [\"{report['sector']}\", \"Intelligence\", \"Strategic Risk\"]
source_urls: [\"{report['url']}\"]
analysis_engine: \"SPS Consensus Engine v1.1 (Editor-Enabled)\"\nconsensus_score: {report['confidence']}
draft: false
---

{report['body']}
"""
        try:
            with open(filename, "w") as f:
                f.write(md_content)
            
            # TRIGGER UPLOAD
            upload_res = self.upload_to_r2(filename, f"briefings/{os.path.basename(filename)}")
            
            return {"status": "success", "file": filename, "archive": upload_res}
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPS Consensus Engine CLI")
    parser.add_argument("--mode", type=str, default="pipeline", choices=["pipeline", "editor"], help="Processing mode")
    parser.add_argument("--input", type=str, required=True, help="Input JSON string or file path")
    parser.add_argument("--write-md", action="store_true", help="Write output to Markdown file")
    parser.add_argument("--out-dir", type=str, default="website/src/content/intelligence", help="Output directory for MD files")

    args = parser.parse_args()
    engine = ConsensusEngine()

    # Load Input
    try:
        if os.path.exists(args.input):
            with open(args.input, 'r') as f:
                raw_input = json.load(f)
        else:
            raw_input = json.loads(args.input)
    except Exception as e:
        print(json.dumps({"error": f"Invalid input: {str(e)}"}))
        sys.exit(1)

    # Normalize Input (Handle list of signals or single signal)
    signals = raw_input if isinstance(raw_input, list) else [raw_input]
    results = []

    for signal in signals:
        if args.mode == "editor":
            res = engine._agent_editor(signal)
            results.append({**signal, "editorial": res})
        
        elif args.mode == "pipeline":
            res = engine.process_pipeline(signal)
            if res and res.get("status") == "approved":
                report = res["report"]
                results.append(report)
                
                if args.write_md:
                    safe_title = re.sub(r'[^a-zA-Z0-9]', '-', report['title']).lower()[:50]
                    # Ensure filename is unique-ish
                    filename = f"{safe_title}-{int(datetime.datetime.now().timestamp())}.md"
                    filepath = os.path.join(args.out_dir, filename)
                    
                    if not os.path.exists(args.out_dir):
                        os.makedirs(args.out_dir)
                        
                    write_status = engine.generate_markdown(report, filepath)
                    results[-1]["file_output"] = write_status

    # Output JSON for n8n
    print(json.dumps(results))
