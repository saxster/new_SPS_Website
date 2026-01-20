# Antigravity Agent Intelligence System

> "This repository is not just code; it is an intelligent operation system."

## 🧠 Brain (Rules)
Read these BEFORE starting work in their respective domains:
- **Design**: [.agent/rules/DESIGN_SYSTEM.md](rules/DESIGN_SYSTEM.md) - Janus System (Titanium).
- **SEO**: [.agent/rules/SEO_STANDARDS.md](rules/SEO_STANDARDS.md) - Meta tags & A11y.
- **Voice**: [.agent/rules/CONTENT_VOICE.md](rules/CONTENT_VOICE.md) - SPS Tone.

## 🛠️ Hands (Skills)
Use these tools to automate verification and analysis:

| Skill | Command | Description |
|-------|---------|-------------|
| **Fact Checker** | `python3 .agent/skills/fact_checker/validate_article.py` | verifies claims/costs in content. |
| **SEO Auditor** | `python3 .agent/skills/audit_seo.py [path]` | Scans frontmatter and headers. |
| **Design Police** | `python3 .agent/skills/verify_design.py [path]` | Catches prohibited classes/patterns. |

## 🔄 Protocols (Workflows)
- [Deploy Content](workflows/deploy_content.md): The checklist for publishing.

## Usage
When asked to "audit the site", run the SEO and Design skills.
When asked to "write an article", use the Voice rule and verify with Fact Checker.
