# Product Requirements Document: Autonomous Newsroom

> **Version**: 2.0
> **Date**: January 2026
> **Status**: Implemented ✅

---

## Executive Summary

The SPS GhostWriter V2 is an **autopoietic autonomous content platform** that:
1. Discovers what to write without human input
2. Researches from multiple verified sources
3. Writes articles with quality controls
4. Learns from its own performance to improve over time

---

## Problem Statement

Manual content creation is:
- Slow (hours per article)
- Inconsistent (quality varies)
- Reactive (waits for human topic selection)
- Not learning (same mistakes repeated)

---

## Solution

An autonomous system with four pillars:

### 1. Multi-Source Intelligence
- **PaperMiner**: Academic papers from arXiv (credibility: 9/10)
- **ArticleMiner**: Web articles via SerpAPI + trafilatura (6-10/10)
- **YouTubeMiner**: Video transcripts (5-7/10)

### 2. Editorial Brain (TopicProposer)
Autonomous topic discovery:
- Monitors news feeds for signals
- Identifies coverage gaps
- Scores topics by demand, timeliness, brand fit
- Proposes specific, actionable articles

### 3. Trust Enforcement
"No Single Point of Truth" principle:
- Claims require multi-source verification
- Credibility-weighted confidence scores
- Articles blocked if avg_confidence < 5.0

### 4. Autopoietic Learning
Self-improvement through feedback:
- Records article outcomes (success/failure)
- Adjusts sector/content type weights
- 80% exploitation of learned preferences
- 20% exploration of new areas
- Daily reflection on patterns

---

## Features Implemented

| Feature | Status | Notes |
|---------|--------|-------|
| YouTube transcript extraction | ✅ | Needs API key for search |
| Web article extraction | ✅ | Via trafilatura |
| arXiv paper search | ✅ | Always available |
| Miner factory | ✅ | Graceful dependency handling |
| SerpAPI integration | ✅ | Feeds URLs to ArticleMiner |
| TopicProposer | ✅ | Signal gathering + LLM extraction |
| TasteMemory | ✅ | SQLite persistence |
| TasteModel | ✅ | Reinforcement learning |
| AutonomousRunner | ✅ | Full loop orchestration |
| Trust enforcement | ✅ | Blocks low-confidence articles |
| Comprehensive tests | ✅ | 56+ tests passing |

---

## Configuration

```yaml
# Key settings in config/settings.yaml

miners:
  paper: { enabled: true }
  article: { enabled: true }
  youtube: { enabled: false }

trust:
  block_on_low_confidence: true
  min_confidence_score: 5.0

autonomous:
  interval_minutes: 60
  learning_rate: 0.1
  exploration_rate: 0.2
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Topic discovery | 5+ proposals/cycle | Logged |
| Article quality | > 75 score | EditorAgent |
| Publish rate | > 70% | TasteMemory |
| Learning convergence | Stable weights by week 4 | TasteModel |

---

## Future Enhancements

1. **Trend Analyzer**: Google Trends API integration
2. **Social Signals**: Twitter/LinkedIn monitoring
3. **Human-in-Loop**: Approval workflow for low-confidence proposals
4. **A/B Testing**: Compare article variations
5. **Multi-language**: Hindi/regional language support

---

## Dependencies

- Python 3.10+
- google-generativeai (Gemini LLM)
- trafilatura (article extraction)
- youtube-transcript-api (transcripts)
- sqlite3 (persistence)
- pydantic (settings)

---

## API Keys Required

| Key | Required | Purpose |
|-----|----------|---------|
| GOOGLE_API_KEY | Yes | Gemini LLM |
| SERPAPI_API_KEY | Yes | Web search |
| YOUTUBE_API_KEY | No | Video search |
