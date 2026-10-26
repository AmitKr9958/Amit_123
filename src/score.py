"""Deterministic relevance & eligibility scoring."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .config import Preferences
from .models import JobListing, ScoreBreakdown, ScoredJob


def _norm(text: str | None) -> str:
    return (text or "").lower().strip()


def _contains_any(text: str, keywords: Iterable[str]) -> list[str]:
    t = _norm(text)
    return [k for k in keywords if _norm(k) in t]


def _title_score(title: str, prefs: Preferences) -> tuple[float, list[str]]:
    t = _norm(title)
    reasons: list[str] = []
    for role in prefs.roles.primary:
        if _norm(role) in t:
            reasons.append(f"Primary role match: {role}")
            return 1.0, reasons
    for role in prefs.roles.secondary:
        if _norm(role) in t:
            reasons.append(f"Secondary role match: {role}")
            return 0.7, reasons
    tokens = set(re.findall(r"[a-z0-9]+", t))
    primary_tokens: set[str] = set()
    for role in prefs.roles.primary:
        primary_tokens.update(re.findall(r"[a-z0-9]+", _norm(role)))
    overlap = tokens & primary_tokens
    if len(overlap) >= 2:
        reasons.append(f"Partial title overlap: {sorted(overlap)}")
        return 0.45, reasons
    reasons.append("Weak or no title match")
    return 0.1, reasons


def _skills_score(job: JobListing, prefs: Preferences) -> tuple[float, list[str], list[str]]:
    blob = " ".join(
        [job.title or "", job.description_snippet or "", " ".join(job.skills or [])]
    )
    must = _contains_any(blob, prefs.skills.must_have_any)
    strong = _contains_any(blob, prefs.skills.strong)
    nice = _contains_any(blob, prefs.skills.nice_to_have)
    reasons: list[str] = []
    missing: list[str] = []
    if must:
        reasons.append(f"Must-have skills present: {must}")
        base = 0.7
    else:
        missing.extend(prefs.skills.must_have_any[:3])
        reasons.append("No must-have Power BI / DAX / Power Query signal")
        base = 0.2
    if strong:
        reasons.append(f"Strong skills: {strong}")
        base = min(1.0, base + 0.2)
    if nice:
        base = min(1.0, base + 0.1)
    return base, reasons, missing


def _experience_score(job: JobListing, prefs: Preferences) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    exclusions: list[str] = []
    my_rel = prefs.profile.relevant_experience_years
    my_total = prefs.profile.total_experience_years
    title = _norm(job.title)
    for kw in prefs.exclude.title_keywords:
        if _norm(kw) in title:
            exclusions.append(f"Excluded title keyword: {kw}")
            return 0.0, reasons, exclusions

    exp_min, exp_max = job.experience_min, job.experience_max
    if exp_min is None and exp_max is None and job.experience_text:
        m = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)",
            job.experience_text,
        )
        if m:
            exp_min, exp_max = float(m.group(1)), float(m.group(2))
        else:
            m2 = re.search(
                r"(\d+(?:\.\d+)?)\s*\+?\s*(?:yrs?|years?)",
                _norm(job.experience_text),
            )
            if m2:
                exp_min = float(m2.group(1))

    if exp_max is not None and exp_max < prefs.exclude.experience_max_years and my_rel >= 8:
        exclusions.append(f"Experience ceiling too low ({exp_max} yrs) for ~{my_rel} yrs profile")
        return 0.0, reasons, exclusions
    if exp_min is not None and my_total < exp_min - 1:
        exclusions.append(f"Below minimum experience ({exp_min}+ yrs)")
        return 0.15, reasons, exclusions
    if exp_min is not None and exp_max is not None:
        if exp_min <= my_rel <= exp_max + 1:
            reasons.append(f"Experience fit: {exp_min}-{exp_max} vs yours ~{my_rel}")
            return 1.0, reasons, exclusions
        if my_rel >= exp_min:
            reasons.append("At or above minimum experience")
            return 0.75, reasons, exclusions
        return 0.3, reasons, exclusions
    reasons.append("Experience range not disclosed")
    return 0.55, reasons, exclusions


def _location_score(job: JobListing, prefs: Preferences) -> tuple[float, list[str]]:
    loc = _norm(job.location)
    reasons: list[str] = []
    if not loc:
        reasons.append("Location unknown")
        return 0.0, reasons

    # Explicit remote/WFH listings can be considered even if an office city is
    # also displayed. "Hybrid" alone is not remote and does not override city.
    remote_tokens = ("remote", "work from home", "wfh", "work-from-home")
    if any(token in loc for token in remote_tokens):
        if prefs.profile.allow_remote:
            reasons.append("Remote work explicitly stated in location")
            return 0.85, reasons
        reasons.append("Remote work is disabled by config")
        return 0.0, reasons

    preferred = [_norm(x) for x in prefs.profile.preferred_locations if _norm(x)]
    # Split multi-location labels before matching. A substring match against
    # "Delhi" must not accept a mixed label such as "Hybrid - Pune, Delhi".
    segments = re.split(r"\s*(?:,|/|\||;|\s[-–—]\s)\s*", loc)
    neutral_modes = re.compile(r"\b(?:hybrid|onsite|on-site|office|india)\b", re.I)
    segments = [neutral_modes.sub("", part).strip() for part in segments]
    segments = [part for part in segments if part]
    segment_matches = [
        any(place in segment for place in preferred) or segment in {"ncr", "delhi ncr"}
        for segment in segments
    ]
    if segment_matches and all(segment_matches):
        reasons.append("Preferred location: " + ", ".join(segments))
        return 1.0, reasons
    if any(segment_matches):
        reasons.append(f"Mixed preferred and non-preferred locations: {job.location}")
        return 0.0, reasons
    reasons.append(f"Location outside preferred set: {job.location}")
    return 0.0, reasons


def _freshness_score(job: JobListing, prefs: Preferences) -> tuple[float, list[str]]:
    hours = job.posted_hours_ago
    max_h = prefs.profile.max_posting_age_hours
    if hours is None:
        return 0.0, ["Posting age unknown; cannot verify freshness"]
    if hours <= max_h:
        return 1.0, [f"Fresh post (~{hours:.0f}h)"]
    return 0.0, [f"Stale (~{hours:.0f}h > {max_h}h maximum)"]


def _competition_score(job: JobListing, prefs: Preferences) -> tuple[float, list[str]]:
    n = job.applicants
    if n is None:
        return 0.5, ["Applicant count not shown"]
    if n <= prefs.profile.ideal_max_applicants:
        return 1.0, [f"Low competition ({n} applicants)"]
    if n <= prefs.profile.max_applicants:
        return 0.6, [f"Acceptable competition ({n})"]
    return 0.2, [f"High competition ({n})"]


def _policy_exclusions(job: JobListing, prefs: Preferences) -> list[str]:
    """Apply hard eligibility rules before a job can enter the apply queue."""
    out: list[str] = []
    company = _norm(job.company)
    for blocked in prefs.exclude.companies:
        if company and _norm(blocked) and _norm(blocked) in company:
            out.append(f"Blacklisted company: {blocked}")

    floor = prefs.profile.min_salary_lpa
    if floor and job.salary_max_lpa is not None and job.salary_max_lpa < floor:
        out.append(f"Salary ceiling {job.salary_max_lpa} LPA below minimum {floor} LPA")

    hours = job.posted_hours_ago
    if hours is None:
        out.append("Posting age unavailable; freshness cannot be verified")
    elif hours > prefs.profile.max_posting_age_hours:
        out.append(
            f"Posting age {hours:.1f}h exceeds maximum "
            f"{prefs.profile.max_posting_age_hours}h"
        )

    location_score, location_reasons = _location_score(job, prefs)
    if location_score <= 0:
        out.append("Location is unknown or outside configured preferred locations")
    return out


def score_job(job: JobListing, prefs: Preferences) -> ScoredJob:
    w = prefs.scoring.weights
    title_s, title_r = _title_score(job.title, prefs)
    skills_s, skills_r, missing = _skills_score(job, prefs)
    exp_s, exp_r, exclusions = _experience_score(job, prefs)
    exclusions.extend(_policy_exclusions(job, prefs))
    loc_s, loc_r = _location_score(job, prefs)
    fresh_s, fresh_r = _freshness_score(job, prefs)
    comp_s, comp_r = _competition_score(job, prefs)

    total = (
        title_s * w.title_match
        + skills_s * w.skills_match
        + exp_s * w.experience_fit
        + loc_s * w.location_fit
        + fresh_s * w.freshness
        + comp_s * w.competition
    )
    if exclusions:
        total = min(total, 0.25)

    breakdown = ScoreBreakdown(
        title_match=round(title_s, 3),
        skills_match=round(skills_s, 3),
        experience_fit=round(exp_s, 3),
        location_fit=round(loc_s, 3),
        freshness=round(fresh_s, 3),
        competition=round(comp_s, 3),
        total=round(total, 3),
        reasons=title_r + skills_r + exp_r + loc_r + fresh_r + comp_r,
        exclusions=exclusions,
        missing_skills=missing,
    )
    eligible = total >= prefs.scoring.min_score_to_apply and not exclusions
    return ScoredJob(job=job, score=breakdown, eligible=eligible)
