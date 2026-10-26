"""Parse job card / detail fields from Naukri pages (resilient heuristics)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from .models import JobListing


def parse_experience(text: str | None) -> tuple[float | None, float | None]:
    if not text:
        return None, None
    t = text.replace("–", "-").replace("—", "-")
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", t)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+", t)
    if m:
        return float(m.group(1)), None
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    if m:
        v = float(m.group(1))
        return v, v
    return None, None


def parse_salary_lpa(text: str | None) -> tuple[float | None, float | None]:
    if not text:
        return None, None
    t = text.lower().replace(",", "")
    # e.g. 10-15 Lacs PA, 12 LPA, Not disclosed
    if "not disclosed" in t or "unpaid" in t:
        return None, None
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac|lpa)", t)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|lpa)", t)
    if m:
        v = float(m.group(1))
        return v, v
    return None, None


def parse_posted_hours(text: str | None) -> float | None:
    if not text:
        return None
    t = text.lower().strip()
    if "just now" in t or "today" in t:
        return 1.0
    if "yesterday" in t:
        return 24.0
    m = re.search(r"(\d+)\s*(minute|min)", t)
    if m:
        return float(m.group(1)) / 60.0
    m = re.search(r"(\d+)\s*hour", t)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*day", t)
    if m:
        return float(m.group(1)) * 24.0
    m = re.search(r"(\d+)\s*week", t)
    if m:
        return float(m.group(1)) * 24.0 * 7
    return None


def parse_applicants(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"(\d+)\s*applicant", text.lower())
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)", text)
    if m and "applicant" in text.lower():
        return int(m.group(1))
    return None


def job_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    if not parts:
        return url
    last = parts[-1]
    # often job-id is numeric suffix
    m = re.search(r"(\d{6,})$", last)
    if m:
        return m.group(1)
    return last


def listing_from_card(data: dict[str, Any], source_query: str | None = None) -> JobListing:
    """Build JobListing from a pre-extracted card dict (title, href, etc.)."""
    url = data.get("url") or data.get("href") or ""
    title = (data.get("title") or "").strip()
    exp_text = data.get("experience")
    sal_text = data.get("salary")
    exp_min, exp_max = parse_experience(exp_text)
    sal_min, sal_max = parse_salary_lpa(sal_text)
    return JobListing(
        job_id=data.get("job_id") or job_id_from_url(url),
        title=title,
        company=data.get("company"),
        location=data.get("location"),
        experience_text=exp_text,
        experience_min=exp_min,
        experience_max=exp_max,
        salary_text=sal_text,
        salary_min_lpa=sal_min,
        salary_max_lpa=sal_max,
        skills=data.get("skills") or [],
        posted_text=data.get("posted"),
        posted_hours_ago=parse_posted_hours(data.get("posted")),
        applicants=parse_applicants(data.get("applicants")),
        url=url,
        description_snippet=data.get("snippet"),
        application_type=data.get("application_type"),
        source_query=source_query,
    )
