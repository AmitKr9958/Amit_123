# Naukri Job Assistant

A Windows-first Python + Playwright assistant to discover, filter and rank Naukri jobs, prevent duplicates, track applications, open listings in the same persistent browser profile, and optionally prefill clearly labelled non-sensitive form fields.

## What is automated

- Search role/location combinations in Delhi, Gurugram, Noida and explicit Remote listings.
- Collect Naukri job-card fields with selector fallbacks.
- Filter by required job keywords, exclusion terms, experience range, posting age and salary when a parseable salary is shown.
- Score role/skill/location/freshness matches and explain why listings were filtered.
- Deduplicate jobs and keep history in a local SQLite database.
- Export the shortlist and status table to CSV.
- Open a chosen job in the same visible, persistent Playwright browser profile used for login.
- After you manually click Apply and open a form, optionally prefill blank fields only when the visible field label strongly matches profile data in your local ignored `config.json`.

## Human confirmation is mandatory

The program **never clicks Apply, Submit, Save and Apply, Send, or final confirmation buttons**. It never selects radio/checkbox answers. It never fills phone/email/address, date of birth, PAN/Aadhaar/passport, bank details, gender, marital status, or other sensitive fields. It skips form assistance on external company portals. You check every prefilled answer and submit manually. A status is only recorded as `applied` when you confirm it in the CLI.

If the site shows CAPTCHA, OTP prompts, login expiry, unusual activity, access denial or a rate-limit notice, stop and resolve it manually. The tool does not solve or bypass site protections. Automated browsing may be limited by Naukri's current terms; check the current terms and use this at your own discretion.

## Install (Windows PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
.\install.ps1
```

This creates a Python virtual environment, installs dependencies and Playwright Chromium, and copies the example config to ignored `config.json`.

Then sign in manually:

```powershell
.\run.ps1 login
```

A visible browser opens. Sign in yourself, complete any OTP/CAPTCHA on Naukri, and then press Enter in the terminal to close the browser. Login cookies stay in `data/browser-profile`, not in source files.

## Daily usage

Search, filter, score and track (preview-only; no applications submitted):

```powershell
.\run.ps1 search
```

List saved jobs:

```powershell
.\run.ps1 list
.\run.ps1 list --status saved
.\run.ps1 list --status excluded
```

Open a saved job in the same logged-in browser profile for human review:

```powershell
.\run.ps1 open JOB_ID
```

The browser page stays open while the terminal waits. Review the listing and click Apply yourself if appropriate. After the application form is open, press Enter to prefill eligible blank fields (or type `s` to skip). Check every field and manually complete/submit the application. The CLI lets you record `applied` only if the site confirmed success, or `reviewed` if you did not submit.

Track status and export:

```powershell
.\run.ps1 status JOB_ID applied
.\run.ps1 export
```

## Configure your targets

Edit local `config.json` (gitignored) to change role keywords, locations, exclusion terms, salary floor, experience range, freshness, number of pages, minimum score and per-run scan cap. Defaults target 5–12 years, 5 days freshness, salary floor ₹16 LPA, Delhi/Gurugram/Noida plus Remote (only when explicitly shown), and three pages per query.

The example `applicant` fields are blank. Fill these locally with accurate facts before using prefill; CTC fields are only eligible for prefill when `ctc_disclosure` is explicitly set to `numbers`. Never put secrets or credentials in the config.

## Repository review

- [codewithanuj28/naukri-auto-apply](https://github.com/codewithanuj28/naukri-auto-apply): Playwright, configurable search and duplicate history.
- [lordzohar/Naukri-autoapply-bot](https://github.com/lordzohar/Naukri-autoapply-bot): Naukri result-card selectors, search and CSV logging.
- [pncodes10/Naukri-Automation](https://github.com/pncodes10/Naukri-Automation): modular job utilities, profile prompts and history ideas.
- The supplied AIHawk URL resolves to [feder-cr/invisible_dots](https://github.com/feder-cr/invisible_dots), a general-purpose local computer agent, so it is not treated as verified AIHawk source.
- [suxrobGM/jobpilot](https://github.com/suxrobGM/jobpilot): job-fit scoring, status/campaign tracking and reviewable workflows.

No repository is copied wholesale. This implementation uses patterns rather than merging entire codebases with unrelated stacks.

## Local data and troubleshooting

- `data/browser-profile/`: authenticated browser profile; do not share it.
- `data/jobs.sqlite3`: local job tracking.
- `exports/naukri_jobs.csv`: exported tracker.
- `config.json`: local settings, ignored by Git.
- Run tests with `python -m unittest discover -s tests -v`.

Naukri markup changes often, and no third-party code can guarantee every selector or form. No AI API key is needed; matching and prefill run locally.

## License

MIT.
