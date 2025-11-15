"""Note model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from oeapp.exc import DoesNotExist

if TYPE_CHECKING:
    import builtins
    from datetime import datetime

    from oeapp.services.db import Database


@dataclass
class Note:
    """Represents a note attached to tokens, spans, or sentences."""

    #: The database.
    db: Database
    #: The note ID.
    id: int | None
    #: The sentence ID.
    sentence_id: int
    #: The start token ID.
    start_token: int | None = None
    #: The end token ID.
    end_token: int | None = None
    #: The note text in Markdown format.
    note_text_md: str = ""
    #: The note type.
    note_type: str = "token"  # token, span, sentence
    #: The date and time the note was created.
    created_at: datetime | None = None
    #: The date and time the note was last updated.
    updated_at: datetime | None = None

    @classmethod
    def list(cls, db: Database, sentence_id: int) -> builtins.list[Note]:
        """
        List all notes for a sentence.
        """
        cursor = db.cursor
        cursor.execute("SELECT * FROM notes WHERE sentence_id = ?", (sentence_id,))
        return [cls(db=db, **row) for row in cursor.fetchall()]

    @classmethod
    def get(cls, db: Database, note_id: int) -> Note:
        """
        Get a note by ID.
        """
        cursor = db.cursor
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            raise DoesNotExist("Note", note_id)  # noqa: EM101
        return cls(db=db, **row)

    @classmethod
    def create(
        cls, db: Database, sentence_id: int, note_text_md: str, note_type: str
    ) -> Note:
        """
        Create a new note for a sentence.
        """
        cursor = db.cursor
        cursor.execute(
            "INSERT INTO notes (sentence_id, note_text_md, note_type) VALUES (?, ?, ?)",
            (sentence_id, note_text_md, note_type),
        )
        return cls(
            db=db,
            id=cursor.lastrowid,
            sentence_id=sentence_id,
            note_text_md=note_text_md,
            note_type=note_type,
        )

    def save(self) -> None:
        """
        Save the note to the database.
        """
        if not self.id:
            self.create(self.db, self.sentence_id, self.note_text_md, self.note_type)
        else:
            cursor = self.db.cursor
            cursor.execute(
                "UPDATE notes SET note_text_md = ?, note_type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",  # noqa: E501
                (self.note_text_md, self.note_type, cast("int", self.id)),
            )
            self.db.commit()

    def delete(self) -> None:
        """
        Delete the note.
        """
        if not self.id:
            return
        cursor = self.db.cursor
        cursor.execute("DELETE FROM notes WHERE id = ?", (cast("int", self.id),))
        self.db.commit()
