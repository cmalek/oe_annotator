"""Database service for Old English Annotator."""

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType


class Database:
    """Manages SQLite database connection and schema."""

    def __init__(self, db_path: str | Path):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file

        """
        #: The path to the SQLite database file.
        self.db_path = Path(db_path)
        #: The database connection.
        self.conn: sqlite3.Connection | None = None
        self._connect()

    def _connect(self) -> None:
        """
        Establish database connection with proper settings.
        """
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys=ON")
        # Enable WAL mode for concurrent reads
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        """
        Create database schema if it doesn't exist.
        """
        if not self.conn:
            msg = "Database connection not established"
            raise ValueError(msg)
        cursor = self.conn.cursor()

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sentences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                display_order INTEGER NOT NULL,
                text_oe TEXT NOT NULL,
                text_modern TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, display_order)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentences_project_order
            ON sentences(project_id, display_order)
        """)

        # Tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
                order_index INTEGER NOT NULL,
                surface TEXT NOT NULL,
                lemma TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sentence_id, order_index)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tokens_sentence_order
            ON tokens(sentence_id, order_index)
        """)

        # Annotations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                token_id INTEGER PRIMARY KEY REFERENCES tokens(id) ON DELETE CASCADE,
                pos TEXT CHECK(pos IN ('N','V','A','R','D','B','C','E','I')),
                gender TEXT CHECK(gender IN ('m','f','n')),
                number TEXT CHECK(number IN ('s','p')),
                "case" TEXT CHECK("case" IN ('n','a','g','d','i')),
                declension TEXT,
                pronoun_type TEXT CHECK(pronoun_type IN ('p','r','d','i')),
                verb_class TEXT,
                verb_tense TEXT CHECK(verb_tense IN ('p','n')),
                verb_person INTEGER CHECK(verb_person IN (1,2,3)),
                verb_mood TEXT CHECK(verb_mood IN ('i','s','imp')),
                verb_aspect TEXT CHECK(verb_aspect IN ('p','f','prg','gn')),
                verb_form TEXT CHECK(verb_form IN ('f','i','p')),
                prep_case TEXT CHECK(prep_case IN ('a','d','g')),
                uncertain BOOLEAN DEFAULT 0,
                alternatives_json TEXT,
                confidence INTEGER CHECK(confidence >= 0 AND confidence <= 100),
                last_inferred_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_annotations_pos ON annotations(pos)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_annotations_uncertain ON annotations(uncertain)
        """)  # noqa: E501

        # Notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
                start_token INTEGER REFERENCES tokens(id) ON DELETE CASCADE,
                end_token INTEGER REFERENCES tokens(id) ON DELETE CASCADE,
                note_text_md TEXT NOT NULL,
                note_type TEXT NOT NULL CHECK(note_type IN ('token','span','sentence')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_sentence ON notes(sentence_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_token ON notes(start_token)
        """)

        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('INSERT','UPDATE','DELETE')),
                diff_json TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_entity
            ON audit_log(entity_type, entity_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp)
        """)

        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()
