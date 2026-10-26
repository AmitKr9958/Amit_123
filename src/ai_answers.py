"""
Optional LLM helpers for screening questions.

Rules enforced here:
- Answers must be grounded in the provided profile dict only.
- The model is instructed never to invent experience, employers, dates, or skills.
- Every generated answer is returned with a confidence flag so the apply flow
  can pause for human review when confidence is low or the question is sensitive.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from rich.console import Console

console = Console()

SENSITIVE_PATTERNS = re.compile(
    r"(salary|ctc|current\s*pay|expected\s*ctc|compensation|notice\s*period|"
    r"last\s*working|reason\s*for\s*(leaving|change)|relocat|background\s*check|"
    r"criminal|disability|gender|religion|caste|marital)",
    re.I,
)


@dataclass
class AnswerDraft:
    question: str
    answer: str
    confidence: float  # 0–1
    source: str  # "profile_map" | "llm" | "none"
    needs_review: bool
    reason: str = ""


def _profile_blob(profile: dict[str, Any]) -> str:
    """Flatten verified profile into a short facts block for the prompt."""
    parts: list[str] = []
    personal = profile.get("personal") or {}
    exp = profile.get("experience") or {}
    comp = profile.get("compensation") or {}
    skills = profile.get("skills") or {}
    defaults = profile.get("screening_defaults") or {}

    if personal.get("full_name"):
        parts.append(f"Name: {personal['full_name']}")
    if exp.get("total_years") is not None:
        parts.append(f"Total experience years: {exp['total_years']}")
    if exp.get("relevant_years") is not None:
        parts.append(f"Relevant experience years: {exp['relevant_years']}")
    if exp.get("notice_period"):
        parts.append(f"Notice period: {exp['notice_period']}")
    if exp.get("currently_serving_notice") is not None:
        parts.append(f"Serving notice: {exp['currently_serving_notice']}")
    if comp.get("expected_ctc_lpa") is not None:
        parts.append(f"Expected CTC (LPA): {comp['expected_ctc_lpa']}")
    if comp.get("current_ctc_lpa") is not None:
        parts.append(f"Current CTC (LPA): {comp['current_ctc_lpa']}")
    if skills.get("primary"):
        parts.append("Primary skills: " + ", ".join(skills["primary"]))
    if skills.get("secondary"):
        parts.append("Secondary skills: " + ", ".join(skills["secondary"]))
    if profile.get("employment_history_summary"):
        parts.append("Summary: " + str(profile["employment_history_summary"]).strip())
    for k, v in defaults.items():
        parts.append(f"{k}: {v}")
    return "\n".join(parts) if parts else "No profile facts provided."


def map_common_question(question: str, profile: dict[str, Any]) -> AnswerDraft | None:
    """Deterministic answers for frequent Naukri screening fields."""
    q = question.lower().strip()
    exp = profile.get("experience") or {}
    comp = profile.get("compensation") or {}
    defaults = profile.get("screening_defaults") or {}
    personal = profile.get("personal") or {}

    def ok(answer: str, conf: float = 0.95) -> AnswerDraft:
        return AnswerDraft(
            question=question,
            answer=answer,
            confidence=conf,
            source="profile_map",
            needs_review=False,
            reason="Mapped from profile",
        )

    if re.search(r"total\s*(years?|exp)|how\s*many\s*years", q):
        if exp.get("total_years") is not None:
            return ok(str(exp["total_years"]))
    if re.search(r"relevant\s*(years?|exp)|years?\s*of\s*(relevant|power\s*bi)", q):
        if exp.get("relevant_years") is not None:
            return ok(str(exp["relevant_years"]))
    if "notice" in q:
        if exp.get("notice_period"):
            return ok(str(exp["notice_period"]))
    if re.search(r"expected\s*(ctc|salary|pay)|salary\s*expectation", q):
        if comp.get("expected_ctc_lpa") is not None:
            return ok(f"{comp['expected_ctc_lpa']} LPA")
    if re.search(r"current\s*(ctc|salary|pay)", q):
        if comp.get("current_ctc_lpa") is not None:
            return ok(f"{comp['current_ctc_lpa']} LPA")
        return AnswerDraft(
            question=question,
            answer="",
            confidence=0.0,
            source="none",
            needs_review=True,
            reason="Current CTC not set in profile",
        )
    if "relocat" in q and defaults.get("willing_to_relocate"):
        return ok(str(defaults["willing_to_relocate"]))
    if "shift" in q and defaults.get("preferred_shift"):
        return ok(str(defaults["preferred_shift"]))
    if re.search(r"work\s*mode|remote|hybrid|wfh", q) and defaults.get("work_mode"):
        return ok(str(defaults["work_mode"]))
    if re.search(r"reason\s*for\s*(change|leaving)", q) and defaults.get("reason_for_change"):
        return ok(str(defaults["reason_for_change"]), conf=0.85)
    if re.search(r"\b(name|full\s*name)\b", q) and personal.get("full_name"):
        return ok(str(personal["full_name"]))
    if "email" in q and personal.get("email"):
        return ok(str(personal["email"]))
    if re.search(r"phone|mobile|contact\s*number", q) and personal.get("phone"):
        return ok(str(personal["phone"]))
    return None


def _call_openai(prompt: str) -> str | None:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You answer job application screening questions. "
                        "Use ONLY the facts in the PROFILE block. "
                        "If the profile does not contain enough information, reply exactly: INSUFFICIENT_FACTS. "
                        "Never invent employers, dates, certifications, salary numbers, or skills. "
                        "Keep answers short and factual (1-3 sentences max)."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        console.print(f"[yellow]OpenAI call failed:[/yellow] {exc}")
        return None


def _call_gemini(prompt: str) -> str | None:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            system_instruction=(
                "Answer job screening questions using ONLY the PROFILE facts. "
                "If insufficient, reply exactly: INSUFFICIENT_FACTS. "
                "Never invent experience, employers, dates, or skills."
            ),
        )
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as exc:
        console.print(f"[yellow]Gemini call failed:[/yellow] {exc}")
        return None


def draft_answer(
    question: str,
    profile: dict[str, Any],
    *,
    use_llm: bool = True,
) -> AnswerDraft:
    """
    Produce an answer draft.
    1) Try deterministic profile map.
    2) Optionally call LLM with strict facts-only instructions.
    3) Mark needs_review for sensitive or low-confidence cases.
    """
    mapped = map_common_question(question, profile)
    if mapped:
        if SENSITIVE_PATTERNS.search(question):
            mapped.needs_review = True
            mapped.reason = (mapped.reason + "; sensitive topic").strip("; ")
        return mapped

    sensitive = bool(SENSITIVE_PATTERNS.search(question))
    if not use_llm:
        return AnswerDraft(
            question=question,
            answer="",
            confidence=0.0,
            source="none",
            needs_review=True,
            reason="No profile mapping; LLM disabled",
        )

    facts = _profile_blob(profile)
    prompt = (
        f"PROFILE:\n{facts}\n\n"
        f"QUESTION:\n{question}\n\n"
        "Answer using only PROFILE. If you cannot, reply INSUFFICIENT_FACTS."
    )
    text = _call_openai(prompt) or _call_gemini(prompt)
    if not text or "INSUFFICIENT_FACTS" in text.upper():
        return AnswerDraft(
            question=question,
            answer="",
            confidence=0.0,
            source="llm" if text else "none",
            needs_review=True,
            reason="Insufficient facts in profile for this question",
        )

    conf = 0.55 if sensitive else 0.7
    return AnswerDraft(
        question=question,
        answer=text,
        confidence=conf,
        source="llm",
        needs_review=True,  # always review LLM free-text by default
        reason="LLM draft from profile facts — review before submit",
    )


def draft_many(
    questions: list[str],
    profile: dict[str, Any],
    *,
    use_llm: bool = True,
) -> list[AnswerDraft]:
    return [draft_answer(q, profile, use_llm=use_llm) for q in questions]
