"""Application attempt helpers – fill only verified profile data; pause on unknowns."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from playwright.async_api import Page
from rich.console import Console
from rich.prompt import Confirm, Prompt

from .ai_answers import draft_answer
from .browser import BrowserSession
from .config import Preferences
from .models import ApplicationStatus, ScoredJob
from .notify import notify_applied
from .selectors import ALREADY_APPLIED_SELECTORS, APPLY_BUTTON_SELECTORS
from .tracker import mark_applied, mark_status

console = Console()


async def _click_apply_if_present(page: Page) -> str:
    """Returns: applied_inline | company_site | already | not_found"""
    for sel in ALREADY_APPLIED_SELECTORS:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible():
                return "already"
        except Exception:
            continue

    for sel in APPLY_BUTTON_SELECTORS:
        try:
            loc = page.locator(sel).first
            if await loc.count() == 0 or not await loc.is_visible():
                continue
            text = ((await loc.inner_text()) or "").lower()
            await loc.click(timeout=5_000)
            await asyncio.sleep(2)
            if "company site" in text or "company-site" in sel:
                return "company_site"
            return "applied_inline"
        except Exception:
            continue

    for phrase in ("Apply on company site", "Apply"):
        try:
            loc = page.locator(f"//button[contains(normalize-space(.), '{phrase}')]").first
            if await loc.count() == 0:
                loc = page.locator(f"//a[contains(normalize-space(.), '{phrase}')]").first
            if await loc.count() and await loc.is_visible():
                text = ((await loc.inner_text()) or "").lower()
                await loc.click(timeout=5_000)
                await asyncio.sleep(2)
                return "company_site" if "company site" in text else "applied_inline"
        except Exception:
            continue
    return "not_found"


async def _collect_visible_questions(page: Page) -> list[str]:
    try:
        questions = await page.evaluate(
            """
            () => {
              const out = [];
              const nodes = document.querySelectorAll(
                'label, div.chatbot-question, div[class*="question"], ' +
                'span[class*="question"], p[class*="chat"], div[class*="screening"]'
              );
              nodes.forEach(n => {
                const t = (n.innerText || n.textContent || '').trim();
                if (t && t.length > 3 && t.length < 300 && t.includes('?')) out.push(t);
              });
              document.querySelectorAll('div[class*="chat"] p, div[class*="bot"] span').forEach(n => {
                const t = (n.innerText || '').trim();
                if (t && t.length > 8 && t.length < 200) out.push(t);
              });
              return [...new Set(out)].slice(0, 12);
            }
            """
        )
        return list(questions or [])
    except Exception:
        return []


async def _try_fill_simple_inputs(page: Page, profile: dict[str, Any]) -> int:
    personal = profile.get("personal") or {}
    exp = profile.get("experience") or {}
    filled = 0
    mappings = [
        (["name", "full name"], personal.get("full_name")),
        (["email", "e-mail"], personal.get("email")),
        (["mobile", "phone", "contact"], personal.get("phone")),
        (["notice"], exp.get("notice_period")),
        (["total experience", "years of experience"], exp.get("total_years")),
    ]
    for keywords, value in mappings:
        if value is None or value == "":
            continue
        for kw in keywords:
            try:
                loc = page.locator(
                    f"input[placeholder*='{kw}' i], input[aria-label*='{kw}' i], "
                    f"textarea[placeholder*='{kw}' i]"
                ).first
                if await loc.count() == 0:
                    continue
                await loc.fill(str(value), timeout=2_000)
                filled += 1
                break
            except Exception:
                continue
    return filled


async def _handle_screening(
    page: Page,
    profile: dict[str, Any],
    prefs: Preferences,
) -> None:
    use_llm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY"))
    questions = await _collect_visible_questions(page)
    if not questions:
        n = await _try_fill_simple_inputs(page, profile)
        if n:
            console.print(f"[cyan]Filled {n} profile-mapped field(s).[/cyan]")
        return

    console.print(f"[cyan]Detected {len(questions)} possible screening prompt(s).[/cyan]")
    for q in questions:
        draft = draft_answer(q, profile, use_llm=use_llm)
        console.print(f"\n[bold]Q:[/bold] {q}")
        if draft.answer:
            console.print(
                f"[green]Draft ({draft.source}, conf={draft.confidence:.2f}):[/green] {draft.answer}"
            )
            if draft.reason:
                console.print(f"  [dim]{draft.reason}[/dim]")
        else:
            console.print(f"[yellow]No safe draft[/yellow] — {draft.reason}")

        if draft.needs_review or prefs.application.pause_on_unknown_question:
            if draft.answer:
                use = Confirm.ask(
                    "Use this draft in the form (you still submit manually)?", default=True
                )
                if not use:
                    draft.answer = Prompt.ask("Your answer (blank to skip)", default="")
            else:
                draft.answer = Prompt.ask("Your answer (blank to skip)", default="")

        if not draft.answer:
            continue

        try:
            box = page.locator("textarea:visible, input[type='text']:visible").last
            if await box.count():
                await box.fill(draft.answer)
                await asyncio.sleep(0.5)
                send_btn = page.locator(
                    "button:has-text('Submit'), button:has-text('Send'), "
                    "button:has-text('Save'), button[type='submit']"
                ).first
                if await send_btn.count():
                    label = ((await send_btn.inner_text()) or "").lower()
                    if "apply" not in label:
                        await send_btn.click()
                        await asyncio.sleep(1)
        except Exception as exc:
            console.print(f"[yellow]Could not auto-type answer:[/yellow] {exc}")

    await _try_fill_simple_inputs(page, profile)


async def attempt_apply(
    session: BrowserSession,
    scored: ScoredJob,
    prefs: Preferences,
    profile: dict[str, Any],
) -> ApplicationStatus:
    page = session.page
    assert page
    job = scored.job
    console.print(f"\n[bold]Applying:[/bold] {job.title} @ {job.company or '?'}")
    console.print(f"  score={scored.score.total}  url={job.url}")

    try:
        await session.goto(job.url)
        await session.human_delay(2, 5)
    except Exception as exc:
        console.print(f"[red]Failed to open job:[/red] {exc}")
        mark_status(job.job_id, ApplicationStatus.FAILED, str(exc))
        return ApplicationStatus.FAILED

    result = await _click_apply_if_present(page)
    if result == "already":
        console.print("[yellow]Already applied.[/yellow]")
        mark_status(job.job_id, ApplicationStatus.SKIPPED, "already applied")
        return ApplicationStatus.SKIPPED

    if result == "company_site":
        console.print("[yellow]Redirected / company site application.[/yellow]")
        if prefs.application.pause_on_external_site:
            console.print(
                "  External careers site detected. Complete manually if desired, "
                "then continue in the terminal."
            )
            Confirm.ask("Press Enter / confirm when done or to skip", default=True)
        mark_status(job.job_id, ApplicationStatus.EXTERNAL, "company site")
        return ApplicationStatus.EXTERNAL

    if result == "not_found":
        console.print("[yellow]No Apply button found.[/yellow]")
        mark_status(job.job_id, ApplicationStatus.NEEDS_REVIEW, "no apply button")
        return ApplicationStatus.NEEDS_REVIEW

    await asyncio.sleep(1.5)
    await _handle_screening(page, profile, prefs)

    if prefs.application.auto_submit:
        try:
            submit = page.locator(
                "button:has-text('Submit'), button:has-text('Apply'), "
                "button:has-text('Send Application')"
            ).first
            if await submit.count():
                await submit.click()
                await asyncio.sleep(2)
        except Exception:
            pass
        mark_applied(job.job_id, "auto_submit")
        notify_applied(job.title, job.company, scored.score.total)
        return ApplicationStatus.APPLIED

    if Confirm.ask("Mark this job as successfully applied?", default=False):
        mark_applied(job.job_id, "user confirmed")
        notify_applied(job.title, job.company, scored.score.total)
        return ApplicationStatus.APPLIED

    mark_status(job.job_id, ApplicationStatus.NEEDS_REVIEW, "user deferred")
    return ApplicationStatus.NEEDS_REVIEW
