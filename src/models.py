"""Shared data models for jobs and application outcomes."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ApplicationStatus(str, Enum):
    SEEN = "seen"
    SCORED = "scored"
    SKIPPED = "skipped"
    QUEUED = "queued"
    APPLIED = "applied"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    EXTERNAL = "external"


class JobListing(BaseModel):
    job_id: str
    title: str
    company: str | None = None
    location: str | None = None
    experience_text: str | None = None
    experience_min: float | None = None
    experience_max: float | None = None
    salary_text: str | None = None
    salary_min_lpa: float | None = None
    salary_max_lpa: float | None = None
    skills: list[str] = Field(default_factory=list)
    posted_text: str | None = None
    posted_hours_ago: float | None = None
    applicants: int | None = None
    url: str
    description_snippet: str | None = None
    application_type: str | None = None  # easy_apply | company_site | unknown
    source_query: str | None = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    def fingerprint(self) -> str:
        """Stable key for deduplication."""
        return self.job_id or self.url.rstrip("/").split("/")[-1]


class ScoreBreakdown(BaseModel):
    title_match: float = 0.0
    skills_match: float = 0.0
    experience_fit: float = 0.0
    location_fit: float = 0.0
    freshness: float = 0.0
    competition: float = 0.0
    total: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class ScoredJob(BaseModel):
    job: JobListing
    score: ScoreBreakdown
    eligible: bool = False
    status: ApplicationStatus = ApplicationStatus.SCORED


class ApplicationRecord(BaseModel):
    job_id: str
    title: str
    company: str | None = None
    url: str
    score: float | None = None
    status: ApplicationStatus
    reason: str | None = None
    applied_at: datetime | None = None
    notes: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
