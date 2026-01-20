# Workflow: Deploy Content (Authoritative)

This workflow governs the creation and publication of content on the SPS Security Platform.

## Phase 1: Preparation (The Draft)
1. **Draft Content**: Write article in Markdown/JSON.
2. **Review Voice**: Ensure tone matches `.agent/rules/CONTENT_VOICE.md`.

## Phase 2: Intelligence (The Audit)
Run the following Skills from the repo root:

### 1. Adversarial Fact Check
Verify standard facts, regulations, and costs.
```bash
python3 .agent/skills/fact_checker/validate_article.py --file <path_to_draft>
```
> **Gate**: Must return `DECISION: PUBLISH` (Standard) or `REVIEW` (require human sign-off).

### 2. SEO Audit & Auto-Fix
Ensure technical compliance. The agent can auto-generate missing tags.
```bash
.agent/venv/bin/python .agent/skills/audit_seo.py website/src/pages --fix
```
> **Gate**: Zero violations allowed.

### 3. Design Verification
If creating new layouts/components, ensure Janus compliance.
```bash
.agent/venv/bin/python .agent/skills/verify_design.py website/src
```
> **Gate**: Zero violations allowed.

## Phase 3: Publication
1. **Commit**: `git commit -m "feat(content): Title of Article"`
2. **Push**: Trigger CI/CD pipeline.
