# Naukri Apply (local-first supervised assistant)

A local-first assistant for discovering, scoring, and preparing applications for Naukri.com jobs that match a configured Power BI / BI profile. **Microsoft Edge is the default browser.**

It automates repetitive search and form-filling steps while keeping account verification and the final submission under your control.

- Persistent Microsoft Edge profile; reuse the signed-in session across runs
- If logged out, open the login page and wait while you complete password / OTP / CAPTCHA / MFA manually
- Deterministic eligibility rules, explainable scores, SQLite tracking and deduplication
- Fill supported form fields using verified facts from `data/profile.yaml`
- Pause for unknown screening questions, external company sites, and final review
- Final application submission is always manual; the program will not click the final Submit/Apply button
- No passwords or API keys committed to source

> **Account risk & Terms of Service**  
> Automated bulk applying may violate a job site's terms or lead to account restrictions. Use this tool only on your own account, respect site rules, and review each application. The project does not bypass OTP, CAPTCHA, MFA, or other security controls.

## How the workflow works

1. Open Microsoft Edge with a dedicated persistent profile at `data/edge_profile/`.
2. Reuse an authenticated session. If the session expires, complete verification manually in Edge.
3. Search configured queries and locations; extract job details.
4. Score jobs and skip duplicates/ineligible or stale listings.
5. Open eligible listings and fill supported fields from your verified profile.
6. Pause when it cannot safely answer a question or when a company-site redirect is detected.
7. You review the completed application and click the final submit button yourself.
8. Record the result in the local SQLite tracker.

Selectors are heuristic and may need maintenance when Naukri changes its UI. No tool can guarantee every application form is supported.

## Setup (Windows PowerShell)

```powershell
git clone https://github.com/AmitKr9958/Amit_123.git naukri-apply
Set-Location .\naukri-apply

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"

# Copy the sample profile, then edit it with verified facts only.
if (-not (Test-Path ".\data\profile.yaml")) {
    Copy-Item ".\data\profile.example.yaml" ".\data\profile.yaml"
}
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

Install Microsoft Edge if it is not already installed. The default `BROWSER_CHANNEL=msedge` launches installed Edge through Playwright. The browser profile is stored separately at `data/edge_profile/`, not in your everyday Edge profile.

If Edge does not launch, verify that Microsoft Edge is installed and up to date. You can explicitly set the browser in the current PowerShell session:

```powershell
$env:BROWSER_CHANNEL = "msedge"
$env:HEADLESS = "false"
```

## Usage

Run these commands from the repository root with the virtual environment activated.

```powershell
# 1. Open Edge and sign in once. Complete OTP/CAPTCHA/MFA manually if requested.
python -m src.cli login

# 2. Dry run: search, score, and track eligible jobs; no application forms opened.
python -m src.cli run

# 3. Prepare eligible applications: open forms and fill supported fields.
#    Review each form and click the final Submit button yourself.
python -m src.cli run --apply

# 4. See tracked outcomes
python -m src.cli status

# Initialize the local database if needed
python -m src.cli init-db
```

The same Edge session/profile is reused between commands. To use a different profile directory, set `BROWSER_USER_DATA_DIR` in your environment. Do not point this tool at your everyday Edge profile while Edge is already running.

## Preferences

Defaults in `config/preferences.yaml` are tailored to the current profile and can be edited:

| Setting | Default |
|---|---|
| Roles | Power BI Developer, Senior Power BI Developer, BI Developer, Data Analyst, Reporting/MIS Analyst |
| Locations | Delhi, Gurugram/Gurgaon, Noida, Jaipur; explicit remote roles allowed |
| Minimum salary | ₹11 LPA when a reliable salary is disclosed |
| Freshness | Up to 48 hours |
| Applicant count | Prefer fewer than 50; ideally fewer than 25 |
| Daily application cap | 30 |
| Concurrency | 1 |

The cap is a maximum, not a target. Do not increase activity to evade a site's limits.

## Profile privacy

- Keep `data/profile.yaml`, resume files, browser profile, database, and `.env` local.
- Populate the profile with accurate information only.
- Do not store passwords, OTPs, session cookies, or other secrets in YAML or source code.
- Screening answers are drafted from profile facts only. Unknown or sensitive questions require your judgment.

## Scheduling

Scheduled tasks should run search/scoring in dry-run mode by default. Do not run unattended application submission. If using Windows Task Scheduler, keep the machine awake and run tasks only in a session you control.

## Development

```powershell
ruff check .
pytest -q
```

The tests validate code behavior, not the live Naukri UI. Always verify a small dry-run before using `--apply`.

## License

MIT. Use at your own risk. Respect site terms and applicable law.
