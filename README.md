# Naukri Job Assistant

A Windows-first Python + Playwright assistant to discover and rank Naukri jobs, prevent duplicates, and track applications locally. Preview-first; no unattended application submission. See setup instructions and inspirations in this README.

## Safe workflow
1. Run `install.ps1` in PowerShell.
2. Run `run.ps1 login` and sign into Naukri manually in the visible browser.
3. Run `run.ps1 search` to discover and score jobs.
4. Run `run.ps1 list` or `run.ps1 export` to review results.
5. Use `run.ps1 open JOB_ID` to inspect the posting and submit manually. Then track it using `run.ps1 status JOB_ID applied`.

The app does not store credentials, bypass CAPTCHA, or auto-submit applications. Local profile and tracker files are ignored by Git. Naukri's page layout may change.

## Repository review
- `codewithanuj28/naukri-auto-apply`: Playwright, config, freshness filters, dedupe, dry-run.
- `lordzohar/Naukri-autoapply-bot`: Selenium, result collection, CSV logs and selector examples.
- `pncodes10/Naukri-Automation`: modular utilities and profile-aware filtering; npm test script is a placeholder.
- `feder-cr/Jobs_Applier_AI_Agent_AIHawk`: GitHub lookup resolved to `feder-cr/invisible_dots`, a general computer-agent project, so it is not assumed to be AIHawk source.
- `suxrobGM/jobpilot`: campaign workflow, local agent, matching and application tracking.

No repository was copied wholesale. This project uses ideas rather than reusing whole codebases. Always respect Naukri's current Terms of Service.

## License
MIT.
