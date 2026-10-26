"""
Centralised Naukri DOM selectors (2026 redesign).

Update this file when Naukri changes class names. Prefer data attributes and
stable text where possible; CSS module hashes change frequently.
"""

from __future__ import annotations

# --- Search results page -------------------------------------------------

# Job card containers (try in order)
CARD_SELECTORS = [
    "div.srp-jobtuple-wrapper",
    "div.cust-job-tuple",
    "article.jobTuple",
    "div[class*='jobTuple']",
    "div[class*='srp-jobtuple']",
]

# Title link inside a card
TITLE_SELECTORS = [
    "a.title",
    "h2 a.title",
    "h2 a",
    "a[class*='title']",
    "a[href*='job-listings']",
]

COMPANY_SELECTORS = [
    "a.comp-name",
    "a[class*='comp-name']",
    "span.comp-name",
    "a[class*='comp']",
]

LOCATION_SELECTORS = [
    "span.locWdth",
    "span[class*='locWdth']",
    "span[class*='loc']",
    "li[class*='location']",
    "span.location",
]

EXPERIENCE_SELECTORS = [
    "span.expwdth",
    "span[class*='expwdth']",
    "span[class*='exp']",
    "li[class*='experience']",
]

SALARY_SELECTORS = [
    "span.sal",
    "span[class*='salar']",
    "span[class*='salary']",
]

POSTED_SELECTORS = [
    "span.job-post-day",
    "span[class*='job-post-day']",
    "span[class*='posted']",
    "span.time",
]

APPLICANTS_SELECTORS = [
    "span[class*='applicant']",
    "span[class*='applied']",
]

SKILL_SELECTORS = [
    "ul.tags-gt li",
    "ul[class*='tags'] li",
    "span[class*='skill']",
    "a[class*='skill']",
]

SNIPPET_SELECTORS = [
    "span.job-desc",
    "div[class*='job-description']",
    "span[class*='desc']",
]

# Wait-for any of these to consider SRP loaded
SRP_READY = ", ".join(CARD_SELECTORS)

# --- Job detail / apply --------------------------------------------------

APPLY_BUTTON_TEXTS = [
    "Apply on company site",
    "Apply",
    "I'm interested",
    "Apply now",
]

APPLY_BUTTON_SELECTORS = [
    "#company-site-button",
    "button#company-site-button",
    "button[class*='company-site-button']",
    "[class*='apply-button-container'] button",
    "button:has-text('Apply on company site')",
    "button:has-text('Apply')",
    "a:has-text('Apply on company site')",
    "a:has-text('Apply')",
]

ALREADY_APPLIED_SELECTORS = [
    "text=/already applied/i",
    "button:has-text('Applied')",
    "span:has-text('Applied')",
    "div:has-text('You have already applied')",
]

# Login / session markers
LOGGED_IN_SELECTORS = [
    "a[href*='mnjuser/profile']",
    "div.nI-gNb-drawer__icon",
    "[data-ga-track*='Profile']",
    "div[class*='user-name']",
]

LOGIN_CTA_SELECTORS = [
    "a[title='Jobseeker Login']",
    "a[href*='nlogin']",
    "button:has-text('Login')",
]
