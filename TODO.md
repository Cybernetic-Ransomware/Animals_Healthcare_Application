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

## 6. Dependency migrations ✅

### 6a. Remove `httplib2` ✅

Removed via `uv remove httplib2`. Pulled `pyparsing` with it (sole dependent).

### 6b. Move `icecream` to dev dependencies ✅

Moved to `[dependency-groups].dev`. Only consumer (`send_email_example` in
`celery_notifications/cron.py`) is dead code — never called. Production images
built with `uv sync --no-group dev` no longer install it.

### 6c. Replace `pycouchdb` with `requests` ✅

- `src/ahc/settings.py` — replaced `pycouchdb.Server(...)` with plain config
  vars (`COUCHDB_BASE_URL`, `COUCHDB_DB_NAME`, `COUCHDB_HOST`; host defaults to
  `appendixes-db` for docker/k8s compatibility).
- `src/ahc/apps/medical_notes/services/couch.py` — adapter rewritten on
  `requests.Session` + `_rev` handling; public method signatures unchanged.
- `uv remove pycouchdb` also dropped `chardet`.

### 6d. Remove `django-libsass` + `libsass` ✅

- `static/css/custom_pico.css` compiled once via `npx sass` and committed.
- `base.html` — `{% compress css %}` block replaced with a plain `<link>`.
- `settings.py` — removed `COMPRESS_*`, `LIBSASS_*`, `compressor` from
  `INSTALLED_APPS` and `STATICFILES_FINDERS`.
- `uv remove django-compressor django-libsass libsass django-appconf` also
  dropped `rcssmin`, `rjsmin`.
- `cffi` kept — still required by `cryptography`.

**Follow-up:** upgrade PicoCSS and bring it in as a git submodule (the 6d SCSS
deprecation warnings originate in pico 1.5.9 internals).

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
