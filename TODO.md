# Remaining work — next sessions

## 1. Dead signals — DONE

All handlers registered in `ready()`. Status per handler:

| Handler                              | File                         | Outcome                                      |
|--------------------------------------|------------------------------|----------------------------------------------|
| `remove_old_pictures_after_change`   | `animals/signals.py`         | Connected as-is                              |
| `remove_old_pictures_after_animal_delete` | `animals/signals.py`    | Connected as-is                              |
| `remove_old_pictures_after_user_delete` | `animals/signals.py`      | Connected as-is                              |
| `update_allowed_users`               | `animals/signals.py`         | Connected as-is                              |
| `validate_one_to_one_fields`         | `medical_notes/signals/`     | Connected as-is                              |
| `clean_orphaned_metric_records`      | `medical_notes/signals/`     | Fixed (None guard on `related_note`), connected |
| `clean_orphaned_diet_records`        | `medical_notes/signals/`     | Fixed (rewrote logic, see §2), connected     |
| `create_profile` / `save_profile`    | `users/signals.py`           | Connected (`save_profile` guarded with `hasattr`) |
| `create_basic_privilege` / `create_background` | `users/signals.py` | **Deleted** — see note below               |

`create_basic_privilege` / `create_background`: `Privilege` and `ProfileBackground`
raise `NotImplementedError` in `__init__`, making them permanently uninstantiable via
the ORM (any queryset that returns a row crashes). `Profile.privilege_tier` and
`profile_background` are nullable (`default=None`), so a Profile without them is valid.
Reconnect only after `homepage/models.py` is redesigned (see the `TODO` comments there).

Note: `remove_old_pictures_after_change` and `remove_old_pictures_after_user_delete`
perform a full media-dir scan on every `Animal`/`Profile` save — O(table). Candidate
for a management command in a later PR.

## 2. FeedingNote missing `author` field — DONE

Fixed in the same PR as §1. `clean_orphaned_diet_records` now mirrors the
`clean_orphaned_metric_records` pattern: finds orphaned `diet_note` shells
(MedicalRecord with no attached FeedingNote) and deletes them.

## 3. Form validation with DB queries in `utils_owner/forms.py` — DONE

Extracted to `profile_by_username(username: str)` selector in `animals/selectors.py`.
Both `clean_new_owner` and `clean_input_user` now use it. Changed `cleaned_data.get()`
to `cleaned_data[field]` (correct pattern for `clean_<field>` methods — key is
guaranteed present when Django calls them).

## 4. Test coverage gaps

- Views (`animals/views.py`, `medical_notes/views/`) have zero test coverage.
- `users/signals.py` handlers untested (currently dead anyway, see §1).
- Fat views refactor (in progress) is the natural trigger for adding view tests.

## 5. Fat views — in progress

`animals/views.py` and `medical_notes/views/` contain business logic.
Extraction to a service layer is already started. Keep signal decisions (§1)
in sync with this work to avoid duplicating logic.

## 6. Replace `[[tool.ty.overrides]]` with a typed request

`pyproject.toml` suppresses `unresolved-attribute` across all view/mixin/signal/form
modules to silence Django ORM false positives (mainly `request.user.profile`).
The proper fix is a custom request type in `src/ahc/types.py`:

```python
# src/ahc/types.py
from typing import TYPE_CHECKING
from django.contrib.auth.models import User
from django.http import HttpRequest

if TYPE_CHECKING:
    from ahc.apps.users.models import Profile

class _AHCUser(User):
    profile: "Profile"

class AuthenticatedRequest(HttpRequest):
    user: _AHCUser  # type: ignore[assignment]
```

Then annotate each view class: `request: AuthenticatedRequest`.
Once all views are covered, remove the `[[tool.ty.overrides]]` block from
`pyproject.toml`. **Do this as part of the fat-views refactor (§5)** — each
view touched during extraction gets the annotation added.
