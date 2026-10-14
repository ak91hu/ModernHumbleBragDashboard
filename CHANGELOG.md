# Modern dashboard update

## Follow-up: Strava data export timestamp

- Display the last successful Strava export below the page heading in Hungarian and English, including on mobile.
- Record UTC completion times with a CSV fingerprint and display them in Budapest time with daylight-saving conversion.
- Successful syncs refresh the timestamp even when there are no new activities; failed syncs preserve the previous export time.
- 41 regression tests pass, including metadata validation, failed-sync recovery and winter/summer time conversion.

## Follow-up: typical activity starting times

- Added a personal time-of-day summary to the overview and a full analysis of dayparts, start hours, sport preferences and weekday/hour patterns to Trends & analysis.
- All classifications use recorded local starting times; activities count once, all date/sport filters apply and tied preferences are preserved.
- 38 unique tests pass, including time boundaries, local offsets, long sessions and empty profiles. Static rendering covers all eight trend charts.
- The live GitHub repository's five most recent scheduled Strava runs were successful, including the run on 2026-10-13.
- Render deployment depends on the linked GitHub branch and automatic-deployment configuration.

## Follow-up: trend display and more personal bests

- Added explicit graph container heights with parent-responsive sizing to support graphs mounted during navigation. Loading no longer hides the chart area, and chart data uses plain arrays with explicit date/category axes.
- Added sport-specific records, qualifying running average-pace records, recorded peak speed, climbing density, kudos and Strava segment-PR counts.
- Added daily, weekly and monthly volume bests, busiest day, most active month and longest active streak, with links to the matching activities.
- 41 record cards are available for the retained 2026 data with all sports selected. Missing measurements do not generate artificial zero records.
- 30 unique regression tests pass; the five actual trend figures also undergo SVG/PNG rendering checks. The user confirmed that the trend graphs now display correctly after the fix and a refresh.

## Experience

- Rebuilt the interface with a coherent visual identity, responsive navigation and six complete views.
- Added date presets/custom ranges, progress metric selection, dark mode and a Hungarian/English interface.
- Added annual goals, favorite activities, activity details, a complete searchable/paginated log and CSV download.
- Added training rhythm and sport distribution charts, clickable activity calendar and sport-aware running pace records.

## Correctness and reliability

- Moving/elapsed efficiency now uses minutes consistently.
- Cumulative distance is recomputed from filtered activities.
- Local activity dates remain local, and calendar weeks no longer collapse at ISO year boundaries.
- Missing datasets, empty selections, invalid goals and missing heart-rate measurements have usable states.
- Incremental sync preserves historical data and writes atomically only after a successful API response.

## Validation

- 41 passing analytics, Flask/Dash callback, chart/record, time-profile, export-metadata and sync regression tests.
- All six views serialized successfully using the real dataset (955 activities, 2022–2026).
- View validation includes both languages/themes and unique component identifiers.
- Python compilation and local HTTP/asset checks passed.
- No connected browser was available for screenshot, mobile viewport or browser-storage persistence verification.

Production deployment depends on the service's linked GitHub branch and Render configuration; verify it after publishing source updates.
