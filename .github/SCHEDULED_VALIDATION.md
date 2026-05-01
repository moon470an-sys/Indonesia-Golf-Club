# Scheduled Data Validation

This repository runs an automated data-quality workflow that watches the JSON
data the site depends on. Defined in
[`.github/workflows/data-validation.yml`](workflows/data-validation.yml).

## When it runs

| Trigger | Schedule |
|---|---|
| `schedule` cron | Every **Monday at 02:00 UTC** (`0 2 * * 1`) |
| `workflow_dispatch` | Manual trigger from the Actions tab any time |

## Jobs

### 1. `static-validation`

Runs `python validate_data.py` against the JSON files under `data/`.

- Checks: schema/required-field, Indonesia bbox sanity for coordinates,
  numeric/currency ranges, accounting identity (A = L + E ±5%), cross-file
  ID consistency, source URL structure, MAD-based outlier detection on fees.
- The validator exits **non-zero** when any **CRITICAL** finding is recorded
  (missing files, duplicate IDs, out-of-bbox coords, negative revenue, ...).
- The full machine-readable report (`validation_raw.md`) is uploaded as the
  `validation_raw` artifact on every run, success or failure.
- **On failure**, the workflow opens or updates a GitHub Issue titled
  `[data-validation] CRITICAL issues detected` whose body is the contents of
  `validation_raw.md`. Done via
  [`peter-evans/create-issue-from-file@v5`](https://github.com/peter-evans/create-issue-from-file).
  Subsequent failing runs update the same issue rather than spamming new ones.

#### Note about the optional `../golf_data/` directory

`validate_data.py` historically lived alongside a sibling `golf_data/` folder
(course-level `financials_*.json` and `fees_*.json`). That folder is **not**
published to this repository — only the `site/` tree is. The validator now
detects this and emits a single `info`-level skip message; it does not flag
the missing files as warnings or criticals, so CI is happy with just the
data shipped in `data/`.

If you ever want full coverage in CI, copy or symlink the relevant files into
`data/golf_data/` and adjust `GOLF_DATA` in `validate_data.py` accordingly.

### 2. `live-url-check`

Runs `python check_sources.py --workers 8`. Worker count is capped at 8
(versus 12 locally) to be polite from a shared GitHub-hosted runner egress IP.

- Hits every source URL referenced across the data files (financials_5y,
  course-level financials, fees) and records HTTP status, content-type, and
  content-length to `url_check_report.json`.
- The script never exits non-zero by design — broken external URLs should
  not block CI.
- The report JSON is uploaded as the `url_check_report` artifact.
- A small inline summary script tallies status codes and emits a workflow
  warning when the count of HARD-404 responses exceeds the threshold
  (`HARD_404_THRESHOLD`, default `25`). Adjust the env var on the step if the
  baseline shifts.

## Inspecting results

1. Open the **Actions** tab of the repo.
2. Pick the most recent **data-validation** run.
3. Download the `validation_raw` and/or `url_check_report` artifacts.
4. If a CRITICAL was found, the auto-opened issue has the same content
   inline.

## Local reproduction

```bash
# Static validation (same command CI runs)
python validate_data.py

# URL check with the same worker count CI uses
python check_sources.py --workers 8
```

Both scripts resolve paths relative to their own location (`Path(__file__).parent`),
so they work when invoked from any directory.
