"""Naukri search URL generation."""
import re
from urllib.parse import quote


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def build_search_urls(cfg: dict) -> list[tuple[str, str]]:
    results = []
    for keyword in cfg["keywords"]:
        for location in cfg["locations"]:
            k, loc = slug(keyword), slug(location)
            base = f"https://www.naukri.com/{k}-jobs"
            if loc and loc != "remote":
                base += f"-in-{loc}"
            query = f"k={quote(keyword)}"
            if location:
                query += f"&l={quote(location)}"
            for page in range(1, int(cfg["max_pages_per_search"]) + 1):
                page_url = base if page == 1 else f"{base}-{page}"
                results.append((f"{keyword} | {location} | page {page}", f"{page_url}?{query}"))
    return results
