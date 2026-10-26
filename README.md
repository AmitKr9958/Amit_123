# Naukri Job Assistant

A Windows-first Python + Playwright assistant to discover and rank Naukri jobs, prevent duplicates, and track applications locally. Preview-first; no unattended application submission. Setup: run `install.ps1`, then `run.ps1 login`, then `run.ps1 search`. Use `run.ps1 list` and `run.ps1 export` to inspect results. Open jobs with `run.ps1 open JOB_ID`; record your own status using `run.ps1 status JOB_ID applied` after you submit yourself.

## Safety
The browser is visible and uses a local persistent profile. Sign in manually and solve OTP/CAPTCHA yourself. The app does not store credentials, bypass verification, or auto-submit. Local profile/database/export files are gitignored. Naukri's page markup can change.

## Repository review
- `codewithanuj28/naukri-auto-apply`: Playwright, config, duplicate handling, filters, dry run.
- `lordzohar/Naukri-autoapply-bot`: Selenium, browser search and CSV results.
- `pncodes10/Naukri-Automation`: modular AI/job utilities; current package's test command is a placeholder.
- `feder-cr/Jobs_Applier_AI_Agent_AIHawk`: GitHub lookup resolved to `feder-cr/invisible_dots`, a general computer-agent project. The intended AIHawk repo may have moved or been renamed, so no implementation was attributed to it.
- `suxrobGM/jobpilot`: broader campaign workflow, match scoring, tracking, and review-oriented networking.

This implementation reuses concepts, not third-party code wholesale. Always comply with Naukri's current Terms of Service. License: MIT.
