import logging
import structlog
import sys
import os
import warnings
from typing import Dict

EVENT_LABELS = {
    "activating_ghostwriter": "Start GhostWriter",
    "pipeline_start": "Pipeline Start",
    "pipeline_summary": "Pipeline Summary",
    "starting_research": "Research: Fetching sources",
    "creating_outline": "Outline: Building structure",
    "writing_draft": "Draft: Writing",
    "reviewing_draft": "Review: Editing",
    "stage_done": "Stage Done",
    "stage_complete": "Stage Complete",
    "stage_failed": "Stage Failed",
    "quality_gate_failed": "Quality Gate",
    "citation_gate_failed": "Citation Gate",
    "claim_ledger_issues": "Claim Ledger",
}

LEVEL_ICON = {
    "INFO": "ℹ️ ",
    "WARNING": "⚠️ ",
    "ERROR": "❌ ",
    "CRITICAL": "❌ ",
}


_printed_table_header = False


def _render_pretty(event_dict: Dict) -> str:
    timestamp = event_dict.pop("timestamp", "")
    level = str(event_dict.pop("level", "info")).upper()
    event = event_dict.pop("event", "")
    label = EVENT_LABELS.get(event, event.replace("_", " ").title())
    icon = LEVEL_ICON.get(level, "")

    key_order = ["stage", "topic", "status", "file", "evidence", "length", "score", "issues", "error", "reason", "duration_s"]
    ordered_parts = []
    for key in key_order:
        if key in event_dict:
            ordered_parts.append(f"{key}={event_dict.pop(key)}")

    for key in sorted(event_dict.keys()):
        ordered_parts.append(f"{key}={event_dict[key]}")

    extras = " | ".join(ordered_parts).strip()
    base = f"{timestamp} {icon}{label}".strip()
    if extras:
        return f"{base}\n    {extras}"
    return base


def _render_table(event_dict: Dict) -> str:
    global _printed_table_header
    timestamp = event_dict.pop("timestamp", "")
    level = str(event_dict.pop("level", "info")).upper()
    event = event_dict.pop("event", "")
    label = EVENT_LABELS.get(event, event.replace("_", " ").title())

    key_order = ["stage", "topic", "status", "file", "evidence", "length", "score", "issues", "error", "reason", "duration_s"]
    ordered_parts = []
    for key in key_order:
        if key in event_dict:
            ordered_parts.append(f"{key}={event_dict.pop(key)}")
    for key in sorted(event_dict.keys()):
        ordered_parts.append(f"{key}={event_dict[key]}")
    details = " | ".join(ordered_parts).strip()

    time_col = f"{timestamp:>8}"
    level_col = f"{level:<7}"
    event_col = f"{label:<28}"
    details_col = details

    header = ""
    if not _printed_table_header:
        _printed_table_header = True
        header = (
            f"{'TIME':>8} {'LEVEL':<7} {'EVENT':<28} DETAILS\n"
            f"{'-'*8} {'-'*7} {'-'*28} {'-'*60}"
        )

    line = f"{time_col} {level_col} {event_col} {details_col}".rstrip()
    return f"{header}\n{line}" if header else line


def _render_event(_, __, event_dict: Dict) -> str:
    fmt = os.getenv("LOG_FORMAT", "table").lower()
    if fmt == "pretty":
        return _render_pretty(event_dict)
    return _render_table(event_dict)


def setup_logging(log_level=logging.INFO):
    """Configures structured logging with compact, readable output."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            _render_event,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redirect standard library logging and suppress noisy libs
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)
    for noisy in ["google", "google.genai", "google.api_core", "httpx", "httpcore", "urllib3"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", message="Pydantic serializer warnings.*")

def get_logger(name: str):
    return structlog.get_logger(name)
