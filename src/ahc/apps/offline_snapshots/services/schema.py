"""DDL for the read-only animal snapshot file (see ADR-12).

The snapshot is a standard SQLite-format database. PostgreSQL remains the
source of truth; the file is a disposable cache that can be deleted and
rebuilt at any time. Binary attachment content never enters the snapshot —
attachments are represented by metadata rows pointing back to CouchDB.
"""

SCHEMA_VERSION = 1

TABLES = (
    """
    CREATE TABLE snapshot_manifest (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        animal_id TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
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
