## Data model — stored fields per entity

### Date
`2023-07-09` (updated `2026-09-27`)

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
| `first_contact_vet`         | FK → `veterinary.Vet` | no (null) | `SET_NULL`; `related_name="first_contact_for"`; nullable, owner-scoped record |
| `first_contact_medical_place`| FK → `veterinary.MedicalPlace` | no (null) | `SET_NULL`; `related_name="first_contact_for"`; nullable, owner-scoped record |
| `legacy_first_contact_vet`  | CharField(250)   | no       | Compatibility-window only — see note below       |
| `legacy_first_contact_medical_place` | CharField(250) | no | Compatibility-window only — see note below       |
| `last_control_visit`        | DateTimeField    | no       |                                                  |
| `next_visit_date`           | DateField        | no       |                                                  |
| `dietary_restrictions`      | CharField(2500)  | no       |                                                  |
| `species`                   | CharField(100)   | no       | Displayed alongside `breed` as "species / breed" |
| `breed`                     | CharField(100)   | no       |                                                  |
| `sex`                       | CharField(1)     | no       | Choices: `m`/`f` via `Sex(TextChoices)`; `get_sex_display()` → Male/Female |
| `sterilization`             | BooleanField     | default  | `default=False`; shown as disabled checkbox in UI|

**`legacy_first_contact_vet` / `legacy_first_contact_medical_place`** (ADR-15, expand/contract
migration) — these keep the original `first_contact_vet` / `first_contact_medical_place` text
columns physically alive via `db_column`, so the pre-migration data is not lost. They are a
**compatibility window only**, not the current data model:

- Runtime UI does not read them.
- The offline snapshot exporter does not read them.
- `animals.services` does not write them — there is no dual-write with the new foreign keys.
- They will be removed by a separate later "contract" migration (ADR-15, stage C12) once the
  expand PR has run in production for an observation period without a rollback.

**Optional field idiom** — existing optional `CharField` / `DateField` fields on `Animal` use
`None` / `null=True`, following the model's historical style; not every nullable field on
`Animal` carries an identical argument set, so this is a style note, not a literal claim that
every optional field is defined with `default=None, blank=True, null=True`. The new
`veterinary.ContactRecord` fields deliberately use a different, stricter idiom — see below.

**Boolean field idiom** — binary booleans (no "unknown" state) use:
`BooleanField(default=False)` without `null=True`.

**`TextChoices` placement** — defined at module level, above the model class that uses them.

#### `Vet` / `MedicalPlace` models (`veterinary/models.py`)

Owner-scoped contact book records, introduced by ADR-15. `ContactRecord` is an **abstract** base
shared by both:

| Field     | Type                | Notes                                                        |
|-----------|---------------------|---------------------------------------------------------------|
| `id`      | UUIDField (PK)      | `uuid4`, non-editable — record identity is the UUID, not `name` |
| `name`    | CharField(250)      | Same length as the legacy `first_contact_*` column            |
| `phone`   | CharField(32)       | Optional                                                       |
| `email`   | EmailField          | Optional                                                       |
| `details` | CharField(2500)     | Optional free text, visible to keepers with `vet_contact`      |

`Vet` adds `owner = FK → Profile` (`CASCADE`, `related_name="vets"`). `MedicalPlace` adds the same
`owner` FK (`related_name="medical_places"`) plus `address` (CharField(250)) and `website`
(URLField).

- Both models are **owner-scoped**: every record belongs to exactly one `Profile`, and `owner`
  uses `CASCADE` — deleting a `Profile` deletes its contact book.
- **No uniqueness constraint on `name`.** Two records — even for the same owner — may share a
  display name; identity is the UUID, and the contact-picker UI disambiguates by phone or
  address.

**Optional string idiom for `veterinary`** — unlike `Animal`'s `null=True` idiom above, new
optional string fields in `veterinary` (`phone`, `email`, `details`, `address`, `website`) use a
single representation of "no value": an empty string.

```python
phone = models.CharField(max_length=32, blank=True, default="")
```

`null=True` is not used for these fields. This does not retroactively change any `Animal` field.

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
| `allow_vet_contact` | BooleanField  | Structured `Vet`/`MedicalPlace` first-contact cards + `next_visit_date` |
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

**`vet_contact` and the contact book**: any logged-in user can open `/veterinary/contacts/`, but
the page shows only **that user's own** owner-scoped contact book — a carer sees their own book
there, never the owner's. A carer holding `vet_contact` on a shared animal sees the first-contact
`Vet`/`MedicalPlace` card only *through the animal* (read-only), with no path from that page into
the owner's book. A direct UUID request into another owner's record (`vet_edit`, `vet_delete`,
`medical_place_edit`, `medical_place_delete`) 404s via `OwnedContactMixin`.

#### `ShareCategory(TextChoices)` (`animals/models.py`)

| Value         | Label             | Scope                                                  |
|---------------|-------------------|--------------------------------------------------------|
| `basic`       | Basic info        | Hero + Overview tab (name, species, breed, sex, age…)  |
| `vet_contact` | Vet contact       | Structured first-contact `Vet` and `MedicalPlace` cards (name, phone, email, address, website, `details`) reached through `Animal.first_contact_*`, plus `next_visit_date` |
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
- data, database, models, Animal, AnimalShare, ShareDefaults, ShareCategory, UserProfile, MedicalNote, sharing, privacy, Vet, MedicalPlace, ContactRecord, contact book

### Links
- `CLAUDE.md` — Animals App Conventions (field editing pipeline, model idioms)
- ADR-08 — database technology choices (PostgreSQL / CouchDB / Redis)
- ADR-15 — vet and medical place contact profiles (`Vet`, `MedicalPlace`, expand/contract migration of `first_contact_*`)
