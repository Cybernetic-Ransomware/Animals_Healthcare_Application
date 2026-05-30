# Remaining work — next sessions

## 1. Dead signals (HIGH — silent production bug)

All `apps.py` have `ready(): pass` — signal handlers are never registered with
Django's dispatch system. As a result, the following logic **does not run in
production**:

| Handler | File | Effect when dead |
|---------|------|-----------------|
| `remove_old_pictures_after_change` | `animals/signals.py` | Orphaned animal images accumulate |
| `remove_old_pictures_after_animal_delete` | `animals/signals.py` | Profile image not removed on delete |
| `remove_old_pictures_after_user_delete` | `animals/signals.py` | Same, on user delete |
| `update_allowed_users` | `animals/signals.py` | Owner can remain in allowed_users |
| `validate_one_to_one_fields` | `medical_notes/signals/` | Invalid BiometricRecords can be saved |
| `clean_orphaned_metric_records` | `medical_notes/signals/` | Orphaned BiometricRecord rows accumulate |
| `clean_orphaned_diet_records` | `medical_notes/signals/` | Orphaned FeedingNote rows accumulate |
| `create_profile` / `save_profile` | `users/signals.py` | Profile not created on User.create |
| `create_basic_privilege` / `create_background` | `users/signals.py` | Privilege/Background not set on Profile.save |

**Decision required:** register each handler in `ready()` OR consciously delete it.
**Warning:** do NOT move signal logic into services "in passing" without a deliberate
decision — it would change current production behaviour (currently: nothing runs).

## 2. FeedingNote missing `author` field (BUG)

`medical_notes/signals/type_feeding_notes.py` references `instance.related_note.author`
but `FeedingNote` has no `author` field — it only has `related_note` (FK to `MedicalRecord`),
and `MedicalRecord` has `author`. The signal traversal chain is:

```
FeedingNote → related_note (MedicalRecord) → author (Profile)
```

Check whether this traversal is actually correct or whether it is a latent
`AttributeError` waiting to surface when the signal is finally connected.

## 3. Form validation with DB queries in `utils_owner/forms.py`

`ChangeOwnerForm.clean_new_owner()` and `ManageKeepersForm.clean_input_user()`
issue `Profile.objects.filter(...)` / `Profile.objects.get(...)` queries inside
`clean_*` methods. This is acceptable for now but can be extracted to selectors
(query layer) in a later refactor. **Do not move in the same PR as signal work** —
risk of changing form validation error messages.

## 4. Test coverage gaps

- Views (`animals/views.py`, `medical_notes/views/`) have zero test coverage.
- `users/signals.py` handlers untested (currently dead anyway, see §1).
- Fat views refactor (in progress) is the natural trigger for adding view tests.

## 5. Fat views — in progress

`animals/views.py` and `medical_notes/views/` contain business logic.
Extraction to a service layer is already started. Keep signal decisions (§1)
in sync with this work to avoid duplicating logic.

## 6. Dependency migrations

### 6a. Remove `httplib2` (no-risk, easy)

`httplib2` is declared as a direct dependency but is **never imported** anywhere in `src/`.
It is a legacy Python 2-era HTTP library superseded by `requests` (already in use).

Action: remove from `pyproject.toml`, run `uv lock`.

### 6b. Move `icecream` to dev dependencies

`icecream` is in the main (production) dependency group but the only usage is a
**lazy import inside a debug branch** in `src/celery_notifications/cron.py:121`.

Action: move to `[dependency-groups] dev` in `pyproject.toml`.

### 6c. Replace `pycouchdb` with maintained HTTP client

`pycouchdb v1.16.0` has not been maintained since ~2019 and has no Python 3.13+
test coverage. The entire interaction is already isolated in one adapter:

- `src/ahc/settings.py` — `pycouchdb.Server(...)` connection init
- `src/ahc/apps/medical_notes/services/couch.py` — single thin adapter class

Migration options (pick one):
- **Raw `requests`** — CouchDB exposes a plain HTTP/JSON API; no client lib needed.
  Simplest: replaces `pycouchdb.Server` + `db[key]` with `requests.get/put` calls.
- **`httpx`** — async-capable drop-in; useful if the app ever adopts ASGI fully.

Risk is low because ADR-08 scopes CouchDB to file/attachment storage only (no
complex queries). The adapter in `couch.py` is the single change surface.

### 6d. Remove `django-libsass` + `libsass` by precompiling SCSS

`django-libsass v0.9` (2021) drives `COMPRESS_PRECOMPILERS` to compile
`static/custom_pico.scss` at request time via `SassCompiler`.

The SCSS file is small (17 lines — PicoCSS variable overrides + one `@import`).
Precompiling it once at build/deploy time removes two C-extension deps (`libsass`,
`cffi`) from the runtime and the runtime compilation overhead.

Action:
1. Run `sass static/custom_pico.scss static/css/custom_pico.css` once (dart-sass
   or node-sass; **not** a Python dep — run as a build step or commit the output).
2. Replace the `<link>` in `base.html` from the compressor tag to a plain CSS link.
3. Remove `django-libsass`, `libsass`, `django-compressor`, `django-appconf` from
   `pyproject.toml` (if compressor is not used for anything else).
4. Remove `COMPRESS_PRECOMPILERS` block from `settings.py`.

Check `settings.py` for other `COMPRESS_*` entries before removing `django-compressor`.

### 6e. Monitor: transitive Python-2-era deps

These cannot be removed directly — they are pulled in by maintained packages:

| Package | Via | Concern |
|---------|-----|---------|
| `six v1.17.0` | `python-dateutil` → `celery` | Python 2 compat; harmless but signals old dep chain |
| `audioop-lts v0.2.2` | `discord.py` | Shim for `audioop` removed in Python 3.13; watch discord.py changelog |
| `pytz v2026.2` | `flower` | Django 4.0+ prefers `zoneinfo`; not actionable until Flower drops pytz |

No action needed now; re-check when upgrading Celery or discord.py.

---

## Already fixed in `refactor/django-5x-prep`

- `STATIC_ROOT` → `BASE_DIR / "static_collected"` ✅
- `SECRET_KEY` / `DEBUG` from env via python-decouple ✅
- `homepage.CronJob` orphaned model dropped ✅
- `validate_one_to_one_fields` set-comprehension bug fixed ✅
- `animals/signals.py` hardcoded paths → `settings.MEDIA_ROOT` ✅
- Migration 0009 naive datetime default → UTC-aware ✅
