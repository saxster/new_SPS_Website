# SPS GhostWriter V2: Autonomous Newsroom

> An autopoietic content intelligence platform that discovers topics, researches from multiple sources, writes articles with trust verification, and learns from its own performance.

---

## 🧠 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   AUTONOMOUS NEWSROOM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────┐    ┌───────────────┐    ┌──────────────┐       │
│   │  SIGNALS  │───▶│ TopicProposer │───▶│ ContentBrain │       │
│   │  (News)   │    │  (Editorial)  │    │ (Topic Queue)│       │
│   └───────────┘    └───────────────┘    └──────┬───────┘       │
│                                                 │               │
│   ┌───────────┐    ┌───────────────┐    ┌──────▼───────┐       │
│   │  MINERS   │───▶│ ResearchAgent │───▶│ GhostWriter  │       │
│   │ (Multi)   │    │  (Evidence)   │    │  (Write)     │       │
│   └───────────┘    └───────────────┘    └──────┬───────┘       │
│                                                 │               │
│   ┌───────────┐    ┌───────────────┐    ┌──────▼───────┐       │
│   │  TASTE    │◀───│ TasteModel    │◀───│ FeedbackLoop │       │
│   │ (Memory)  │    │  (Learning)   │    │  (Observe)   │       │
│   └───────────┘    └───────────────┘    └──────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

```bash
# 1. Setup
cd agent_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure (.env)
cp .env.example .env
# Add: GOOGLE_API_KEY, SERPAPI_API_KEY

# 3. Run Autonomous Newsroom
python cli/autonomous_runner.py --dry-run --cycles 1
```

---

## 📦 Components

### Multi-Source Miners
Extract evidence from multiple sources with credibility weighting.

| Miner | Source | Credibility | Status |
|-------|--------|-------------|--------|
| PaperMiner | arXiv API | 9 (peer-reviewed) | ✅ |
| ArticleMiner | Web articles | 6-10 (by domain) | ✅ |
| YouTubeMiner | Transcripts | 5-7 | ⚠️ Needs API key |

### TopicProposer (Editorial Brain)
Discovers what to write autonomously:
- Gathers signals from news, trends, and coverage gaps
- Uses LLM to extract specific, actionable topics
- Scores by timeliness, demand, coverage gap, brand fit

### Trust Enforcement
"No Single Point of Truth" principle:
- Claims require multi-source verification
- Articles with avg_confidence < 5.0 are **blocked**
- ClaimLedger tracks source credibility

### Autopoietic Learning
System improves over time:
- **TasteMemory**: Persistent storage for feedback
- **TasteModel**: Adjusts weights based on success/failure
- **Reflection**: Periodic LLM analysis of patterns

---

## 🛠️ CLI Commands

```bash
# Discover topics
python skills/agents/topic_proposer.py --discover

# Run autonomous loop (dry-run)
python cli/autonomous_runner.py --dry-run --cycles 3

# Run forever
python cli/autonomous_runner.py

# Reflect on performance
python cli/autonomous_runner.py --reflect

# Run tests
python -m pytest tests/ -v
```

---

## 📁 Project Structure

```
agent_backend/
├── cli/
│   └── autonomous_runner.py    # Main orchestration loop
├── config/
│   ├── manager.py              # Pydantic settings
│   └── settings.yaml           # Configuration
├── skills/
│   ├── agents/
│   │   ├── topic_proposer.py   # Editorial Brain
│   │   ├── researcher.py       # Evidence gathering
│   │   ├── writer.py           # Article drafting
│   │   └── editor.py           # Quality review
│   ├── miners/
│   │   ├── base_miner.py       # Abstract interface
│   │   ├── youtube_miner.py    # YouTube transcripts
│   │   ├── article_miner.py    # Web articles
│   │   ├── paper_miner.py      # arXiv papers
│   │   └── miner_factory.py    # Factory with deps
│   ├── ghost_writer.py         # Main orchestrator
│   ├── claim_ledger.py         # Trust verification
│   ├── taste_memory.py         # Persistent learning
│   └── taste_model.py          # Weight adjustment
├── tests/
│   ├── test_miners.py          # Miner tests
│   └── test_autopoietic.py     # Learning system tests
└── .env.example                # API key template
```

---

## ⚙️ Configuration

```yaml
# config/settings.yaml

# Multi-source miners
miners:
  paper:
    enabled: true
  article:
    enabled: true
  youtube:
    enabled: false  # Needs YOUTUBE_API_KEY

# Trust enforcement
trust:
  block_on_low_confidence: true
  min_confidence_score: 5.0

# Autonomous runner
autonomous:
  interval_minutes: 60
  learning_rate: 0.1
  exploration_rate: 0.2
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suite
python -m pytest tests/test_autopoietic.py -v
python -m pytest tests/test_miners.py -v
```

---

## 📊 How Taste Develops

```
Week 1: Exploration
  All sectors = 1.0x weight

Week 2-4: Calibration
  cybersecurity: 1.0 → 1.1 → 1.21 (success)
  fire_safety: 1.0 → 0.9 → 0.81 (failures)

Month 2+: Refined Taste
  Strong preferences established
  20% exploration to avoid stagnation
```

---

## 📜 License

Proprietary - SPS Security Solutions
