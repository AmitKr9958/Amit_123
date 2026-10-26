"""Visible persistent Playwright browser and resilient job-card extraction."""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

STOP_PHRASES = (
    "too many requests", "unusual activity", "verify you are human", "captcha",
    "temporarily blocked", "please try again later", "daily quota",
    "access denied", "suspicious activity",
)


class NaukriBrowser:
    def __init__(self, cfg):
        self.cfg, self.pw, self.context = cfg, None, None

    def __enter__(self):
        self.pw = sync_playwright().start()
        bcfg = self.cfg["browser"]
        profile = Path(__file__).resolve().parents[1] / "data" / "browser-profile"
        profile.mkdir(parents=True, exist_ok=True)
        kwargs = {
            "headless": bool(bcfg.get("headless", False)),
            "slow_mo": int(bcfg.get("slow_mo_ms", 80)),
            "viewport": {"width": 1365, "height": 900}
        }
        channel = bcfg.get("channel", "chromium")
        if channel in ("chrome", "msedge"):
            kwargs["channel"] = channel
        self.context = self.pw.chromium.launch_persistent_context(str(profile), **kwargs)
        self.context.set_default_navigation_timeout(int(bcfg.get("navigation_timeout_ms", 45000)))
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.context:
            self.context.close()
        if self.pw:
            self.pw.stop()

    def new_page(self):
        return self.context.pages[0] if self.context.pages else self.context.new_page()

    @staticmethod
    def _first_text(locator, selectors, default=""):
        for selector in selectors:
            try:
                item = locator.locator(selector).first
                if item.count():
                    value = item.inner_text(timeout=1500).strip()
                    if value:
                        return re.sub(r"\s+", " ", value)
            except Exception:
                continue
        return default

    @staticmethod
    def _first_attr(locator, selectors, attr, default=""):
        for selector in selectors:
            try:
                item = locator.locator(selector).first
                if item.count():
                    value = item.get_attribute(attr, timeout=1500)
                    if value:
                        return value.strip()
            except Exception:
                continue
        return default

    @staticmethod
    def stop_reason(page):
        try:
            body = page.locator("body").inner_text(timeout=2500).lower()
        except Exception:
            body = ""
        for phrase in STOP_PHRASES:
            if phrase in body:
                return phrase
        current = page.url.lower()
        if "naukri.com/nlogin" in current or "login.naukri.com" in current:
            return "login prompt/session expired"
        return None

    def extract_jobs(self, page, search_query, search_url):
        page.wait_for_timeout(900)
        cards = None
        for selector in (".srp-jobtuple-wrapper", ".cust-job-tuple", "article.jobTuple"):
            try:
                candidate = page.locator(selector)
                if candidate.count():
                    cards = candidate
                    break
            except Exception:
                continue
        if cards is None:
            return []
        results = []
        for index in range(cards.count()):
            card = cards.nth(index)
            title = self._first_text(card, ["a.title", "h2 a"], "Unknown")
            url = self._first_attr(card, ["a.title", "h2 a", "a[href*='job-listings']"], "href")
            if not url:
                continue
            if url.startswith("/"):
                url = "https://www.naukri.com" + url
            if not url.startswith("https://www.naukri.com/"):
                continue
            company = self._first_text(card, [".comp-name", ".comp-dtls-wrap a", "a.subTitle", "[class*='company']"], "Unknown")
            location = self._first_text(card, [".loc-wrap", ".locWdth", "[class*='location']", "[class*='loc']"], "Unknown")
            experience = self._first_text(card, [".exp-wrap", ".expwdth", "[class*='experience']", "[class*='exp']"], "")
            salary = self._first_text(card, [".sal-wrap", "[class*='salary']", "[class*='sal']"], "")
            posted = self._first_text(card, "[class*='date'], [class*='posted'], [class*='time']".split(", "), "")
            summary = self._first_text(card, [".job-desc", "[class*='description']", "[class*='tag-li']"], "")
            job_id = card.get_attribute("data-job-id") or self._first_attr(card, ["[data-job-id]"], "data-job-id")
            if not job_id:
                match = re.search(r"(?:job-listings/[^/]*-)([0-9a-fA-F]{6,})(?:\?|$)", url)
                job_id = match.group(1) if match else url.split("?")[0]
            results.append({
                "job_id": job_id, "title": title, "url": url, "company": company,
                "location": location, "experience": experience, "salary_text": salary,
                "posted_text": posted, "description": summary,
                "search_query": search_query, "source_url": search_url
            })
        unique, seen = [], set()
        for job in results:
            key = job["url"].split("?")[0].rstrip("/")
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique
