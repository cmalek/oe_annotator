"""Sentence model."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from oeapp.exc import DoesNotExist
from oeapp.models.token import Token

if TYPE_CHECKING:
    import builtins
    from datetime import datetime

    from oeapp.models.note import Note
    from oeapp.services.db import Database


@dataclass
class Sentence:
    """Represents a sentence."""

    db: Database
    #: The sentence ID.
    id: int | None
    #: The project ID.
    project_id: int
    #: The display order of the sentence in the project.
    display_order: int
    #: The Old English text.
    text_oe: str
    #: The Modern English translation.
    text_modern: str | None = None
    #: The date and time the sentence was created.
    created_at: datetime | None = None
    #: The date and time the sentence was last updated.
    updated_at: datetime | None = None
    # The tokens in the sentence.
    tokens: list[Token] = field(default_factory=list)

    @property
    def notes(self) -> list[Note]:
        """
        Get the notes for the sentence.
        """
        from .note import Note  # noqa: PLC0415

        if not self.id:
            msg = "Sentence has not yet been saved to the database"
            raise ValueError(msg)
        return Note.list(self.db, self.id)

    @classmethod
    def list(cls, db: Database, project_id: int) -> builtins.list[Sentence]:
        """
        List all sentences for a project.
        """
        cursor = db.cursor
        cursor.execute(
            "SELECT id FROM sentences WHERE project_id = ? ORDER BY display_order",
            (project_id,),
        )
        return [cls.get(db, row[0]) for row in cursor.fetchall()]

    @classmethod
    def get(cls, db: Database, sentence_id: int) -> Sentence:
        """
        Get a sentence by ID.

        Args:
            db: Database object
            sentence_id: Sentence ID

        Returns:
            The :class:`~oeapp.models.sentence.Sentence` object

        """
        cursor = db.cursor
        cursor.execute("SELECT * FROM sentences WHERE id = ?", (sentence_id,))
        row = cursor.fetchone()
        if not row:
            raise DoesNotExist("Sentence", sentence_id)  # noqa: EM101
        # row[0] is the sentence ID
        tokens = Token.list(db, sentence_id)
        return cls(
            db=db,
            id=row[0],
            project_id=row[1],
            display_order=row[2],
            text_oe=row[3],
            created_at=row[4],
            updated_at=row[5],
            tokens=tokens,
        )

    @classmethod
    def create(
        cls, db: Database, project_id: int, display_order: int, text_oe: str
    ) -> Sentence:
        """
        Import an entire OE text into a project.

        The text is split into sentences and each sentence is imported into
        the project.  The display order is the index of the sentence in the
        text.

        Args:
            db: Database object
            project_id: Project ID
            display_order: Display order
            text_oe: Old English text

        Returns:
            The new :class:`~oeapp.models.sentence.Sentence` object

        """
        cursor = db.cursor
        cursor.execute(
            "INSERT INTO sentences (project_id, display_order, text_oe) VALUES (?, ?, ?)",  # noqa: E501
            (project_id, display_order, text_oe),
        )
        sentence_id = cursor.lastrowid
        if not sentence_id:
            msg = "Failed to create sentence"
            raise ValueError(msg)
        cursor.execute("SELECT * FROM sentences WHERE id = ?", (sentence_id,))
        data = cursor.fetchone()
        tokens = Token.create_from_sentence(db, data[0], text_oe)
        db.conn.commit()
        return cls(
            db=db,
            id=data[0],
            project_id=data[1],
            display_order=data[2],
            text_oe=data[3],
            created_at=data[5],
            updated_at=data[6],
            tokens=tokens,
        )

    def update(self, text_oe: str) -> Sentence:
        """
        Update the sentence.
        """
        assert self.db.conn is not None, "Database connection not established"  # noqa: S101
        cursor = self.db.conn.cursor()
        cursor.execute(
            "UPDATE sentences SET text_oe = ? WHERE id = ?", (text_oe, self.id)
        )
        self.db.conn.commit()
        Token.update_from_sentence(self.db, text_oe, cast("int", self.id))
        return Sentence.get(self.db, cast("int", self.id))

    def delete(self) -> None:
        """
        Delete the sentence.
        """
        # First delete all tokens in the sentence
        for token in self.tokens:
            token.delete()
        cursor = self.db.cursor
        cursor.execute("DELETE FROM sentences WHERE id = ?", (self.id,))
        self.db.commit()

    def save(self) -> None:
        """
        Save the sentence and its tokens to the database.
        """
        cursor = self.db.cursor
        cursor.execute(
            "UPDATE sentences SET text_oe = ?, text_modern = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",  # noqa: E501
            (self.text_oe, self.text_modern, self.id),
        )
        self.db.commit()
        for token in self.tokens:
            token.save()
