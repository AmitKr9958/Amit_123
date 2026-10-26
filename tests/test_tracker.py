"""Tracker behaviour: queued jobs must survive a dry-run so --apply can pick them up."""

import pytest

from src import tracker
from src.config import load_preferences
from src.models import ApplicationStatus, JobListing
from src.score import score_job


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "applied.db")
    monkeypatch.setattr(tracker, "ensure_data_dirs", lambda: None)
    tracker.init_db()


def _scored():
    job = JobListing(
        job_id="42",
        title="Senior Power BI Developer",
        location="Delhi",
        url="https://www.naukri.com/job-listings-42",
    )
    return score_job(job, load_preferences())


def test_status_roundtrip_and_cap_count():
    assert tracker.get_status("42") is None
    tracker.record_scored(_scored(), status=ApplicationStatus.QUEUED)
    assert tracker.get_status("42") == "queued"
    assert tracker.count_applied_today() == 0
    tracker.mark_applied("42", "test")
    assert tracker.get_status("42") == "applied"
    assert tracker.count_applied_today() == 1
