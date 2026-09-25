## Chart visualisation technology — Chart.js

### Date
`2023-06-05`

### Status
Done

### Context
A technology was needed to render charts (weight trends, medicine consumption, etc.) in the application.

Two categories of solutions were considered:

- **Static charts** (server-rendered image): Matplotlib.
- **Interactive dashboards** (client-side): Chart.js (in-page JS), Dash-Plotly (separate microservice).

Originally, a two-phase plan was proposed: a static Matplotlib prototype first, with Chart.js
evaluated as a later drop-in replacement. Phase 1 (Matplotlib) was never implemented — by the time
chart work actually started, the frontend architecture had already evolved to htmx + native
`<dialog>` (ADR-11), with no build pipeline and partial-page rendering as the established pattern.
Chart.js was adopted directly as the first and only chart implementation (PR #59, merged 2026-09-24).

### Decision
**Chart.js**, vendored locally under `static/js/vendor/` (no CDN dependency), consistent with the
no-build-step constraint from ADR-11. Chart data is passed from the view to the template as plain
context, serialised into the page via Django's `json_script` template filter, and read by a small
vendored JS module (`biometric_charts.js`) that constructs one `Chart` instance per `<canvas>`. No
server-side image rendering and no dedicated JSON/REST endpoint were introduced — the chart is a
progressive enhancement over the server-rendered history table, which remains the no-JS fallback.

A dedicated biometric JSON API is not required for chart rendering. Any future public API remains a
separate architectural decision covered by ADR-07.

Dash-Plotly was not pursued — it would require a separate microservice (see ADR-03) and interactive
dashboards were never a core requirement.

### Consequences
- Chart.js renders client-side from data embedded via `json_script`; no server-side chart image
  generation exists or is planned.
- No JSON/REST API endpoint backs the charts; ADR-07 (DRF) remains a separate, still-Proposed
  decision, unaffected by this choice.
- The server-rendered history table stays the accessibility / no-JS fallback for every chartable
  measurement.
- Adding another chartable numeric measurement type only requires shaping it into the existing
  `chart_series` contract on the backend — no new JS is needed, since the frontend renders series
  generically by label/unit/points.
- Dash-Plotly remains out of scope unless interactive dashboards become a core requirement.

### Keywords
- Matplotlib, Chart.js, Dash Plotly, dashboards, charts, data visualisation

### Links
*[2023-06-14]*\
https://matplotlib.org/\
https://www.chartjs.org/\
https://dash.plotly.com/
