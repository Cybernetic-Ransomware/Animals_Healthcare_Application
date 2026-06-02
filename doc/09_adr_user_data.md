## Data model — stored fields per entity

### Date
`2023-07-09` (updated `2026-06-01`)

### Status
In-building

### Context
Defines what data is stored per entity in PostgreSQL (primary DB, ADR-08), which fields are
optional vs required, and how the models evolve over time.
This ADR is a living document — update it when new fields are added.

### Decision

#### `Animal` model (`animals/models.py`)

| Field                       | Type             | Required | Notes                                            |
|-----------------------------|------------------|----------|--------------------------------------------------|
| `id`                        | UUIDField (PK)   | auto     | `uuid4`, non-editable                            |
| `full_name`                 | CharField(50)    | yes      | Unique per owner's animals (validated in form)   |
| `short_description`         | CharField(250)   | no       | Optional freetext                                |
| `long_description`          | CharField(2500)  | no       | Optional freetext                                |
| `birthdate`                 | DateField        | no       |                                                  |
| `profile_image`             | ImageField       | default  | Defaults to `profile_pics/pet-care.png`          |
| `creation_date`             | DateTimeField    | auto     | `auto_now_add`, non-editable                     |
| `owner`                     | FK → UserProfile | no (null)| `SET_NULL` on delete; `related_name="owner"`     |
| `allowed_users`             | M2M → UserProfile| —        | Keepers; `through="AnimalShare"`; `related_name="keepers"` |
| `first_contact_vet`         | CharField(250)   | no       |                                                  |
| `first_contact_medical_place`| CharField(250)  | no       |                                                  |
| `last_control_visit`        | DateTimeField    | no       |                                                  |
| `next_visit_date`           | DateField        | no       |                                                  |
| `dietary_restrictions`      | CharField(2500)  | no       |                                                  |
| `species`                   | CharField(100)   | no       | Displayed alongside `breed` as "species / breed" |
| `breed`                     | CharField(100)   | no       |                                                  |
| `sex`                       | CharField(1)     | no       | Choices: `m`/`f` via `Sex(TextChoices)`; `get_sex_display()` → Male/Female |
| `sterilization`             | BooleanField     | default  | `default=False`; shown as disabled checkbox in UI|

**Optional field idiom** — all optional `CharField` / `DateField` use:
`default=None, blank=True, null=True`.

**Boolean field idiom** — binary booleans (no "unknown" state) use:
`BooleanField(default=False)` without `null=True`.

**`TextChoices` placement** — defined at module level, above the model class that uses them.

#### `AnimalShare` model (`animals/models.py`) — through model for `Animal.allowed_users`

Stores per-share metadata for the keeper relationship.  Created explicitly via the
`create_share(animal, carer_id, scope, valid_until)` service; never via `.add()` in application code.

| Field            | Type             | Notes                                                      |
|------------------|------------------|------------------------------------------------------------|
| `id`             | AutoField (PK)   |                                                            |
| `animal`         | FK → Animal      | `CASCADE`, `related_name="shares"`                         |
| `carer`          | FK → UserProfile | `CASCADE`, `related_name="received_shares"`                |
| `created`        | DateTimeField    | `auto_now_add`, records when share was granted             |
| `valid_until`    | DateField        | `null=True` = indefinite; expiry enforced by selectors     |
| `allow_basic`    | BooleanField     | Basic info (name, species, breed, sex, age, descriptions)  |
| `allow_vet_contact` | BooleanField  | Vet contact fields + `next_visit_date`                     |
| `allow_diet`     | BooleanField     | `dietary_restrictions` + diet-note timeline                |
| `allow_medications` | BooleanField  | Medication-note timeline                                   |
| `allow_history`  | BooleanField     | Medical-visit timeline + general notes                     |
| `allow_biometrics` | BooleanField   | Biometric records                                          |

**Unique constraint**: `(animal, carer)` — one share row per keeper per animal.

**Helper methods**:
- `allowed_categories() -> set[str]` — maps boolean flags to `ShareCategory` values.
- `is_active(today) -> bool` — returns `True` when `valid_until is None or valid_until >= today`.

**Access enforcement — two layers**:
1. `animals/selectors.py`: `user_can_access_animal` checks expiry; `allowed_categories_for` returns the granted set.
2. Tab views / templates: `_build_*` functions skip building data for absent categories; templates gate sections with `{% if "<cat>" in allowed_categories %}`.

#### `ShareCategory(TextChoices)` (`animals/models.py`)

| Value         | Label             | Scope                                                  |
|---------------|-------------------|--------------------------------------------------------|
| `basic`       | Basic info        | Hero + Overview tab (name, species, breed, sex, age…)  |
| `vet_contact` | Vet contact       | `first_contact_*`, `next_visit_date` (Vet tab fields)  |
| `diet`        | Diet              | `dietary_restrictions` + diet-note timeline            |
| `medications` | Medications       | medicament-note timeline                               |
| `history`     | History & notes   | medical-visit timeline + fast/other notes              |
| `biometrics`  | Biometrics        | biometric-record notes                                 |

#### `ShareDefaults` model (`animals/models.py`)

Per-owner template applied automatically when a new share is created without an explicit scope.

| Field             | Type             | Default | Notes                                              |
|-------------------|------------------|---------|----------------------------------------------------|
| `profile`         | OneToOne → UserProfile | — | `CASCADE`, `related_name="share_defaults"`         |
| `allow_basic`     | BooleanField     | `True`  |                                                    |
| `allow_vet_contact` | BooleanField   | `False` |                                                    |
| `allow_diet`      | BooleanField     | `False` |                                                    |
| `allow_medications` | BooleanField   | `False` |                                                    |
| `allow_history`   | BooleanField     | `False` |                                                    |
| `allow_biometrics` | BooleanField    | `False` |                                                    |

Created lazily via `get_or_create_share_defaults(profile)`.  Editable at `/users/share-defaults/` (name `share_defaults`).

#### `UserProfile` model (`users/models.py`)
Extends `auth.User` via OneToOne. Stores profile image, pinned animals (`M2M → Animal`).
Full field list: see `users/models.py`.

#### `MedicalNote` models (`medical_notes/models/`)
Split into sub-models by note type. See `medical_notes/models/` for current field lists.
Core fields: `animal` (FK), `title`, `short_description`, `full_description`, `creation_date`,
`modify_date`, `start_event_date`, `end_event_date`, `type_of_event`.
`FeedingNote` additionally carries `purchase_source` (CharField 250, optional) — where to buy the product.

### Consequences
- `Animal` fields are edited through the `Change*` pipeline documented in `CLAUDE.md` (Animals App — Conventions).
- New fields on `Animal` require a migration named `0NNN_add_<field>.py` via `makemigrations animals --name`.
- Optional fields must **not** be displayed in the hero overview when empty — use `{% if animal.field %}` guards.
- New keeper shares must be created via `services.create_share(...)`, never via `animal.allowed_users.add()` in application code (the through model would create rows with all `allow_*=False`).
- Expired shares (`valid_until < today`) are excluded by the selectors; no background cleanup is required for correctness, though a Celery Beat task could prune old rows.

### Keywords
- data, database, models, Animal, AnimalShare, ShareDefaults, ShareCategory, UserProfile, MedicalNote, sharing, privacy

### Links
- `CLAUDE.md` — Animals App Conventions (field editing pipeline, model idioms)
- ADR-08 — database technology choices (PostgreSQL / CouchDB / Redis)
