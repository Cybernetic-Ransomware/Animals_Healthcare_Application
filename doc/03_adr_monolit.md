## Application architecture — monolith with optional microservice extensions

### Date
`2023-06-05`

### Status
Done

### Context
An architecture style was needed for the project. The main options were a monolith or a microservices approach.
Django was already selected (ADR-02), which has a natural affinity with the monolithic model.

### Decision
A **monolith** architecture was chosen, open via APIs to selective microservice extensions where justified.
With a single developer and a rapid-prototype goal, starting with a monolith avoids distributed-systems
complexity (service discovery, inter-service auth, deployment overhead) before the core product is validated.

### Consequences
- All core features (animals, medical notes, notifications) live inside one Django project (`src/ahc/`).
- A future microservice (e.g. interactive dashboards — ADR-05) can be grafted on via a REST API (ADR-07)
  without restructuring the monolith.
- Each new feature should be evaluated: monolith addition vs separate microservice.
  The default is monolith unless the feature has a clearly distinct deployment or scaling requirement.

### Keywords
- architecture, monolith, microservices

### Links
