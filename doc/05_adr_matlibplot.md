## Chart visualisation technology — Matplotlib first, Chart.js next

### Date
`2023-06-05`

### Status
Proposed

### Context
A technology was needed to render charts (weight trends, medicine consumption, etc.) in the application.

Two categories of solutions were considered:

- **Static charts** (server-rendered image): Matplotlib.
- **Interactive dashboards** (client-side): Chart.js (in-page JS), Dash-Plotly (separate microservice).

### Decision
**Phase 1 — Matplotlib** (static server-rendered charts): chosen to avoid adding a JavaScript dependency
or a microservice before the core application is stable. The data (biometric records, weight history)
does not require real-time filtering in the initial version.

**Phase 2 — Chart.js** (planned): once the static prototype is validated, Chart.js will be evaluated
as a drop-in replacement. It runs in-browser without a build pipeline, making it compatible with the
no-build-step constraint from ADR-11. Dash-Plotly is deferred indefinitely (it would require
a separate microservice — see ADR-03).

### Consequences
- Static Matplotlib charts are generated on-demand server-side and served as images.
- Switching to Chart.js later requires replacing the server-side render path with a JSON data endpoint
  and a JS chart component — scoped work, no architectural change.
- Dash-Plotly is not planned unless interactive dashboards become a core requirement.

### Keywords
- Matplotlib, Chart.js, Dash Plotly, dashboards, charts, data visualisation

### Links
*[2023-06-14]*\
https://matplotlib.org/\
https://www.chartjs.org/\
https://dash.plotly.com/
