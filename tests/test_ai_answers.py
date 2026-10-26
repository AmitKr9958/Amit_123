"""Tests for profile-mapped screening answers (no API keys required)."""

from src.ai_answers import draft_answer, map_common_question


PROFILE = {
    "personal": {
        "full_name": "Amit Kumar",
        "email": "amit@example.com",
        "phone": "+919999999999",
    },
    "experience": {
        "total_years": 11,
        "relevant_years": 10,
        "notice_period": "30 days",
    },
    "compensation": {
        "expected_ctc_lpa": 11,
    },
    "screening_defaults": {
        "willing_to_relocate": "Within Delhi NCR / Jaipur only",
        "preferred_shift": "Day",
        "work_mode": "Hybrid preferred",
        "reason_for_change": "Seeking greater ownership of BI outcomes",
    },
}


def test_notice_period_mapped():
    d = map_common_question("What is your notice period?", PROFILE)
    assert d is not None
    assert "30" in d.answer


def test_expected_ctc_mapped():
    d = draft_answer("What is your expected CTC?", PROFILE, use_llm=False)
    assert "11" in d.answer
    assert d.source == "profile_map"


def test_unknown_without_llm_needs_review():
    d = draft_answer(
        "Describe a complex DAX measure you built for inventory aging",
        PROFILE,
        use_llm=False,
    )
    assert d.needs_review is True
    assert d.answer == ""
