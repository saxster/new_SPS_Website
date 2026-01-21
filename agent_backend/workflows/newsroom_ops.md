# Workflow: Newsroom Operations

## The "Drop & Go" Publishing Pipeline

We have implemented an **Automated Newsroom** that watches the `drafts/` folder.

### How to Publish
1.  **Create a Draft**: Create a JSON file in `drafts/` (e.g., `drafts/new_alert.json`).
    ```json
    {
      "title": "New PSARA Guidelines 2026",
      "summary": "The Ministry has updated uniform regulations...",
      "regulations": ["PSARA Act 2005", "Annexure B"],
      "costs": "Zero if compliant",
      "topic": "compliance"
    }
    ```
2.  **Wait**: The Agent Watcher (`newsroom_watcher.py`) sees the file.
3.  **Validation**:
    - It runs the **Adversarial Fact Checker**.
    - **IF PASS**: It converts the JSON to Markdown and saves it to `website/src/content/blog/`.
    - **IF FAIL**: It moves the file to `drafts/failed_checks/` and generates a report.

### Starting the Watcher
Run this in a dedicated terminal:
```bash
source .agent/venv/bin/activate
python .agent/skills/newsroom_watcher.py
```
