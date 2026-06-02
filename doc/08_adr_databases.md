## Database stack — PostgreSQL + CouchDB + Redis

### Date
`2023-06-05`

### Status
In-building

### Context
Three distinct data storage needs were identified:
1. Relational data (users, animals, medical notes) — needs transactions and Django ORM support.
2. File/attachment storage (medical PDFs) — binary blobs do not belong in a relational DB.
3. Async task brokering (Celery) — needs a fast in-memory queue.

Candidates evaluated per role:
- Relational: PostgreSQL, MS SQL, MySQL, SQLite.
- Document/file: CouchDB, MongoDB.
- Broker: Redis.

### Decision
Three databases were selected, each with a dedicated role:

| Database          | Version     | Port  | Role                                                  |
|-------------------|-------------|-------|-------------------------------------------------------|
| **PostgreSQL**    | 18          | 5433  | Primary relational store — all Django models          |
| **CouchDB**       | 3.3.3       | 5982  | Attachment/file storage only (medical PDFs, images)   |
| **Redis**         | 7           | 6379  | Celery broker + task result backend                   |

SQLite is used **only** for the test database (activated in `settings.py` when `"test"` in `sys.argv`).

Django database routing is required: the default router sends all ORM queries to PostgreSQL;
CouchDB is accessed directly via its HTTP API (not through Django's ORM).

### Consequences
- CouchDB is intentionally narrow in scope — file storage only. No relational queries, no Django models.
  Any new file storage feature must use the CouchDB HTTP client, not the Django ORM.
- Redis must be running for Celery workers to start; the application is degraded (no async tasks,
  no notifications) if Redis is unavailable.
- Test runs use SQLite (no Docker required); integration tests that need PostgreSQL-specific behaviour
  must be marked `@pytest.mark.integration` and run against the real stack.

### Keywords
- DBMS, database, PostgreSQL, CouchDB, Redis, Celery, routing

### Links
*[2023-06-14]*\
https://www.postgresql.org/\
https://redis.io/\
https://couchdb.apache.org/

*[2023-01-24]*\
[How to use PostgreSQL with Django](https://www.enterprisedb.com/postgres-tutorials/how-use-postgresql-django)

*[2008-08-18]*\
[An Introduction to Using CouchDB with Django](https://lethain.com/an-introduction-to-using-couchdb-with-django/)
