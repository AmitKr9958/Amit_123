"""Unit tests for deterministic scoring (no browser required)."""

from src.config import load_preferences
from src.extract import parse_experience, parse_posted_hours, parse_salary_lpa
from src.models import JobListing
from src.score import score_job


def test_parse_experience():
    assert parse_experience("5-10 Yrs") == (5.0, 10.0)
    assert parse_experience("8+ years")[0] == 8.0


def test_parse_salary():
    assert parse_salary_lpa("12-18 Lacs PA") == (12.0, 18.0)
    assert parse_salary_lpa("Not disclosed") == (None, None)


def test_parse_posted():
    assert parse_posted_hours("2 days ago") == 48.0
    assert parse_posted_hours("Today") == 1.0


def test_power_bi_role_scores_high():
    prefs = load_preferences()
    job = JobListing(
        job_id="1",
        title="Senior Power BI Developer",
        company="Example",
        location="Gurugram",
        experience_text="8-12 Yrs",
        experience_min=8,
        experience_max=12,
        skills=["Power BI", "DAX", "SQL"],
        posted_text="1 day ago",
        posted_hours_ago=24,
        applicants=15,
        url="https://www.naukri.com/job-listings-1",
        description_snippet="Build Power BI dashboards with DAX and Power Query",
    )
    scored = score_job(job, prefs)
    assert scored.score.total >= 0.7
    assert scored.eligible is True
    assert not scored.score.exclusions


def test_intern_excluded():
    prefs = load_preferences()
    job = JobListing(
        job_id="2",
        title="Power BI Intern",
        company="Example",
        location="Delhi",
        url="https://www.naukri.com/job-listings-2",
    )
    scored = score_job(job, prefs)
    assert scored.eligible is False
    assert any("intern" in e.lower() for e in scored.score.exclusions)


def test_salary_below_floor_excluded():
    prefs = load_preferences()
    job = JobListing(
        job_id="3",
        title="Senior Power BI Developer",
        location="Noida",
        salary_text="4-6 Lacs PA",
        salary_min_lpa=4,
        salary_max_lpa=6,
        url="https://www.naukri.com/job-listings-3",
    )
    scored = score_job(job, prefs)
    assert scored.eligible is False
    assert any("salary" in e.lower() for e in scored.score.exclusions)


def test_blacklisted_company_excluded():
    prefs = load_preferences()
    prefs.exclude.companies = ["BadCorp"]
    job = JobListing(
        job_id="4",
        title="Senior Power BI Developer",
        company="BadCorp Pvt Ltd",
        location="Noida",
        url="https://www.naukri.com/job-listings-4",
    )
    assert score_job(job, prefs).eligible is False


def test_experience_range_with_word_to():
    assert parse_experience("5 to 10 Yrs") == (5.0, 10.0)
