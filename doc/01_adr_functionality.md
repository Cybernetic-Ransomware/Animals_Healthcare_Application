## Core functionality scope of the Animals Healthcare Application

### Date
`2023-06-04`

### Status
In-building

### Context
A list of main functions was needed to define the business scope of the first version of the application
and to decide what functionality should be deferred to future releases.

### Decision
Initial brainstorm produced the following feature list:

In scope (first version):
- Animal profiles (age, weight, size, food preferences, etc.)
- User profiles (owner and carers)
- Healthcare place and vet profiles (address, historical prices, ratings)
- Medical calendars (visits, feeding periods, medicine dosage)
- Medical record storage (.pdf attachments via CouchDB — see ADR-08)
- Static charts on demand (weight, medicine consumption)
- Visit notifications via at least one channel (Discord implemented; SMS/email deferred)

Deferred to future iterations:
- Sticky-note kanban for feeding period tracking
- Printable PDF reports
- Google Calendar synchronisation
- Interactive dashboards (Dash-Plotly microservice — see ADR-05)
- All notification channels beyond Discord (SMS, WhatsApp, Messenger)
- Direct chat between users

### Consequences
The feature set was scoped to an achievable first version, leaving a documented backlog for future iterations.
Deferred features are recorded here rather than in code as TODO comments.

### Keywords
- init, functionality, scope of project

### Links
