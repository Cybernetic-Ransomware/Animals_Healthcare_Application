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
