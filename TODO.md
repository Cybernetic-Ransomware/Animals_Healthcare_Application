# Remaining work — next sessions

## 1. Dead signals — DONE

All handlers registered in `ready()`. Status per handler:

| Handler                              | File                         | Outcome                                      |
|--------------------------------------|------------------------------|----------------------------------------------|
| `remove_old_pictures_after_animal_delete` | `animals/signals.py`    | Targeted O(1), after-commit cleanup          |
| `remove_old_pictures_after_profile_delete` | `users/signals.py`     | Targeted O(1), after-commit cleanup          |
| `update_allowed_users`               | `animals/signals.py`         | Connected as-is                              |
| `validate_one_to_one_fields`         | `medical_notes/signals/`     | Connected as-is                              |
| `clean_orphaned_metric_records`      | `medical_notes/signals/`     | Fixed (None guard on `related_note`), connected |
| `clean_orphaned_diet_records`        | `medical_notes/signals/`     | Fixed (rewrote logic, see §2), connected     |
| `create_profile` / `save_profile`    | `users/signals.py`           | Connected (`save_profile` guarded with `hasattr`) |
| `create_basic_privilege` / `create_background` | `users/signals.py` | Restored, connected — see note below       |

`create_basic_privilege` / `create_background` were deleted at one point because
`Privilege`/`ProfileBackground` used to raise `NotImplementedError` in `__init__`.
`homepage/models.py` no longer does that — both are plain, ORM-instantiable models —
so the two handlers were restored and are unit-tested in `users/tests.py`.

Current profile-image cleanup lifecycle:
- **Animal delete** and **Profile delete** (direct, or cascaded via `User.delete()`):
  targeted O(1) `pre_delete` signals (`remove_old_pictures_after_animal_delete`,
  `remove_old_pictures_after_profile_delete`) schedule the file removal via
  `transaction.on_commit`, so a rolled-back delete leaves the file in place. Both
  signals explicitly skip the field's default image.
- **Image replacement** (custom → custom, custom → default): deliberately deferred,
  no signal — the old file becomes an unreferenced orphan, picked up by the daily
  sweep below.
- **Orphan sweep**: `clean_orphaned_profile_images` (Celery Beat, daily 03:00) now
  covers both `profile_pics/animals/` (Animal) and `profile_pics/users/` (Profile).

## 2. FeedingNote missing `author` field — DONE

Fixed in the same PR as §1. `clean_orphaned_diet_records` now mirrors the
`clean_orphaned_metric_records` pattern: finds orphaned `diet_note` shells
(MedicalRecord with no attached FeedingNote) and deletes them.

## 3. Form validation with DB queries in `utils_owner/forms.py` — DONE

Extracted to `profile_by_username(username: str)` selector in `animals/selectors.py`.
Both `clean_new_owner` and `clean_input_user` now use it. Changed `cleaned_data.get()`
to `cleaned_data[field]` (correct pattern for `clean_<field>` methods — key is
guaranteed present when Django calls them).

## 4. Test coverage gaps — DONE

- `medical_notes/views/` feeding views covered (§5).
- `users/signals.py` `create_profile`/`save_profile` connected (§1); `create_basic_privilege`/
  `create_background` restored (§1); unit tests for all four in `users/tests.py`.
- `animals/views.py`: `CreateAnimalView`, `AnimalProfileDetailView`, `StableView`,
  `ToPinAnimalsView` — integration tests added (`animals/tests.py`).
- `animals/utils_owner/views.py`: `AnimalDeleteView`, `ChangeBirthdayView`,
  `ChangeFirstContactView`, `ChangeNextVisitView`, `ChangeDietaryRestrictionsView`,
  `ChangeAnimalDetailsView`, `ManageKeepersView`, `ChangeOwnerView`, `EditShareView` —
  integration tests added (`animals/tests.py`).
- `users/views.py`: `UserRegisterView`, `UserProfileView`, `ShareDefaultsView` —
  integration tests added (`users/tests.py`).

## 5. Fat views — DONE

Remaining business logic extracted to services/selectors. All `medical_notes/views/`
are now thin.

Changes:
- `services/feeding.py` — new: `create_feeding_note`
- `selectors.py` — new: `is_author_of_any_note`
- `utils.py` — new: `build_timeline_base_query` (presentation helper, DB-free)
- `views/type_feeding_notes.py` — `DietRecordCreateView.form_valid` delegates to service;
  `EditDietRecordView` broken `form_valid` removed, correct `get_success_url` added
  (fixes latent 404 bug — pk was misused as EmailNotification id)
- `views/type_basic_note.py` — `EditRelatedAnimalsView` uses `is_author_of_any_note`;
  `FullTimelineOfNotes` uses `build_timeline_base_query`
- `src/ahc/types.py` — new: `AuthenticatedRequest` (under `TYPE_CHECKING` to avoid
  Django model metaclass registration)
- `request: AuthenticatedRequest` added to all touched view classes (partial §6)

Regression tests added for all modified view flows (see §4 — coverage now exists
for `DietRecordCreateView`, `EditDietRecordView`, `FeedingNoteListView`).

## 6. Replace `[[tool.ty.overrides]]` with a typed request

`pyproject.toml` suppresses `unresolved-attribute` across all view/mixin/signal/form
modules to silence Django ORM false positives (mainly `request.user.profile`).
The custom request type already exists at `src/ahc/types.py`. Both classes live
under `TYPE_CHECKING` to prevent Django's model metaclass from registering
`_AHCUser` as a real model at import time (runtime `RuntimeError` otherwise):

```python
# src/ahc/types.py  — CORRECT pattern
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest
    from ahc.apps.users.models import Profile

    class _AHCUser(User):
        profile: Profile

    class AuthenticatedRequest(HttpRequest):
        user: _AHCUser
```

To use in a view, two things are required:
1. `from __future__ import annotations` at the top of the view file (makes all
   class-body annotations lazy — Python never evaluates them at import time).
2. Import under `TYPE_CHECKING`:
   ```python
   if TYPE_CHECKING:
       from ahc.types import AuthenticatedRequest
   ```
3. Annotate the view class: `request: AuthenticatedRequest`

**Current state:** all view classes with `LoginRequiredMixin` carry `request: AuthenticatedRequest`.
The `[[tool.ty.overrides]]` block has been removed entirely (`refactor/backend-typing-cleanup`):

- `homepage/views.py` — narrowed locally: `cast("AuthenticatedRequest", self.request)` only
  inside the `is_authenticated` branch, since `HomepageView` also serves anonymous users.
- `mixins/**` (`self.kwargs` on `UserPassesTestMixin`-based permission mixins, which don't
  inherit from `View`) — fixed with one shared typing-only base, `ahc.types.AuthenticatedCBVMixin`,
  mixed in ahead of `UserPassesTestMixin` instead of repeating `request`/`kwargs` per class.
- `forms/**` — fixed with `cast()` to the concrete field type (`ModelChoiceField` /
  `ModelMultipleChoiceField` / `Field`) where django-stubs only exposes the generic base, and
  `super().clean() or {}` where the stub return type is `dict[str, Any] | None`.
- `signals/**` — fixed with `TYPE_CHECKING`-only reverse-manager annotations
  (`feedingnote_set` / `biometricrecord_set`) on `MedicalRecord`, since neither FK sets
  `related_name` and `ty` has no equivalent to django-stubs' mypy plugin for inferring them.

No local ignores were left — every case had a correct static-typing fix.
