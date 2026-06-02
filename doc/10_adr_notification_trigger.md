## Notification delivery — Celery Beat + Django Background Tasks

### Date
`2023-12-19` (updated `2026-05-31`)

### Status
In-building

### Context
The application needs to send time-based notifications to users (e.g. upcoming vet visits).
Key constraints:
- Avoid overwhelming the database with frequent polling.
- Support at least one external channel (Discord is the primary target).
- Work within the existing Django monolith (ADR-03) without adding a separate service.

Options evaluated:
- **django-crontab** — OS-level cron wrapper; simple but couples scheduling to the server's cron daemon.
  No retry logic, no visibility into task state.
- **Celery Beat** — distributed periodic task scheduler; integrates with the Celery worker (Redis broker)
  already used for async tasks. Supports retry, monitoring via Flower, and dynamic schedule updates.
- **Django Background Tasks API** (`ImmediateBackend`) — lightweight in-process runner;
  no separate worker process needed; suitable for short, non-critical tasks.

### Decision
**django-crontab was chosen initially but has since been removed.**
The current stack uses two complementary mechanisms:

1. **Celery Beat** (periodic tasks via `celery_notifications/cron.py`) — handles scheduled checks
   (e.g. scan for upcoming vet visits and enqueue notification tasks). Runs as a separate
   `celery_beat` Docker service with Redis 7 as the broker.

2. **Django Background Tasks API** (`ImmediateBackend`) — used for lightweight in-process tasks
   that do not need a separate worker. Configured in `settings.py`.

Notification channel: **Discord** via `discord.py`. Additional channels (e-mail, SMS) are deferred.

### Consequences
- The `homepage.CronJob` model is an **orphan** — it was populated by django-crontab and nothing
  currently writes to it. Follow-up required: migrate it or drop the table (tracked in CLAUDE.md
  under Known Refactoring Targets).
- Celery Beat requires two running processes: the Celery worker (`queue` service) and the Beat
  scheduler (`celery_beat` service). Both are defined in `docker/docker-compose.yml`.
- Task visibility is available via **Celery Flower** (port 5555).
- Adding a new notification type means: (a) write a task function in `celery_notifications/cron.py`,
  (b) register it in the Celery Beat schedule in `celery_notifications/config.py`.

### Keywords
- Celery, Celery Beat, notifications, Discord, cron, queue, broker, background tasks

### Links
*[2026-05-31]*\
https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html

*[2023-12-19]*\
https://docs.djangoproject.com/en/stable/topics/db/multi-db/ (database routing reference)
