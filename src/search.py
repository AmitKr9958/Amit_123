"""Job discovery on Naukri search result pages (2026 selectors)."""

from __future__ import annotations

import re
from typing import Any

from playwright.async_api import Page
from rich.console import Console

from .browser import BrowserSession
from .config import Preferences
from .extract import listing_from_card
from .models import JobListing
from .selectors import SRP_READY

console = Console()


def build_search_url(query: str, location: str | None, page: int = 1) -> str:
    """
    Build a Naukri search URL (2026 pattern).
    /{slug}-jobs-in-{location}  or  /{slug}-jobs
    Pagination suffix: -{page} when page > 1
    """
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    if location:
        loc = re.sub(r"[^a-z0-9]+", "-", location.lower()).strip("-")
        base = f"https://www.naukri.com/{slug}-jobs-in-{loc}"
    else:
        base = f"https://www.naukri.com/{slug}-jobs"
    if page > 1:
        return f"{base}-{page}"
    return base


def _js_extract_cards() -> str:
    """Browser-side extraction aligned with 2026 srp-jobtuple-wrapper structure."""
    return """
    () => {
      const pick = (root, sels) => {
        for (const s of sels) {
          const el = root.querySelector(s);
          if (el) return (el.innerText || el.textContent || '').trim();
        }
        return null;
      };
      const pickHref = (root, sels) => {
        for (const s of sels) {
          const el = root.querySelector(s);
          if (el && el.href) return el.href;
        }
        return null;
      };
      const results = [];
      const nodes = document.querySelectorAll(
        'div.srp-jobtuple-wrapper, div.cust-job-tuple, article.jobTuple, div[class*="jobTuple"], div[class*="srp-jobtuple"]'
      );
      nodes.forEach((node) => {
        const jobId = node.getAttribute('data-job-id')
          || node.getAttribute('data-jobid')
          || null;
        const titleSels = ['a.title', 'h2 a.title', 'h2 a', 'a[class*="title"]', 'a[href*="job-listings"]'];
        const title = pick(node, titleSels);
        const href = pickHref(node, titleSels);
        if (!title || !href) return;
        const company = pick(node, [
          'a.comp-name', 'a[class*="comp-name"]', 'span.comp-name', 'a[class*="comp"]'
        ]);
        const location = pick(node, [
          'span.locWdth', 'span[class*="locWdth"]', 'span[class*="loc"]',
          'li[class*="location"]', 'span.location'
        ]);
        const experience = pick(node, [
          'span.expwdth', 'span[class*="expwdth"]', 'span[class*="exp"]',
          'li[class*="experience"]'
        ]);
        const salary = pick(node, [
          'span.sal', 'span[class*="salar"]', 'span[class*="salary"]'
        ]);
        const posted = pick(node, [
          'span.job-post-day', 'span[class*="job-post-day"]',
          'span[class*="posted"]', 'span.time'
        ]) || ((node.innerText || '').match(
          /\b(?:just now|just posted|today|yesterday|few\s+(?:minutes?|hours?)\s+ago|\d+\s*(?:minutes?|mins?|hours?|hrs?|days?|weeks?)\s+ago)\b/i
        ) || [])[0] || null;
        const applicants = pick(node, [
          'span[class*="applicant"]', 'span[class*="applied"]'
        ]);
        const skillEls = node.querySelectorAll(
          'ul.tags-gt li, ul[class*="tags"] li, span[class*="skill"], a[class*="skill"]'
        );
        const skills = Array.from(skillEls).map(s => (s.innerText || '').trim()).filter(Boolean);
        const snippet = pick(node, [
          'span.job-desc', 'div[class*="job-description"]', 'span[class*="desc"]'
        ]);
        results.push({
          job_id: jobId,
          title,
          url: href,
          company,
          location,
          experience,
          salary,
          posted,
          applicants,
          skills,
          snippet: snippet ? snippet.slice(0, 500) : null
        });
      });
      return results;
    }
    """


async def _dismiss_overlays(page: Page) -> None:
    """Best-effort close of cookie / login nudge modals that block SRP."""
    for sel in [
        "button:has-text('Got it')",
        "button:has-text('Accept')",
        "button:has-text('Close')",
        "button[aria-label='Close']",
    ]:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible():
                await loc.click(timeout=1_500)
                await page.wait_for_timeout(400)
        except Exception:
            continue


async def _extract_cards(page: Page) -> list[dict[str, Any]]:
    try:
        await page.wait_for_selector(SRP_READY, timeout=18_000)
    except Exception:
        console.print("[yellow]No job cards found on page (timeout or empty).[/yellow]")
        try:
            n = await page.locator("a[href*='job-listings']").count()
            console.print(f"  (fallback job-listings anchors: {n})")
        except Exception:
            pass
        return []

    await _dismiss_overlays(page)
    cards = await page.evaluate(_js_extract_cards())
    if cards:
        return cards

    console.print("[yellow]Primary card parse empty; using link fallback.[/yellow]")
    return await page.evaluate(
        """
        () => {
          const out = [];
          const seen = new Set();
          document.querySelectorAll('a[href*="job-listings"]').forEach(a => {
            const href = a.href;
            const title = (a.innerText || '').trim();
            if (!href || !title || seen.has(href)) return;
            seen.add(href);
            out.push({ title, url: href });
          });
          return out.slice(0, 40);
        }
        """
    )


async def collect_jobs(
    session: BrowserSession,
    prefs: Preferences,
    *,
    max_jobs: int | None = None,
) -> list[JobListing]:
    """
    Walk configured queries x locations x pages; return unique JobListing objects.
    Sequential single-tab navigation for lower burst risk.
    """
    page = session.page
    assert page
    seen: set[str] = set()
    jobs: list[JobListing] = []
    limit = max_jobs or prefs.search.max_jobs_per_run
    locations = prefs.search.locations or [None]
    combinations = max(1, len(prefs.search.queries) * len(locations))
    # Prevent the first broad result page from consuming the entire run cap.
    # Share the cap across configured query/location pairs, allowing page 2
    # only when page 1 did not yield enough unique listings for that pair.
    per_combination_limit = max(1, (limit + combinations - 1) // combinations)

    for query in prefs.search.queries:
        for loc in locations:
            combination_added = 0
            for pnum in range(1, prefs.search.pages_per_query + 1):
                if len(jobs) >= limit or combination_added >= per_combination_limit:
                    break
                url = build_search_url(query, loc, pnum)
                console.print(f"[cyan]Search[/cyan] {url}")
                try:
                    await session.goto(url)
                    await session.human_delay(
                        prefs.search.min_delay_seconds,
                        prefs.search.max_delay_seconds,
                    )
                    cards = await _extract_cards(page)
                    console.print(f"  -> {len(cards)} cards")
                    for raw in cards:
                        listing = listing_from_card(raw, source_query=query)
                        if not listing.url or not listing.title:
                            continue
                        fp = listing.fingerprint()
                        if fp in seen:
                            continue
                        seen.add(fp)
                        jobs.append(listing)
                        combination_added += 1
                        if len(jobs) >= limit or combination_added >= per_combination_limit:
                            break
                except Exception as exc:
                    console.print(f"[red]Search error:[/red] {exc}")
                    continue
    return jobs
