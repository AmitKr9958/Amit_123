"""Command-line entry points."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import __version__
from .apply import attempt_apply
from .browser import BrowserSession
from .config import ensure_data_dirs, load_preferences, load_profile
from .models import ApplicationStatus
from .notify import notify_error, notify_run_summary
from .score import score_job
from .search import collect_jobs
from .tracker import (
    already_seen,
    count_applied_today,
    finish_run,
    init_db,
    list_recent,
    record_scored,
    start_run,
)

console = Console()


async def cmd_login() -> None:
    ensure_data_dirs()
    session = BrowserSession()
    try:
        await session.start()
        await session.ensure_authenticated(timeout_seconds=600)
        console.print("[green]Session saved in data/browser_profile.[/green]")
    finally:
        await session.close()


async def cmd_search_and_score(*, apply: bool = False) -> None:
    ensure_data_dirs()
    init_db()
    prefs = load_preferences()
    try:
        profile = load_profile()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        console.print("Copy data/profile.example.yaml → data/profile.yaml first.")
        sys.exit(1)

    applied_today = count_applied_today()
    remaining = max(0, prefs.search.daily_application_cap - applied_today)
    console.print(
        f"Daily cap {prefs.search.daily_application_cap} · already applied today {applied_today} · remaining {remaining}"
    )
    if apply and remaining <= 0:
        console.print("[yellow]Daily application cap reached. Skipping apply phase.[/yellow]")
        apply = False

    run_id = start_run()
    session = BrowserSession()
    jobs_seen = jobs_scored = applied = skipped = failed = 0
    scored_eligible: list = []

    try:
        await session.start()
        await session.ensure_authenticated()

        jobs = await collect_jobs(session, prefs)
        jobs_seen = len(jobs)
        console.print(f"\n[bold]Collected {jobs_seen} unique listings[/bold]")

        for job in jobs:
            if already_seen(job.job_id):
                continue
            scored = score_job(job, prefs)
            jobs_scored += 1
            status = (
                ApplicationStatus.QUEUED
                if scored.eligible
                else ApplicationStatus.SKIPPED
            )
            record_scored(scored, status=status)
            if scored.eligible:
                scored_eligible.append(scored)
            else:
                skipped += 1

        scored_eligible.sort(key=lambda s: s.score.total, reverse=True)

        table = Table(title="Top eligible jobs")
        table.add_column("Score", justify="right")
        table.add_column("Title")
        table.add_column("Company")
        table.add_column("Location")
        table.add_column("Exp")
        for s in scored_eligible[:20]:
            table.add_row(
                f"{s.score.total:.2f}",
                s.job.title[:50],
                (s.job.company or "")[:24],
                (s.job.location or "")[:20],
                s.job.experience_text or "",
            )
        console.print(table)

        if not apply:
            console.print(
                "\n[cyan]Dry-run complete.[/cyan] Re-run with --apply to attempt applications "
                "(still supervised; auto_submit defaults to false)."
            )
            notify_run_summary(
                jobs_seen=jobs_seen,
                jobs_scored=jobs_scored,
                applied=0,
                skipped=skipped,
                failed=0,
                top_titles=[s.job.title for s in scored_eligible[:5]],
            )
            return

        for s in scored_eligible:
            if applied >= remaining:
                console.print("[yellow]Hit remaining daily cap.[/yellow]")
                break
            status = await attempt_apply(session, s, prefs, profile)
            if status == ApplicationStatus.APPLIED:
                applied += 1
            elif status == ApplicationStatus.FAILED:
                failed += 1
            else:
                skipped += 1
            await session.human_delay(
                prefs.search.min_delay_seconds,
                prefs.search.max_delay_seconds,
            )

    except Exception as exc:
        notify_error(str(exc))
        raise
    finally:
        finish_run(
            run_id,
            jobs_seen=jobs_seen,
            jobs_scored=jobs_scored,
            applied=applied,
            skipped=skipped,
            failed=failed,
        )
        try:
            await session.close()
        except Exception:
            pass
        top = [s.job.title for s in scored_eligible[:5]] if scored_eligible else []
        notify_run_summary(
            jobs_seen=jobs_seen,
            jobs_scored=jobs_scored,
            applied=applied,
            skipped=skipped,
            failed=failed,
            top_titles=top,
        )
        console.print(
            f"\n[bold]Run summary[/bold] seen={jobs_seen} scored={jobs_scored} "
            f"applied={applied} skipped={skipped} failed={failed}"
        )


def cmd_status() -> None:
    init_db()
    rows = list_recent(30)
    table = Table(title="Recent applications")
    table.add_column("Status")
    table.add_column("Score")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Updated")
    for r in rows:
        table.add_row(
            r.get("status") or "",
            f"{r['score']:.2f}" if r.get("score") is not None else "",
            (r.get("title") or "")[:45],
            (r.get("company") or "")[:20],
            (r.get("updated_at") or "")[:19],
        )
    console.print(table)
    console.print(f"Applied today: {count_applied_today()}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="naukri-apply",
        description="Supervised Naukri job search, scoring, and application assistant",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="Open browser and complete manual login / OTP once")
    p_run = sub.add_parser("run", help="Search + score jobs (add --apply to attempt apply)")
    p_run.add_argument(
        "--apply",
        action="store_true",
        help="Attempt applications for eligible jobs (supervised; respects auto_submit=false)",
    )
    sub.add_parser("status", help="Show recent tracked applications")
    sub.add_parser("init-db", help="Create SQLite schema")

    args = parser.parse_args(argv)

    if args.command == "login":
        asyncio.run(cmd_login())
    elif args.command == "run":
        asyncio.run(cmd_search_and_score(apply=args.apply))
    elif args.command == "status":
        cmd_status()
    elif args.command == "init-db":
        init_db()
        console.print("Database ready at data/applied.db")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
