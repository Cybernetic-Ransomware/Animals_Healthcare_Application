"""DDL for the read-only animal snapshot file (see ADR-12).

The snapshot is a standard SQLite-format database. PostgreSQL remains the
source of truth; the file is a disposable cache that can be deleted and
rebuilt at any time. Binary attachment content never enters the snapshot —
attachments are represented by metadata rows pointing back to CouchDB.

is_read_only in the manifest marks an application contract (AHC never writes
to a generated snapshot), not a filesystem guarantee — the file itself stays
writable.
"""

# Bumped only for breaking changes; additive changes (new tables, new
# nullable/defaulted columns) keep the version. See the compatibility
# contract in ADR-12, stage 5.
SCHEMA_VERSION = 1

# Provenance only ("which exporter code wrote this file") — never consulted
# for compatibility decisions. Kept in sync with pyproject.toml manually.
# Absent (NULL column) in files written before ADR-12 stage 5.
EXPORTER_VERSION = "0.1.0"

# Kept in sync with TABLES below; consumed by the snapshot inspector.
# All tables listed here are required in a schema_version 1 file. When a
# future additive table is introduced, split this into required vs optional
# so readers do not reject older files that legitimately lack it.
TABLE_NAMES = (
    "snapshot_manifest",
    "animal_snapshot",
    "medical_record_snapshot",
    "feeding_note_snapshot",
    "biometric_snapshot",
    "vaccination_note_snapshot",
    "attachment_metadata_snapshot",
)

TABLES = (
    """
    CREATE TABLE snapshot_manifest (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        animal_id TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        exporter_version TEXT,
        source_revision TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        generated_by TEXT,
        is_read_only INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE animal_snapshot (
        id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        species TEXT,
        breed TEXT,
        sex TEXT,
        birthdate TEXT,
        dietary_restrictions TEXT,
        first_contact_vet TEXT,
        first_contact_medical_place TEXT,
        last_control_visit TEXT,
        next_visit_date TEXT
    )
    """,
    """
    CREATE TABLE medical_record_snapshot (
        id TEXT PRIMARY KEY,
        animal_id TEXT NOT NULL,
        date_creation TEXT,
        date_updated TEXT,
        date_event_started TEXT,
        date_event_ended TEXT,
        participants TEXT,
        place TEXT,
        short_description TEXT NOT NULL,
        full_description TEXT,
        type_of_event TEXT,
        tags_json TEXT
    )
    """,
    """
    CREATE TABLE feeding_note_snapshot (
        id INTEGER PRIMARY KEY,
        medical_record_id TEXT NOT NULL,
        real_start_date TEXT,
        real_end_date TEXT,
        is_medicine INTEGER NOT NULL,
        category TEXT,
        product_name TEXT,
        producer TEXT,
        dose_annotations TEXT,
        purchase_source TEXT
    )
    """,
    """
    CREATE TABLE biometric_snapshot (
        id INTEGER PRIMARY KEY,
        animal_id TEXT NOT NULL,
        related_note_id TEXT,
        date_updated TEXT,
        weight TEXT,
        weight_unit TEXT,
        height TEXT,
        height_unit TEXT,
        custom_name TEXT,
        custom_value TEXT,
        custom_unit TEXT
    )
    """,
    """
    CREATE TABLE vaccination_note_snapshot (
        id TEXT PRIMARY KEY,
        medical_record_id TEXT NOT NULL,
        vaccine_name TEXT,
        last_vaccination_date TEXT,
        valid_until TEXT,
        suggested_clinic TEXT
    )
    """,
    """
    CREATE TABLE attachment_metadata_snapshot (
        id TEXT PRIMARY KEY,
        medical_record_id TEXT NOT NULL,
        file_name TEXT,
        description TEXT,
        couch_id TEXT,
        upload_date TEXT
    )
    """,
)


def create_schema(conn) -> None:
    """Create all snapshot tables on a fresh connection."""
    for ddl in TABLES:
        conn.execute(ddl)
    conn.commit()
