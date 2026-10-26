"""Explainable local job matching and configured hard filters. No external AI calls."""
import re
from datetime import datetime, timezone


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.]+", (text or "").lower()))


def parse_posted_days(text: str):
    text = (text or "").strip().lower()
    if not text:
        return None
    if any(item in text for item in ("just now", "minute", "hour", "today", "few")):
        return 0
    if "yesterday" in text:
        return 1
    for pattern, multiplier in ((r"(\d+)\s*\+?\s*day", 1),
                                (r"(\d+)\s*\+?\s*week", 7),
                                (r"(\d+)\s*\+?\s*month", 30)):
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)) * multiplier
    return None


def parse_experience_range(text: str):
    values = [int(value) for value in re.findall(r"\d+", text or "")]
    if not values:
        return None
    low = values[0]
    if len(values) > 1:
        return low, values[-1]
    if "+" in (text or ""):
        return low, 99
    return low, low


def parse_salary_range(text: str):
    """Return (min_lpa, max_lpa) only when the listing explicitly uses LPA/lakh units."""
    text = (text or "").lower().replace(",", "")
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?|lac)\b",
        text,
    )
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))
    single_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?|lac)\b", text)
    if single_match:
        number = float(single_match.group(1))
        return number, number
    return None


def _location_is_allowed(location: str, cfg: dict) -> bool | None:
    value = (location or "").strip().lower()
    if not value or value in {"unknown", "not specified", "n/a", "na"}:
        return None
    allowed = [str(x).strip().lower() for x in cfg.get("locations", [])]
    aliases = {
        "delhi": ("delhi", "new delhi", "ncr", "national capital region"),
        "gurugram": ("gurugram", "gurgaon"),
        "noida": ("noida", "greater noida"),
        "remote": ("remote", "work from home", "wfh"),
    }
    for loc in allowed:
        terms = aliases.get(loc, (loc,))
        if any(term in value for term in terms):
            return True
    # Unknown format is handled above; an explicit different city is a mismatch.
    return False


def score_job(job: dict, cfg: dict) -> dict:
    title = (job.get("title") or "").strip()
    company = (job.get("company") or "").strip()
    description = (job.get("description") or "").strip()
    location = (job.get("location") or "").strip()
    full_text = " ".join([title, company, description, location]).lower()
    title_tokens = _tokens(title)
    all_tokens = _tokens(full_text)

    matched = []
    for skill in cfg.get("skills", []):
        skill = str(skill).strip()
        skill_tokens = _tokens(skill)
        if skill and skill_tokens and (skill.lower() in full_text or skill_tokens.issubset(all_tokens)):
            matched.append(skill)

    hard_reasons = []
    title_lower = title.lower()
    for term in cfg.get("exclude_keywords", []):
        term = str(term).strip()
        if term and re.search(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)", title_lower):
            hard_reasons.append(f"excluded title keyword: {term}")

    role_match = any(_tokens(keyword) and _tokens(keyword).issubset(title_tokens)
                     for keyword in cfg.get("keywords", []))
    if cfg.get("keywords") and not role_match:
        hard_reasons.append("title does not match configured roles")

    location_match = _location_is_allowed(location, cfg)
    if location_match is False:
        hard_reasons.append(f"location outside configured targets: {location}")

    exp_range = parse_experience_range(job.get("experience", ""))
    exp_min = int(cfg.get("experience_min", 0))
    exp_max = int(cfg.get("experience_max", 99))
    if exp_range and (exp_range[1] < exp_min or exp_range[0] > exp_max):
        hard_reasons.append(f"experience outside configured range ({job.get('experience', '')})")

    age_days = parse_posted_days(job.get("posted_text", ""))
    posted_limit = int(cfg.get("posted_within_days", 0) or 0)
    if age_days is not None and posted_limit > 0 and age_days > posted_limit:
        hard_reasons.append(f"posted {age_days} days ago; limit is {posted_limit}")

    salary_range = parse_salary_range(job.get("salary_text", ""))
    salary_floor = cfg.get("salary_floor_lpa")
    salary_unknown = salary_range is None and salary_floor is not None
    if salary_range and salary_floor is not None and salary_range[1] < float(salary_floor):
        hard_reasons.append(f"salary maximum below configured floor ({salary_range[1]:g} LPA)")

    # Keep score explainable; unknown salary/date/experience does not get guessed.
    score = min(45, len(matched) * 9)
    score += 25 if role_match else 0
    score += 10 if location_match is True else 0
    score += 10 if exp_range and not any("experience outside" in reason for reason in hard_reasons) else 0
    if age_days is not None and age_days <= max(0, posted_limit):
        score += max(0, 10 - age_days * 2)
    score = min(100, score)

    if hard_reasons:
        score = 0
    min_score = int(cfg.get("min_match_score", 0) or 0)
    reasons = hard_reasons[:]
    if not hard_reasons and score < min_score:
        reasons.append(f"match score below configured minimum ({min_score})")
    if salary_unknown:
        job["salary_note"] = "Salary not disclosed/parsed; manually verify before proceeding."
    if not job.get("posted_text"):
        job["freshness_note"] = "Posting age not shown; manually verify the date."

    job["posted_days"] = age_days
    job["salary_range_lpa"] = salary_range
    job["experience_range"] = exp_range
    job["match_score"] = score
    job["matched_skills"] = ", ".join(matched)
    job["excluded_reasons"] = "; ".join(reasons)
    job["is_eligible"] = not reasons
    job["matched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return job
