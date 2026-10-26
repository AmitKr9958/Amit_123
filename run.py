"""CLI for the Naukri Job Assistant."""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

from naukri_assistant.browser import NaukriBrowser
from naukri_assistant.config import load_config
from naukri_assistant.db import JobStore
from naukri_assistant.form_helper import is_naukri_host, prefill_known_fields
from naukri_assistant.matcher import score_job
from naukri_assistant.search import build_search_urls

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "jobs.sqlite3"
STATUS_CHOICES = ["saved", "excluded", "reviewed", "applied", "rejected", "interview", "offer", "closed"]


def store() -> JobStore:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return JobStore(DB_PATH)


def command_login(_args: argparse.Namespace) -> int:
    cfg = load_config()
    print("Opening a visible browser. Sign into Naukri manually and complete any OTP/CAPTCHA yourself.")
    with NaukriBrowser(cfg) as browser:
        page = browser.new_page()
        page.goto("https://www.naukri.com/", wait_until="domcontentloaded")
        input("\nAfter confirming you are signed in in the browser, press Enter to close it...")
    print("Browser profile is saved locally in data/browser-profile.")
    return 0


def command_search(args: argparse.Namespace) -> int:
    cfg = load_config()
    if args.limit is not None:
        cfg["limits"]["max_jobs_per_run"] = max(1, args.limit)
    db = store()
    processed = 0
    new_eligible = 0
    queries = build_search_urls(cfg)
    print(f"Configured searches: {len(queries)}. PREVIEW ONLY: the tool never submits applications.")
    stop_all = False
    try:
        with NaukriBrowser(cfg) as browser:
            page = browser.new_page()
            for query, url in queries:
                if processed >= cfg["limits"]["max_jobs_per_run"] or stop_all:
                    break
                print(f"\n[SEARCH] {query} -> {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=cfg["browser"]["navigation_timeout_ms"])
                    page.wait_for_timeout(1800)
                    protection = browser.stop_reason(page)
                    if protection:
                        print(f"[SAFETY STOP] {protection}. Resolve manually and restart; no bypass attempted.")
                        stop_all = True
                        break
                    extracted = browser.extract_jobs(page, query, url)
                except Exception as exc:
                    print(f"[WARN] Could not inspect search page: {exc}")
                    continue
                if not extracted:
                    print("[INFO] No job cards detected. Naukri markup may have changed or verification is required.")
                for raw in extracted:
                    if processed >= cfg["limits"]["max_jobs_per_run"]:
                        break
                    scored = score_job(raw, cfg)
                    status = db.upsert_job(scored)
                    processed += 1
                    if status == "new" and scored.get("is_eligible"):
                        new_eligible += 1
                    print_job(scored, status)
    finally:
        db.close()
    print(f"\nDone. {new_eligible} new eligible jobs discovered from {processed} cards. Use 'python run.py list' to review.")
    return 0


def print_job(job: dict, status: str) -> None:
    if job.get("excluded_reasons"):
        marker = "FILTERED"
    else:
        marker = "NEW" if status == "new" else "SEEN"
    print(f"  [{marker}] score={job.get('match_score', 0):>3} | {job.get('title', 'Unknown')} | {job.get('company', 'Unknown')} | {job.get('location', 'Unknown')}")
    if job.get("matched_skills"):
        print(f"        matched: {job['matched_skills']}")
    if job.get("excluded_reasons"):
        print(f"        reason: {job['excluded_reasons']}")
    elif job.get("salary_note"):
        print(f"        note: {job['salary_note']}")
    if job.get("freshness_note"):
        print(f"        note: {job['freshness_note']}")
    print(f"        {job.get('url', '')}")


def command_list(args: argparse.Namespace) -> int:
    db = store()
    try:
        jobs = db.list_jobs(limit=args.limit, status=args.status)
        if not jobs:
            print("No saved jobs yet. Run: python run.py search")
            return 0
        for job in jobs:
            print(f"{job['id']} | score={job['match_score']:>3} | {job['status']:<10} | {job['title']} | {job['company']} | {job['location']}")
            if job["excluded_reasons"]:
                print(f"    filtered: {job['excluded_reasons']}")
            print(f"    posted: {job['posted_text']} | experience: {job['experience']}")
            print(f"    {job['url']}")
    finally:
        db.close()
    return 0


def command_open(args: argparse.Namespace) -> int:
    db = store()
    job = db.get_job(args.job_id)
    if not job:
        db.close()
        print(f"Unknown job ID: {args.job_id}")
        return 2
    try:
        cfg = load_config()
        with NaukriBrowser(cfg) as browser:
            page = browser.new_page()
            page.goto(job["url"], wait_until="domcontentloaded", timeout=cfg["browser"]["navigation_timeout_ms"])
            page.wait_for_timeout(1200)
            protection = browser.stop_reason(page)
            if protection:
                print(f"[SAFETY STOP] {protection}. Use the site manually; no bypass attempted.")
                return 1
            print("\nThe job is open in the saved visible browser profile.")
            print("Inspect the job details. If you decide to apply, click Apply yourself in the browser.")
            choice = input("After the application form is open, press Enter for optional safe field prefill, or type S to skip prefill/Q to quit: ").strip().lower()
            if choice == "q":
                return 0
            if choice != "s":
                if not is_naukri_host(page.url):
                    print("External company portal detected. No fields were filled; use that site manually.")
                else:
                    filled = prefill_known_fields(page, cfg)
                    if filled:
                        print("Prefilled blank fields from your local profile. Verify every field:")
                        for label in filled:
                            print(f"  - {label}")
                    else:
                        print("No confidently labelled eligible fields were filled.")
            print("\nNo Apply/Submit/Send button is clicked by this program.")
            result = input("After you finish manually, type applied only if the site confirms success; R=reviewed, S=skip tracking, Q=quit: ").strip().lower()
            if result == "applied":
                db.update_status(args.job_id, "applied")
            elif result == "r":
                db.update_status(args.job_id, "reviewed")
            elif result == "s":
                db.update_status(args.job_id, "rejected")
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 0
    finally:
        db.close()
    return 0


def command_status(args: argparse.Namespace) -> int:
    if args.status not in STATUS_CHOICES:
        print(f"Invalid status. Choose from: {', '.join(STATUS_CHOICES)}")
        return 2
    db = store()
    try:
        if not db.update_status(args.job_id, args.status):
            print(f"Unknown job ID: {args.job_id}")
            return 2
    finally:
        db.close()
    print(f"Updated {args.job_id} -> {args.status}")
    return 0


def command_export(_args: argparse.Namespace) -> int:
    db = store()
    out_dir = ROOT / "exports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "naukri_jobs.csv"
    try:
        jobs = db.list_jobs(limit=10000)
        if not jobs:
            print("No saved jobs to export.")
            return 0
        with out_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=list(jobs[0].keys()))
            writer.writeheader()
            writer.writerows(jobs)
    finally:
        db.close()
    print(f"Exported {len(jobs)} jobs to {out_path}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Naukri Job Assistant - search, score, track and review jobs.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("login", help="Open visible browser for manual sign-in")
    p.set_defaults(func=command_login)
    p = sub.add_parser("search", help="Discover, filter and score jobs (preview-only)")
    p.add_argument("--limit", type=int, help="Override max jobs processed")
    p.set_defaults(func=command_search)
    p = sub.add_parser("list", help="List saved jobs")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--status", choices=STATUS_CHOICES)
    p.set_defaults(func=command_list)
    p = sub.add_parser("open", help="Open a saved job in your persistent browser for manual review")
    p.add_argument("job_id")
    p.set_defaults(func=command_open)
    p = sub.add_parser("status", help="Update application status")
    p.add_argument("job_id")
    p.add_argument("status")
    p.set_defaults(func=command_status)
    p = sub.add_parser("export", help="Export tracker to CSV")
    p.set_defaults(func=command_export)
    return parser


def main() -> int:
    args = make_parser().parse_args()
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
