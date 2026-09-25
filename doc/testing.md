# Test suite conventions

This document describes how tests are organised in AHC. It is the reference for adding, moving
or reviewing tests.

## Layout

Tests live in a `tests/` package inside the package they test. The layout of `tests/` mirrors
the production code, so finding the tests for a module is a path lookup rather than a search.

| Production code                | Tests                                       |
|--------------------------------|---------------------------------------------|
| `{app}/models.py`              | `{app}/tests/test_models.py`                |
| `{app}/services.py`            | `{app}/tests/test_services.py`              |
| `{app}/services/exporter.py`   | `{app}/tests/services/test_exporter.py`     |
| `{app}/utils_owner/views.py`   | `{app}/tests/utils_owner/test_views.py`     |
| `ahc/views.py`, `ahc/settings.py` | `src/ahc/tests/test_views.py`, `test_csp.py` |

Rules:

- A module `x.py` maps to `test_x.py`; a package `x/` maps to a directory `tests/x/`.
- A large module may map to a `tests/<module>/` directory split by area
  (for example `animals/tests/views/test_profile.py`, `views/test_stable.py`).
- A test of a business invariant that crosses several layers stays together in
  `tests/test_<feature>.py` (for example `medical_notes/tests/test_deceased_write_blocking.py`).
  Reading the whole scenario in one place matters more than splitting it per layer.
- Do not create empty placeholder test files for untested modules.
- Every test directory contains an `__init__.py`. Basenames such as `test_views.py` repeat across
  apps, and without packages pytest fails with "import file mismatch".
- Never keep a `tests.py` module next to a `tests/` package: the package shadows the module.
- Test files are named `test_*.py`. Test classes are named `Test*` and do not subclass
  `django.test.TestCase`; write plain pytest classes and functions.

## Markers

Every test carries exactly one kind marker: `unit` or `integration`. A collection hook in the
root `conftest.py` rejects tests with neither, with both, or with `unit` combined with database
or Django client access.

| Marker        | Meaning |
|---------------|---------|
| `unit`        | An isolated component. No database, no Django request/client, no external services. It may use hermetic local resources such as `tmp_path` when they are part of the component's direct contract (for example a file sweeper tested on a temporary directory). |
| `integration` | Several layers or adapters working together, or real infrastructure: ORM/database, Django client/URLconf/middleware, signals with the ORM, management commands, Celery/Redis/CouchDB. |
| `regression`  | Orthogonal, added on top of `unit` or `integration`. Guards a specific fixed bug; the test docstring names the PR or issue. |
| `slow`        | Excluded from CI runs. |
| `django_db`   | Technical pytest-django marker granting database access. It is not a test category. |

`regression` rules:

- Put it on the test method that guards the fixed bug. Put it on a class only when every test
  in the class guards the same bug.
- A test merely added in a `fix(...)` commit is not a regression test by that fact alone; it has
  to protect against the bug that commit fixed.

## Fixtures

Fixtures live at the lowest level that serves every user.

| Level                          | What belongs there |
|--------------------------------|--------------------|
| Root `conftest.py`             | Fixtures used by several apps: `user_profile`, `second_user_profile`, `logged_in_client`, `png_upload`, and the marker guard. |
| `{app}/tests/conftest.py`      | Domain fixtures used by several files of one app (for example `animal`, `snapshot_dir`). |
| A subdirectory `conftest.py`   | Fixtures used only by one area of an app. |
| The test module or class       | Fixtures used by a single file or class. |

- There is no central `fixtures.py`.
- Plain helper functions shared by several files of one app go to `{app}/tests/helpers.py` and
  are imported relatively (`from ..helpers import _query`). Do not import test code through an
  absolute `ahc.apps...tests` path: `src/__init__.py` makes pytest import test modules as
  `src.ahc.apps...`, and an absolute import would load a second copy of the module.
- A class-level fixture with the same name as a conftest fixture overrides it for that class.
  Keep the override when the test asserts on the overridden data.

## Parametrization

Parametrize only when the behaviour under test is genuinely the same and only the input differs.
Separate behaviours get separate tests, even when their bodies look similar.

## Running tests

```bash
uv run pytest                          # whole suite
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m regression

just test
just test-unit
just test-integration
just test-regression
```

CI runs `unit` and `integration` in separate parallel jobs. Because every test is exactly one of
the two, together they cover the whole suite once. The test database is SQLite
(set in `settings.py` when pytest is invoked).
