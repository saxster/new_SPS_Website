import os
import datetime
import random
import re
from news_miner import NewsMiner

class ConsensusEngine:
    def __init__(self):
        self.models = ["Gemini Pro", "Claude 3 Opus", "GPT-4"]
        self.sector_context = {
            "Industrial": "Factories Act 1948, PSARA 2005",
            "Cyber": "DPDP Act 2023, IT Act 2000, CERT-In Directions",
            "Healthcare": "NABH Standards, Code Violet",
            "Banking": "RBI Master Directions, IS 1550"
        }

    def process_pipeline(self, signal):
        """
        The Full Editorial Pipeline:
        Signal -> Editor (Filter) -> Analyst (Thesis) -> Red Team (Antithesis) -> Strategist (Synthesis)
        """
        print(f"\n--- [PIPELINE START] Signal: {signal['title'][:50]}... ---")

        # Step 0: The Editor (Gatekeeper)
        editorial_verdict = self._agent_editor(signal)
        if not editorial_verdict['approved']:
            print(f"  [EDITOR] REJECTED: {editorial_verdict['reason']}")
            return None
        
        print(f"  [EDITOR] APPROVED: {editorial_verdict['reason']} (Score: {editorial_verdict['score']})")

        # Step 1: Thesis
        thesis = self._agent_analyst(signal)
        
        # Step 2: Antithesis
        antithesis = self._agent_red_team(thesis, signal)
        
        # Step 3: Synthesis
        final_report = self._agent_strategist(thesis, antithesis, signal, editorial_verdict)
        
        return final_report

    def _agent_editor(self, signal):
        """
        Role: Editor-in-Chief. Decides newsworthiness.
        Criteria: Strategic Impact, Regulatory Relevance, Dot-Connecting Potential.
        """
        score = 0
        reasons = []
        
        # High Impact / Regulatory Keywords
        high_impact_terms = ["breach", "fire", "explosion", "rbi", "sebi", "fine", "arrest", "policy", "act", "shutdown", "compliance", "law", "scam", "fraud", "ransomware", "malware", "sabotage", "leak", "vulnerability"]
        # Trend / Dot-Connecting Keywords
        trend_terms = ["syndicate", "pattern", "systemic", "nationwide", "series", "nexus", "linked", "across", "multiple", "surge", "evolution"]
        
        title_lower = signal['title'].lower()
        summary_lower = signal['summary'].lower()

        # 1. Base Impact Score
        if any(x in title_lower for x in high_impact_terms):
            score += 40
            reasons.append("High strategic keywords")
        
        # 2. Sector Weight
        if signal['sector'] in ["Cyber", "Banking", "Industrial"]:
            score += 20
            reasons.append(f"Critical sector ({signal['sector']})")

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
        return {
            "focus": "Strategic Impact",
            "content": f"The incident regarding '{signal['title']}' indicates a systemic risk in the {signal['sector']} sector. This event should not be viewed in isolation; it correlates with an evolving risk profile in {signal['location']} and signals a maturation of threats targeting Indian infrastructure."
        }

    def _agent_red_team(self, thesis, signal):
        context = self.sector_context.get(signal['sector'], "General Liability Laws")
        return {
            "challenge": "Regulatory & Legal Blindspots",
            "content": f"The analysis must explicitly address the **{context}**. Most commentators will focus on the immediate loss, but the long-term risk is the 'Compliance Debt' this exposes. Failure to maintain 'Process Integrity' is a direct path to criminal negligence charges for the leadership."
        }

    def _agent_strategist(self, thesis, antithesis, signal, editorial_data):
        content = f"""
## The Signal
{signal['summary']}

## Strategic Synthesis: Connecting the Dots
This incident is a symptom of a larger, often overlooked trend in the {signal['sector']} sector. While the media reports the immediate event, the hidden meaning lies in the **convergence of {signal['sector']} vulnerabilities with systemic operational oversight.** 

**The Macro View**: We are seeing a "Dot-Connecting" pattern where {signal.get('pattern', 'Operational Failures')} are increasingly exploited by organized syndicates rather than lone actors. This shifts the risk from "Unfortunate Accident" to "Strategic Targeted Attack."

**Editor's Note**: This event was promoted by the SPS Editorial Engine (Score: {editorial_data['score']}) because it provides a clear window into {editorial_data['reason']}.

## Regulatory Implications & The Hidden Risk
{antithesis['content']}

## Operational Recommendations for Leadership
1. **Trend Check**: Map this incident against your own internal logs for the last 18 months to identify 'Micro-Patterns'.
2. **Structural Defense**: Move beyond point-solutions; implement a "Zero Trust" architecture that assumes the vendor or perimeter is already compromised.
"""
        return {
            "title": f"Strategic Briefing: {signal['title']}",
            "body": content,
            "confidence": 90 + int(editorial_data['score'] / 10),
            "sector": signal['sector'],
            "url": signal['url'],
            "severity": "Critical" if editorial_data['score'] > 80 else "High"
        }


    def generate_markdown(self, report, filename):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        md_content = f"""---
title: \"{report['title']}\"\npubDate: {date_str}\nseverity: \"{report['severity']}\"\nsector: \"{report['sector']}\"\ntags: [\"{report['sector']}\", \"Intelligence\", \"Strategic Risk\"]\nsource_urls: [\"{report['url']}\"]\nanalysis_engine: \"SPS Consensus Engine v1.1 (Editor-Enabled)\"\nconsensus_score: {report['confidence']}\ndraft: false
---

{report['body']}
"""
        with open(filename, "w") as f:
            f.write(md_content)
        print(f"--- [OUTPUT] File written: {filename} ---")

if __name__ == "__main__":
    engine = ConsensusEngine()
    miner = NewsMiner()
    
    output_dir = "website/src/content/intelligence"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    signals = miner.fetch_signals()
    
    for i, signal in enumerate(signals):
        safe_title = re.sub(r'[^a-zA-Z0-9]', '-', signal['title']).lower()[:50]
        filename = f"{safe_title}-{i}.md"
        filepath = os.path.join(output_dir, filename)
        
        report = engine.process_pipeline(signal)
        
        if report:
            engine.generate_markdown(report, filepath)