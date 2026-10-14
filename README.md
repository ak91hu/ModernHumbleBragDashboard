# humblebrag.

**Every move counts.** A modern, bilingual Strava dashboard built with Python, Dash and Plotly. This version extends [ModernHumbleBragDashboard](https://github.com/ak91hu/ModernHumbleBragDashboard) and keeps its CSV data pipeline and Render/Gunicorn deployment model.

**Live dashboard:** [Open Humblebrag](https://modernhumblebragdashboard.onrender.com/).

## What's new

- A forest-green and lime visual identity, custom mountain illustration, locally hosted fonts, and a responsive layout.
- Six dedicated views: overview, trends and analysis, activity calendar, goals and challenges, personal bests, and activity log.
- Hungarian and English interface, plus a persistent light/dark theme.
- Last successful Strava data export shown below the page heading in Budapest time, separately from the latest activity date.
- 30-day, 90-day, annual, all-time and custom date ranges, with sport filtering and selectable progress metrics.
- Cumulative progress compared with the previous year for ranges starting on January 1; other ranges use the preceding period of equal length. Comparison dates are shown in the overview.
- Weekly volume, sport distribution by moving time, training rhythm, distance/speed scatter and measured heart-rate distribution.
- Typical local starting times: four dayparts with counts/percentages, a 24-hour start distribution, sport-specific preferences and a weekday/hour heatmap. The overview includes a compact personal summary.
- A clickable activity heatmap with correct year boundaries, active days, current streak and longest streak.
- Editable annual distance, elevation and activity goals saved in the browser. **Goals cover all sports for their selected year**, independently of dashboard filters.
- Mountain challenges and playful food conversions with clearly labeled estimated energy.
- All matching activities in a searchable, sortable, paginated log; persistent favorites, activity details and direct Strava links.
- Expanded personal bests: individual activity records, highest-volume day/week/month, longest streak, busiest day and most active days in a month; separate records for each Strava sport.
- Running average-pace records for activities of at least 5 km, 10 km, half-marathon and marathon distance; qualifying distances only, with no fabricated split times. Cycling/walking speed records have minimum-distance requirements.
- Recorded peak speed (converted from m/s to km/h), elevation per kilometer, kudos and Strava segment-PR counts where those measurements are available. Record cards open the source activity or matching period activities.
- CSV export of the current date/sport selection. In the activity log, search and favorites filters also apply to export.
- Keyboard-accessible dialogs, Escape to close, focus trapping, skip link and reduced-motion support.
- Corrected moving-time efficiency, filtered cumulative totals, local calendar dates and empty-data handling.
- Incremental, atomic data sync that preserves the previous CSV if the API fails.

## Run locally

Requires Python 3.11 or newer.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Set `PORT` to use another port; set `DASH_DEBUG=1` for development hot reload. The app binds to loopback when started directly. The production `gunicorn app:server` command continues to work.

In the prepared Windows workspace, `./start.ps1` uses the local portable Python runtime when present; otherwise it uses the Python installation on PATH. `.runtime/` is local tooling and is excluded from source packages.

The included `data/activities.csv` is the original repository's data. No Strava credentials are required to view it. A missing or empty CSV produces an empty state without fabricated activities.

## Data sync

Create a Strava API application and obtain a refresh token with `activity:read_all`. Configure these GitHub Actions secrets or local environment variables:

- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REFRESH_TOKEN`

```sh
python scripts/update_data.py         # new activities + a 7-day overlap
python scripts/update_data.py --full  # intentional full-history refresh
```

The overlap refreshes recent edits and kudos. Rows are merged by activity ID and written atomically after a successful fetch. A failed fetch does not alter the existing CSV. An empty full-history response is rejected when existing data is present. Older edits or activities removed on Strava require a successful `--full` refresh.

Successful syncs also save `data/activities.export.json` with the UTC completion time and a SHA-256 fingerprint of the CSV, including successful checks with no new activities. The dashboard displays this time in `Europe/Budapest`, with automatic daylight-saving conversion. Missing, invalid or mismatched metadata displays “time not recorded”; CSV file modification times and activity dates are not treated as export times. The existing action already commits all of `data/`, so the timestamp is deployed with the matching CSV. The bundled timestamp was recovered from the successful [October 13 export step](https://github.com/ak91hu/ModernHumbleBragDashboard/actions/runs/38397555436), whose source CSV matches the bundled file.

The existing GitHub Action runs daily at **05:00 UTC** and supports manual execution. The running dashboard loads the CSV on startup; restart/redeploy it after data changes. On Render, ensure automatic deployment is enabled for commits to the deployed branch.

GitHub schedules can start later than their configured time. Public workflow history was checked on 2026-10-13: the most recent five scheduled runs completed successfully, including [the October 13 run](https://github.com/ak91hu/ModernHumbleBragDashboard/actions/runs/38397555436). This confirms the existing repository's automation; the development workspace is a separate local version.

## Deploy on Render

Connect your repository to a Python Web Service:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:server`

The web service needs no Strava secrets when the GitHub Action supplies the CSV. Keep credentials in the sync environment rather than the public application.

Local edits and the source ZIP do not trigger deployment. First commit/push the application files to the service's linked GitHub branch. With a connected GitHub provider and **Auto-Deploy → On Commit**, Render rebuilds after branch updates, including the data bot's CSV commits. A service created from a public repository URL without a connected Git provider requires manual deploys. Check build filters: excluding `data/` would prevent CSV-only commits from redeploying the dashboard. See [Render's automatic-deploy documentation](https://render.com/docs/deploys#automatic-deploys).

**After CI Checks Pass** only deploys commits with detected passing checks. The current repository's scheduled data bot alone is not a general push-triggered CI setup, so use **On Commit** for this data-refresh deployment flow unless dedicated CI is configured. The account's actual Render settings must be checked through an authenticated connection; they cannot be inferred from the source code.

### Time-of-day calculations

Activities are grouped by their recorded **local start time**: night 00:00–05:59, morning 06:00–11:59, afternoon 12:00–17:59 and evening 18:00–23:59. Date and sport filters apply throughout. Each activity is counted once, even if it continues into another daypart; the activity's entire distance/moving time is assigned to its starting daypart. Counts and percentages describe activity starts, while tied preferences are all shown.

## Validate

```sh
python -m unittest discover -s tests -v
```

The 41 tests exercise data normalization, efficiency, inclusive filtering, local dates, streaks, year boundaries, filtered cumulative values, all six views, both languages/themes, callback responses, unique component IDs, pagination, favorites, goals, activity details, CSV export, sync failure recovery, chart container sizing, sport/period records, time-of-day boundaries/filtering and export metadata/time zones.

An optional static-rendering check exports the actual eight trend chart payloads to SVG and PNG and checks for rendered data marks:

```sh
python -m pip install kaleido
python scripts/verify_chart_export.py
```

It requires an existing Chrome installation for Kaleido's image exporter. Outputs are written to `artifacts/chart-check/`. The app itself does not require Kaleido or a server-side browser.

Static Plotly rendering is checked separately from the application's interactive browser layout. The user confirmed that the previously blank trend graphs now appear after the sizing/loading fix and a refresh. A connected browser for automated application QA was unavailable in the development session; full mobile and keyboard verification still needs a manual check.

## Structure

```text
app.py                    App layout, callbacks and health endpoint
analytics.py              Data normalization and calculations
export_metadata.py        Successful Strava export timestamp and CSV fingerprint
records.py                Sport-specific and period personal bests
charts.py                 Plotly visualizations
views.py                  Dashboard views and activity components
ui.py                     Icons and presentation helpers
assets/                   Styles, illustrations, fonts and keyboard behavior
scripts/update_data.py    Safe incremental Strava sync
tests/test_dashboard.py   Regression and callback tests
tests/test_records_and_charts.py  Chart sizing and personal-best regressions
tests/test_time_profile.py  Local time-of-day calculations and charts
data/activities.csv       Retained Strava activities
Procfile                  Production Gunicorn command
```

Fonts: DM Sans and Manrope, distributed under the SIL Open Font License; licenses are included in `assets/fonts/`. Project license: Apache 2.0, retained from the original repository.
