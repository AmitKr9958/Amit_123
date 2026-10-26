# Naukri Apply (local-first supervised assistant)

A **production-oriented, local-first** assistant for discovering, scoring, and (optionally) applying to Naukri.com jobs that match a configured Power BI / BI profile.

This is **not** a blind spray bot. It is designed around:

- Persistent browser profile + **manual login / OTP / CAPTCHA** (credentials never stored in code)
- Deterministic eligibility rules first, explainable scores
- Human-paced, low-concurrency navigation
- SQLite tracking and deduplication
- Pause on external career sites and unknown screening questions
- `auto_submit: false` by default

> **Account risk & ToS**  
> Automated bulk applying can violate Naukri’s Terms of Service and may lead to restrictions. Use only on your own account, keep volume low, supervise every run, and prefer quality over quantity. This project does not bypass security controls.

---

## Architecture (short)

```
config/preferences.yaml   → roles, locations, skills, caps, weights
data/profile.yaml         → verified personal facts (gitignored)
data/browser_profile/     → Playwright persistent session
data/applied.db           → seen / scored / applied history

src/
  browser.py   persistent context + auth pause
  search.py    multi-query discovery + card extraction
  extract.py   experience / salary / freshness parsers
  score.py     deterministic relevance + hard exclusions
  apply.py     supervised apply flow
  tracker.py   SQLite
  cli.py       login | run | status
```

Ideas adapted from open-source Naukri bots (Selenium multi-tab search, CSV history) and stronger patterns from local agent systems (persistent session, scoring before apply, approval gates). Selectors are heuristic and will need occasional updates when Naukri redesigns the UI.

---

## Setup

```bash
git clone https://github.com/AmitKr9958/Amit_123.git naukri-apply
cd naukri-apply

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

cp .env.example .env
cp data/profile.example.yaml data/profile.yaml
# Edit data/profile.yaml with verified facts only
# Edit config/preferences.yaml for roles / locations / caps
```

---

## Usage

```bash
# 1. One-time (or when session expires): open browser and log in manually
python -m src.cli login

# 2. Dry-run: search + score, write to SQLite, print table (no apply).
#    Eligible jobs are saved as QUEUED and picked up by step 3.
python -m src.cli run

# 3. Supervised apply for eligible jobs (still pauses; auto_submit=false)
python -m src.cli run --apply

# 4. Recent outcomes
python -m src.cli status
```

Or after `pip install -e .`:

```bash
naukri-apply login
naukri-apply run
naukri-apply run --apply
naukri-apply status
```

---

## Preferences (your Power BI profile defaults)

Already seeded in `config/preferences.yaml`:

| Setting | Default |
|--------|---------|
| Roles | Power BI Developer, Senior Power BI Developer, Power BI Engineer/Consultant, BI Developer, Data Analyst, Reporting Analyst, MIS Analyst, BI Team Lead |
| Skills | Power BI, DAX, Power Query, SQL, Excel, Power Automate, dashboards, reporting |
| Experience | ~11 total / ~10 relevant |
| Locations | Delhi, Gurugram/Gurgaon, Noida, Jaipur (+ explicit remote only) |
| Min salary | ₹11 LPA (job rejected only if disclosed salary ceiling is below this) |
| Freshness | prefer ≤ 48 hours |
| Competition | prefer < 50 applicants (ideal < 25) |
| Daily cap | 30 |
| Concurrency | 1 |

Tune freely. Hard exclusions (intern/fresher keywords, junior experience ceilings) override score.

---

## Safety defaults

| Control | Behaviour |
|--------|-----------|
| Credentials | Never in repo; manual browser login only |
| CAPTCHA / OTP / MFA | Always pause for human |
| `auto_submit` | `false` — you confirm |
| External company sites | Flagged; optional pause |
| Unknown screening questions | Pause; answer only from verified profile |
| Invented facts | Forbidden by design |
| Rate limiting | Human-like delays + daily cap |

---

## Optional integrations

**Telegram** — set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.  
Run summaries and successful applies are posted when configured.

**LLM screening drafts** — set `OPENAI_API_KEY` and/or `GEMINI_API_KEY`.  
Common fields (notice period, expected CTC, name, …) map **deterministically** from `data/profile.yaml`. Free-text questions may get an LLM draft instructed to use **only** profile facts (or reply `INSUFFICIENT_FACTS`). Drafts always surface for review; sensitive topics force review.

```bash
# example .env fragments
TELEGRAM_BOT_TOKEN=123:abc
TELEGRAM_CHAT_ID=987654321
# OPENAI_API_KEY=sk-...
```

## What this does *not* do

- Silent AI answers without review
- Multi-board (LinkedIn / Indeed) — out of scope for this repo
- Guaranteed unbroken selectors forever — Naukri changes UI; extraction is heuristic
- Cloud headless runs from datacenter IPs (intentionally local)
- Bypassing CAPTCHA, OTP, or MFA

---

## Scheduling (Windows)

```powershell
# once
.\scripts\setup_task.ps1
# task runs scripts\run_daily.bat at 09:00 (dry-run by default)
# edit run_daily.bat to enable --apply when you are ready
```

Linux/macOS: use `scripts/run_daily.sh` with cron.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest tests/ -q
```

CI (`.github/workflows/ci.yml`) runs both on every push and PR.

> **Unattended runs:** the apply flow asks for confirmation in the terminal. Scheduled
> runs should stay dry-run (the default in `scripts/run_daily.*`); use `--apply` only
> in a session you are watching.

---

## License

MIT. Use at your own risk. Respect Naukri’s terms and applicable law.
