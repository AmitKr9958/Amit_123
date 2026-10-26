"""Load and validate configuration and profile data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"


class _Strict(BaseModel):
    """Reject unknown keys so a typo in YAML cannot silently disable a safety rule."""

    model_config = ConfigDict(extra="forbid")


class ProfileConfig(_Strict):
    name: str = "Amit Kumar"
    total_experience_years: float = 11
    relevant_experience_years: float = 10
    notice_period_days: int | str = 30
    current_location: str = "Delhi NCR"
    preferred_locations: list[str] = Field(default_factory=list)
    allow_remote: bool = True
    min_salary_lpa: float = 11
    max_applicants: int = 50
    ideal_max_applicants: int = 25
    max_posting_age_hours: int = 48


class RolesConfig(_Strict):
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)


class SkillsConfig(_Strict):
    must_have_any: list[str] = Field(default_factory=list)
    strong: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)


class ExcludeConfig(_Strict):
    title_keywords: list[str] = Field(default_factory=list)
    experience_max_years: float = 6
    companies: list[str] = Field(default_factory=list)


class SearchConfig(_Strict):
    queries: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    pages_per_query: int = 2
    max_jobs_per_run: int = 40
    daily_application_cap: int = 30
    concurrency: int = 1
    min_delay_seconds: float = 4
    max_delay_seconds: float = 12


class ScoringWeights(_Strict):
    title_match: float = 0.30
    skills_match: float = 0.25
    experience_fit: float = 0.20
    location_fit: float = 0.15
    freshness: float = 0.05
    competition: float = 0.05


class ScoringConfig(_Strict):
    min_score_to_apply: float = 0.55
    weights: ScoringWeights = Field(default_factory=ScoringWeights)


class ApplicationConfig(_Strict):
    auto_submit: bool = False
    pause_on_unknown_question: bool = True
    pause_on_external_site: bool = True
    answer_screening_from_profile_only: bool = True


class Preferences(_Strict):
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    roles: RolesConfig = Field(default_factory=RolesConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    exclude: ExcludeConfig = Field(default_factory=ExcludeConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    application: ApplicationConfig = Field(default_factory=ApplicationConfig)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_preferences(path: Path | None = None) -> Preferences:
    path = path or (CONFIG_DIR / "preferences.yaml")
    raw = _load_yaml(path)
    return Preferences.model_validate(raw)


def load_profile(path: Path | None = None) -> dict[str, Any]:
    path = path or (DATA_DIR / "profile.yaml")
    if not path.exists():
        example = DATA_DIR / "profile.example.yaml"
        raise FileNotFoundError(
            f"Missing {path}. Copy {example} to {path} and fill verified facts only."
        )
    return _load_yaml(path)


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "screenshots").mkdir(exist_ok=True)
    (DATA_DIR / "browser_profile").mkdir(exist_ok=True)
