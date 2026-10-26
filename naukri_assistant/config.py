"""Configuration loading and validation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    path = ROOT / "config.json"
    if not path.exists():
        path = ROOT / "config.example.json"
    if not path.exists():
        raise FileNotFoundError("Missing config.json and config.example.json.")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    for key in ("keywords", "locations", "skills", "exclude_keywords"):
        if not isinstance(cfg.get(key), list):
            raise ValueError(f"Config field '{key}' must be a list.")
    for key in ("experience_min", "experience_max", "posted_within_days", "max_pages_per_search", "min_match_score"):
        if not isinstance(cfg.get(key), (int, float)):
            raise ValueError(f"Config field '{key}' must be numeric.")
    if cfg["experience_min"] > cfg["experience_max"]:
        raise ValueError("experience_min cannot exceed experience_max.")
    cfg.setdefault("salary_floor_lpa", None)
    cfg.setdefault("applicant", {})
    cfg.setdefault("browser", {})
    cfg["browser"].setdefault("headless", False)
    cfg["browser"].setdefault("channel", "chromium")
    cfg["browser"].setdefault("slow_mo_ms", 80)
    cfg["browser"].setdefault("navigation_timeout_ms", 45000)
    cfg.setdefault("limits", {})
    cfg["limits"].setdefault("max_jobs_per_run", 100)
    return cfg
