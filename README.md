# Naukri Job Assistant

A Windows-first Python + Playwright assistant to discover and rank Naukri jobs, prevent duplicates, and track applications locally. Preview-first; no unattended application submission.

## Features
- Search Power BI, BI, Data Analyst, Reporting and MIS roles across Delhi, Gurugram, Noida and Remote.
- Use a visible browser with a persistent local profile; sign in manually.
- Discover job cards, score skill/role matches, and store jobs in SQLite.
- Deduplicate on rescans and track status from saved to applied/interview/offer.
- Export the tracker to CSV.
- Unit tests and GitHub Actions workflow included.

## Install (Windows PowerShell)
```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
.\install.ps1
.\run.ps1 login
.\run.ps1 search
.\run.ps1 list
.\run.ps1 export
```

To review and mark a job after manually submitting:
```powershell
.\run.ps1 open JOB_ID
.\run.ps1 status JOB_ID applied
```

The browser profile and database remain local and are ignored by Git. The tool does not store credentials, bypass CAPTCHA/OTP, or automatically submit applications. Naukri page markup may change, so job-card extraction may need maintenance. Confirm current Naukri Terms of Service before use.

## Repository review and inspirations
- [codewithanuj28/naukri-auto-apply](https://github.com/codewithanuj28/naukri-auto-apply): Playwright, configuration, duplicate handling and dry-run.
- [lordzohar/Naukri-autoapply-bot](https://github.com/lordzohar/Naukri-autoapply-bot): Selenium job discovery and CSV results.
- [pncodes10/Naukri-Automation](https://github.com/pncodes10/Naukri-Automation): modular utilities and job filters; its current npm test command is a placeholder.
- The AIHawk URL lookup resolved to [feder-cr/invisible_dots](https://github.com/feder-cr/invisible_dots), a general-purpose computer agent, so I have not assumed it is the intended AIHawk code.
- [suxrobGM/jobpilot](https://github.com/suxrobGM/jobpilot): campaign workflows, matching, tracking and review-oriented outreach.

No repository was copied wholesale. This project uses concepts rather than third-party code copied wholesale.

## Run tests
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

License: MIT.
