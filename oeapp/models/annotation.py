"""Annotation model."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from oeapp.exc import DoesNotExist

if TYPE_CHECKING:
    from datetime import datetime

    from oeapp.services.db import Database


@dataclass
class Annotation:
    """Represents grammatical/morphological annotations for a token."""

    #: The database.
    db: Database
    #: The token ID.
    token_id: int
    #: The Part of Speech.
    pos: str | None = None  # N, V, A, R, D, B, C, E, I
    #: The gender.
    gender: str | None = None  # m, f, n
    #: The number.
    number: str | None = None  # s, p
    #: The case.
    case: str | None = None  # n, a, g, d, i (reserved keyword, use "case" in SQL)
    #: The declension.
    declension: str | None = None
    #: The pronoun type.
    pronoun_type: str | None = None  # p, r, d, i
    #: The verb class.
    verb_class: str | None = None
    #: The verb tense.
    verb_tense: str | None = None  # p, n
    #: The verb person.
    verb_person: int | None = None  # 1, 2, 3
    #: The verb mood.
    verb_mood: str | None = None  # i, s, imp
    #: The verb aspect.
    verb_aspect: str | None = None  # p, f, prg, gn
    #: The verb form.
    verb_form: str | None = None  # f, i, p
    #: The preposition case.
    prep_case: str | None = None  # a, d, g
    #: Whether the annotation is uncertain.
    uncertain: bool = False
    #: The alternatives in JSON format.
    alternatives_json: str | None = None
    #: The confidence in the annotation.
    confidence: int | None = None  # 0-100
    #: The last inferred JSON.
    last_inferred_json: str | None = None
    #: The date and time the annotation was last updated.
    updated_at: datetime | None = None

    @classmethod
    def get(cls, db: Database, token_id: int) -> Annotation:
        """
        Get an annotation by token ID.
        """
        cursor = db.cursor
        cursor.execute("SELECT * FROM annotations WHERE token_id = ?", (token_id,))
        row = cursor.fetchone()
        if not row:
            raise DoesNotExist("Annotation", token_id)  # noqa: EM101
        return cls(db=db, **row)

    @classmethod
    def create(cls, db: Database, token_id: int) -> Annotation:
        """
        Create a new annotation for a token.
        """
        cursor = db.cursor
        cursor.execute("INSERT INTO annotations (token_id) VALUES (?)", (token_id,))
        return cls(db=db, token_id=token_id)

    def save(self) -> None:
        """
        Save the annotation to the database.
        """
        cursor = self.db.cursor
        cursor.execute(
            """UPDATE annotations SET pos = ?, gender = ?, number = ?, "case" = ?, declension = ?, pronoun_type = ?, verb_class = ?, verb_tense = ?, verb_person = ?, verb_mood = ?, verb_aspect = ?, verb_form = ?, prep_case = ?, uncertain = ?, alternatives_json = ?, confidence = ?, updated_at = CURRENT_TIMESTAMP WHERE token_id = ?
            """,  # noqa: E501
            (
                self.pos,
                self.gender,
                self.number,
                self.case,
                self.declension,
                self.pronoun_type,
                self.verb_class,
                self.verb_tense,
                self.verb_person,
                self.verb_mood,
                self.verb_aspect,
                self.verb_form,
                self.prep_case,
                self.uncertain,
                self.alternatives_json,
                self.confidence,
                self.token_id,
            ),
        )
        self.db.conn.commit()

    def delete(self) -> None:
        """
        Delete the annotation.
        """
        cursor = self.db.cursor
        cursor.execute("DELETE FROM annotations WHERE token_id = ?", (self.token_id,))
        self.db.commit()
