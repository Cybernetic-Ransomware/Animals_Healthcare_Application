## Vet and medical place profiles as owner-scoped contact records

### Date:
`2026-09-26`

### Status
In-building

### Context
`Animal` currently stores the vet and medical place contact as two free-text fields
(`first_contact_vet`, `first_contact_medical_place`, `CharField(250)`). This causes three problems:

- **Duplication.** The same vet has to be retyped for every animal that shares them; a phone
  number change means editing every animal individually.
- **No structure.** Phone, address, and name are mixed into one text blob, so there is no `tel:` /
  `mailto:` link, no contact book, and no way to later associate a contact with a visit.
- **An unrealized original intent.** ADR-01 already lists "healthcare place and vet profiles
  (address, historical prices, ratings)" in the first-version scope. Git history confirms this
  was meant to be a foreign key from the start: an early commit ("Models fields reviewed",
  2023-08-07) planned `first_contact_vet = models.ForeignKey(Vet_pofile)` and
  `first_contact_medical_place = models.ForeignKey(Place_profile)`; the follow-up commit that
  replaced these with text fields is explicitly titled "First contact as text fields
  implementation" — the text fields were a conscious interim step, not the final design. The
  `Vet_pofile` / `Place_profile` comments and a `# TO change` marker are still in the codebase.

The goal of this feature is to replace the text fields with domain records `Vet` and
`MedicalPlace`, without losing existing data and without breaking the offline snapshot contract
(ADR-12). The decisions below were evaluated against several alternatives (documented in the
feature's implementation plan) and approved before any model, migration, or view work started.

### Decision

**Domain shape**

- Two separate models, `Vet` and `MedicalPlace`, sharing an abstract base (`ContactRecord`) for
  common fields and formatting, rather than one polymorphic `Contact(kind=...)` model. The domain
  genuinely distinguishes them (a place has an address and, later, hours/pricing; a vet is a
  person who may work at several places), and splitting one table into two later would be a
  painful data migration.
- No `Vet` ↔ `MedicalPlace` relationship in the MVP. No current flow reads it, and a plain,
  attribute-less M2M (`Vet.places`) can be added later as a purely additive change. A vet's
  workplace can be recorded in free-text `details` until then.
- `Vet` and `MedicalPlace` live in a new app, `ahc.apps.veterinary`, rather than being folded into
  `animals`. The app name intentionally covers both entities and future extensions (M2M, pricing)
  without needing an app-label change later.

**Ownership and visibility**

- Records live in a **private contact book per `Profile`** (`owner = FK Profile, CASCADE`), not in
  a global, moderated directory. A global catalog would require deduplication, edit rights, and
  moderation of third-party personal data (GDPR-sensitive for vets) and mainly pays off once
  ratings/pricing exist — both are out of scope here. Duplicate contacts across different owners
  are acceptable. A global directory with a "copy to my contacts" action remains a possible later
  addition that would not require changing the MVP model.
- Carers never see the owner's contact book. A carer holding the `vet_contact` share category
  continues to see the first-contact data only *through the animal* (read-only), exactly as today.
  No new `ShareCategory` is introduced — `vet_contact` is extended to cover the structured vet and
  place cards (name, phone, email, address, website, details) instead of the current plain text.
  `ShareDefaults` is unchanged.

**`Animal` first-contact relations**

- `Animal.first_contact_vet` and `Animal.first_contact_medical_place` keep their current attribute
  names (per the original 2023 intent) but become nullable foreign keys to `veterinary.Vet` and
  `veterinary.MedicalPlace`, with `on_delete=models.SET_NULL`. Deleting a contact from the book must
  never block or cascade-delete an animal; `SET_NULL` also means the delete-confirmation page can
  show which animals (including archived ones) would lose that reference.
- On ownership transfer, first-contact records are **copied** into the new owner's contact book and
  the animal's foreign keys are repointed. Without this, the new owner (and their carers) would see
  and be able to edit/delete a record that still belongs to the previous owner.
- Setting first contact for a deceased animal is blocked, closing an existing gap where the
  `ChangeFirstContactView` only checked ownership and not the archive/deceased state — this is a
  deliberate behavior change, consistent with the project's "no writes on a deceased animal" rule.

**Migration strategy (expand / contract)**

- Existing text is preserved through an **expand/contract** migration, not a one-shot destructive
  conversion: the legacy `first_contact_vet` / `first_contact_medical_place` text columns stay
  physically in the database (renamed at the model-state level only) through the whole "expand" PR,
  and are dropped only in a **separate, later "contract" PR** once the expand PR has run on
  production for an observation period (target: **around 7 days**) without a rollback, and a
  verification query confirms no animal has non-empty legacy text with an unset new foreign key.
- **No dual-write.** The application never keeps the legacy text column in sync with the new
  record once both exist. Maintaining dual-write would change the legacy text's semantics (it would
  become just a name instead of the full historical description), add code that is deleted again in
  the contract PR, and would only protect one scenario — an image rollback during the compatibility
  window — whose cost is instead accepted explicitly (see "Rollback" below).
- The one-time text-to-record migration is lossless: the first line of the legacy text becomes
  `name` (it always fits, since `name` is `CharField(250)`, the same length as the legacy column),
  and any remaining lines become `details`. The migration reuses an existing record with identical
  materialized fields instead of always creating a new one, so re-running it after a partial
  rollback does not create duplicate contacts.

**`as_contact_text()`**

- Every `ContactRecord` (`Vet`, `MedicalPlace`) formats itself for display and snapshot export via
  `as_contact_text()`. This method joins the record's non-empty **structured contact fields**
  (name, phone, email, and place-only address/website) as one line each, skipping any field that is
  empty. It then appends `details` **verbatim** — including internal blank lines — because `details`
  is free text the owner wrote intentionally; only the structured fields are individually filtered
  for emptiness. This is also what lets a migrated record's `as_contact_text()` reproduce the
  original legacy text exactly.

**Unaffected areas**

- Visit-time text fields (`MedicalRecord.place`, `MedicalRecord.participants`,
  `VaccinationNote.suggested_clinic`) remain plain text. They are a historical label captured at the
  moment of the visit; renaming or deleting a contact record must not rewrite history. A structured
  FK on visit notes is a possible later step (see Consequences) but is out of scope here.
- Pricing and ratings (mentioned in ADR-01's original scope) remain out of the MVP. They need a
  services/pricing model tied to visits and mainly make sense for a global directory — both are
  separately deferred decisions.
- The offline snapshot contract (ADR-12) stays compatible: `animal_snapshot.first_contact_vet` and
  `first_contact_medical_place` keep their existing columns and meaning (deterministic contact text
  via `as_contact_text()`), gated by the same `vet_contact` category as today. `SCHEMA_VERSION`
  stays at `1` — this is an additive/behavior-preserving change under the ADR-12 contract, not a
  breaking one. Editing a contact record does cause the animals that reference it to report as
  stale ("Ready, but outdated") once, which is expected.

**Field conventions**

- `Vet` and `MedicalPlace` use a UUID primary key, consistent with `Animal` and `MedicalRecord`.
- `name = models.CharField(max_length=250)` — the same length as the legacy text column, so the
  lossless migration described above never has to truncate.
- **No uniqueness constraint on `name`**, in the model or in forms. A record's identity is its UUID;
  two vets or two places may legitimately share a display name. The contact-picker UI disambiguates
  same-name records by phone or address. Deduplication is performed only inside the one-time data
  migration, based on an exact match of the normalized legacy text for the same owner, and reuses
  an existing identical record rather than enforcing a database-level constraint.

**Rollback semantics**

- Rolling back the **application image** (pinning the deploy back to a pre-feature build) while the
  database has already run the expand migration is schema-compatible: the old code reads the
  untouched legacy text columns and simply ignores the new `*_id` columns and `veterinary_*`
  tables.
- This rollback is **not fully write-compatible**, and this must be treated as an operational rule,
  not just a footnote:
  - The old image can still write to the legacy `first_contact_*` text columns through its own,
    unmodified UI.
  - Any first-contact change made through that old UI during the rollback window is **not**
    automatically reflected in the new foreign keys after the new image is redeployed — there is no
    dual-write to carry it over.
  - Consequently, during such a rollback, first-contact data should be treated as **read-only**, or
    the two representations must be **manually reconciled** before the new image is restored.
    Silently trusting the new FKs after a rollback-and-forward-roll risks losing whatever was
    written through the old UI in between.

### Consequences

- **Easier:** contacts are entered once per owner and reused across all their animals; a phone
  number or address change propagates to every animal automatically. `tel:`/`mailto:`/website links
  and a proper contact-management UI become possible. The domain has a clear extension path for
  vet ↔ place M2M relationships, structured FKs on visit notes, pricing, and ratings — all
  additive, none requiring a redesign of this decision, so these backlog items have a concrete path
  forward.
- **Harder:** the feature now spans two PRs ("expand" and "contract") separated by an observation
  window, rather than a single self-contained change — a rollback after the contract PR requires a
  database backup, not just an image pin. Any code path that reads first-contact must, for the
  rest of the compatibility window, be aware that either representation (legacy text or FK) may be
  the current source of truth for a given animal. Deferring pricing, ratings, the Vet↔Place
  relationship, and structured FKs on visit notes to the backlog means those original ADR-01 scope
  items remain unimplemented for now.
- **Follow-up documentation debt:** ADR-01 (scope note on pricing/ratings), ADR-09 (`Animal` field
  table, the new `blank=True, default=""` idiom deviation, and the `vet_contact` sharing
  description) and ADR-12 (snapshot rendering note) are updated once the feature actually lands
  (tracked as a later stage of this same plan), not as part of this decisions-only record.

### Keywords
- vet contact,
- medical place,
- contact book,
- expand-contract migration,
- first contact,
- veterinary app.

### Links
- ADR-01 (core functionality scope — originally listed "healthcare place and vet profiles")
- ADR-09 (data model — `Animal` fields and sharing; to be updated once this feature lands)
- ADR-12 (offline snapshots — schema compatibility contract kept intact by this decision)
