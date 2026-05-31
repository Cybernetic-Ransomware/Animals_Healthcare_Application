## API framework — decision pending

### Date
`2023-06-05`

### Status
Proposed

### Context
An API layer is needed to support potential microservice extensions (ADR-03) and future external integrations.
No API has been implemented yet — the current application is a server-rendered monolith with no public endpoints.

Candidates under consideration:
- **Django REST Framework (DRF)** — mature, widely adopted, large ecosystem; verbose for simple cases.
- **Django Ninja** — modern, type-annotated (Pydantic), faster to write; smaller community than DRF.
- **FastAPI** — excellent performance and type safety, but would run as a separate service outside Django.
- **GraphQL** — flexible querying; adds client-side complexity and a schema maintenance burden.

### Decision
*Pending.* No API framework has been selected. The decision will be made when the first API endpoint
is required by a concrete feature (e.g. Chart.js data feed, mobile client, or microservice integration).

### Consequences
- Until a decision is made, all data access goes through Django views and Django templates.
- The choice of DRF vs Django Ninja is the most likely outcome given the monolith-first strategy (ADR-03);
  both integrate natively with Django's ORM, auth, and permission system.

### Keywords
- API framework, REST, DRF, Django Ninja, FastAPI, GraphQL

### Links
