"""Explainable local job matching; no external AI calls."""
import re
from datetime import datetime, timezone


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.]+", (text or "").lower()))


def score_job(job: dict, cfg: dict) -> dict:
    title = job.get("title", "")
    company = job.get("company", "")
    description = job.get("description", "")
    location = job.get("location", "")
    full_text = " ".join([title, company, description, location]).lower()
    tokens = _tokens(full_text)
    matched = []
    for skill in cfg.get("skills", []):
        skill_tokens = _tokens(skill)
        if skill.strip() and (skill.lower() in full_text or (skill_tokens and skill_tokens.issubset(tokens))):
            matched.append(skill)
    excluded = [word for word in cfg.get("exclude_keywords", []) if word.lower() in full_text]
    title_tokens = _tokens(title)
    role_match = any(_tokens(k) & title_tokens for k in cfg.get("keywords", []))
    location_match = any(loc.lower() in location.lower() for loc in cfg.get("locations", []) if loc.lower() != "remote") or "remote" in location.lower()
    # Phrase-based match contributes a small boost for each core role/skill signal.
    # Keep scoring explainable and bounded; exclusion terms always force a zero.
    score = min(60, len(matched) * 10) + (25 if role_match else 0) + (10 if location_match else 0)
    if excluded:
        score = 0
    job["match_score"] = min(100, score)
    job["matched_skills"] = ", ".join(matched)
    job["excluded_reasons"] = ", ".join(excluded)
    job["matched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return job
