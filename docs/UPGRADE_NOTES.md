# Repository upgrade notes

## Reference repositories reviewed

This branch applies selected design ideas from the repositories previously requested for review:

- [crissy-coder/auto_Apply](https://github.com/crissy-coder/auto_Apply): clear application outcomes, profile-grounded answers, and explicit handling for unknown screening questions.
- [abhayiitbhu/jobs-auto-apply](https://github.com/abhayiitbhu/jobs-auto-apply): configuration-driven filters and deferred handling when facts are missing.

This is a targeted upgrade of the existing Python/Playwright application, not a wholesale copy or merge of another project's code. Platform selectors and application flows still require live validation.

## Changes in this branch

- Treat a job's posting age as a hard gate: unknown posting age or age beyond `profile.max_posting_age_hours` means the job is not eligible for the apply queue.
- Treat unknown or out-of-scope locations as hard exclusions. Jobs must match a configured preferred location or an explicitly allowed remote location.
- Keep the existing salary ceiling and company blacklist exclusions.
- Block `application.auto_submit: true` from the CLI apply flow. Use the supervised path and verify each result instead of assuming an application succeeded.
- Add regression tests for stale jobs, missing posting age, and out-of-scope locations.

## Important caveat

The code and tests in this branch have been updated through GitHub's file API. A passing CI run is required before merge. CI tests scoring and other automated code paths; it does not guarantee Naukri's live DOM selectors still work or prove that a live application was submitted successfully. First run `python -m src.cli run` (dry-run), inspect the results, and only then use `python -m src.cli run --apply` while watching the browser and terminal.

## VS Code update commands

From the existing project folder, commit or stash local edits first, then run:

```powershell
git fetch origin
git switch fix/production-readiness-review
git pull origin fix/production-readiness-review
```

If the branch does not yet exist locally:

```powershell
git fetch origin
git switch --track origin/fix/production-readiness-review
```

To return to the main branch later:

```powershell
git switch main
git pull origin main
```
