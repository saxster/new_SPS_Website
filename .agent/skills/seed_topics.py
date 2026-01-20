"""
Topic Seeder 🌱
Bootstraps the Content Brain with ~50 high-quality topics.
Runs TopicHunter across multiple distinct domains to ensure variety.
"""

import subprocess
import time

DOMAINS = [
    "AI in Physical Security",
    "Perimeter Intrusion Detection Systems (PIDS) Trends 2026",
    "Biometric Access Control Innovations India",
    "School Safety & Security Protocols India (POCSO/CBSE)",
    "Jewellery Store Security Standards (IS 550)",
    "Hospital Security Management & NBC Code 2016",
    "Corporate Security & Executive Protection India",
    "Drone Security & Counter-Drone Tech",
    "Cyber-Physical Convergence in Industrial IoT",
    "Bank Security & Cash Logistics India"
]

def seed():
    print(f"🌱 Seeding Content Brain with {len(DOMAINS)} domains...")
    
    for i, domain in enumerate(DOMAINS):
        print(f"\n[{i+1}/{len(DOMAINS)}] Hunting for: {domain}")
        try:
            subprocess.run([
                ".agent/venv/bin/python", 
                ".agent/skills/topic_hunter.py",
                "--domain", domain
            ], check=True)
            time.sleep(2) # Be nice to the API
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to seed {domain}: {e}")

    print("\n✅ Seeding Complete. Check Content Brain stats.")

if __name__ == "__main__":
    seed()
