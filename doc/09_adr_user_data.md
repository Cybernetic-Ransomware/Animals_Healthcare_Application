## Data model — stored fields per entity

### Date
`2023-07-09` (updated `2026-05-31`)

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
| `allowed_users`             | M2M → UserProfile| —        | Keepers; `related_name="keepers"`                |
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

### Keywords
- data, database, models, Animal, UserProfile, MedicalNote

### Links
- `CLAUDE.md` — Animals App Conventions (field editing pipeline, model idioms)
- ADR-08 — database technology choices (PostgreSQL / CouchDB / Redis)
