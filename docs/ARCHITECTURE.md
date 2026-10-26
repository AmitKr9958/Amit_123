# Architecture notes

## Design goals

1. **Local-first** – browser profile, SQLite, and profile data stay on your machine.
2. **Supervised** – login, OTP, CAPTCHA, unknown questions, and final submit require human presence by default.
3. **Explainable** – every score has reasons and exclusions; nothing is a black box for eligibility.
4. **Recoverable** – dedup via `job_id`, daily caps, run logs, status history.
5. **Maintainable** – YAML config, small modules, heuristic selectors isolated in `search.py` / `apply.py`.

## Data flow

```
preferences.yaml + profile.yaml
        │
        ▼
  BrowserSession (persistent Chromium)
        │
        ├─ ensure_authenticated()  → manual login if needed
        │
        ▼
  collect_jobs()  → list[JobListing]
        │
        ▼
  score_job()     → ScoredJob (eligible?)
        │
        ▼
  tracker (SQLite)
        │
        ▼
  attempt_apply()  [optional --apply]
        │
        └─ pause on external site / unknown fields
```

## Why Playwright over Selenium here

- Persistent context maps cleanly to “log in once, reuse session”.
- Modern async API and locator model.
- Easier to keep a real (non-headless) window for supervision.

Selectors will still break when Naukri ships UI changes; extraction is deliberately multi-fallback and lives in one place.

## Extension points

| Concern | Where to extend |
|--------|------------------|
| New role keywords | `config/preferences.yaml` |
| Card DOM changes | `src/search.py` → `_extract_cards` |
| Apply button / chat UI | `src/apply.py` |
| Optional LLM answers (facts-only) | `src/ai_answers.py` (always gated by review) |
| Telegram summary | `src/notify.py` reading `TELEGRAM_*` from env |

## Security checklist

- [ ] No password in git
- [ ] `data/profile.yaml` gitignored
- [ ] `data/browser_profile/` gitignored
- [ ] Never click through CAPTCHA programmatically
- [ ] Config models reject unknown YAML keys (typos fail loudly)
- [ ] Apply click asks for confirmation first unless `auto_submit: true`
- [ ] `auto_submit: false` unless you consciously enable it
