"""Note model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, Session, mapped_column, reconstructor, relationship

from oeapp.db import Base
from oeapp.models.token import Token
from oeapp.utils import from_utc_iso, to_utc_iso

if TYPE_CHECKING:
    from oeapp.models.sentence import Sentence


class Note(Base):
    """
    Represents a note attached to tokens, spans, or sentences.
    """

    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint(
            "note_type IN ('token','span','sentence')", name="ck_notes_note_type"
        ),
    )

    #: The note ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The sentence ID.
    sentence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False
    )
    #: The start token ID.
    start_token: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True
    )
    #: The end token ID.
    end_token: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True
    )
    #: The note text in Markdown format.
    note_text_md: Mapped[str] = mapped_column(String, nullable=False, default="")
    #: The note type.
    note_type: Mapped[str] = mapped_column(
        String, nullable=False, default="token"
    )  # token, span, sentence
    #: The date and time the note was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    #: The date and time the note was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    sentence: Mapped[Sentence] = relationship("Sentence", back_populates="notes")
    start_token_rel: Mapped[Token | None] = relationship(
        "Token", foreign_keys=[start_token]
    )
    end_token_rel: Mapped[Token | None] = relationship(
        "Token", foreign_keys=[end_token]
    )

    @reconstructor
    def _sanitize_foreign_keys(self) -> None:
        """
        Sanitize foreign key values when object is reconstructed from database.

        Ensures that nullable foreign keys are None instead of 0 or False,
        which can cause SQLAlchemy mapping errors.
        """
        # Convert 0 or False to None for nullable foreign keys
        if self.start_token == 0 or self.start_token is False:
            self.start_token = None
        if self.end_token == 0 or self.end_token is False:
            self.end_token = None

    @classmethod
    def get(cls, session: Session, note_id: int) -> Note | None:
        """
        Get a note by ID.

        Args:
            session: SQLAlchemy session
            note_id: Note ID

        Returns:
            Note or None if not found

        """
        return session.get(cls, note_id)

    def to_json(self, session: Session) -> dict:
        """
        Serialize note to JSON-compatible dictionary (without PKs).

        Args:
            session: SQLAlchemy session (needed for token lookups)

        Returns:
            Dictionary containing note data

        """
        note_data: dict = {
            "note_text_md": self.note_text_md,
            "note_type": self.note_type,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
        }

        # For notes, we need to reference tokens by order_index
        # since we don't have PKs
        if self.start_token:
            start_token = Token.get(session, self.start_token)
            if start_token:
                note_data["start_token_order_index"] = start_token.order_index
        if self.end_token:
            end_token = Token.get(session, self.end_token)
            if end_token:
                note_data["end_token_order_index"] = end_token.order_index

        return note_data

    @classmethod
    def from_json(
        cls,
        session: Session,
        sentence_id: int,
        note_data: dict,
        token_map: dict[int, Token],
    ) -> Note:
        """
        Create a note from JSON import data.

        Args:
            session: SQLAlchemy session
            sentence_id: Sentence ID to attach note to
            note_data: Note data dictionary from JSON
            token_map: Map of order_index to Token entities

        Returns:
            Created Note entity

        """
        note = cls(
            sentence_id=sentence_id,
            note_text_md=note_data["note_text_md"],
            note_type=note_data.get("note_type", "token"),
        )
        created_at = from_utc_iso(note_data.get("created_at"))
        if created_at:
            note.created_at = created_at
        updated_at = from_utc_iso(note_data.get("updated_at"))
        if updated_at:
            note.updated_at = updated_at

        # Resolve token references by order_index
        # Ensure None instead of False or 0 for nullable foreign keys
        if "start_token_order_index" in note_data:
            order_idx = note_data["start_token_order_index"]
            if order_idx in token_map and token_map[order_idx].id:
                note.start_token = token_map[order_idx].id
            else:
                note.start_token = None
        else:
            note.start_token = None

        if "end_token_order_index" in note_data:
            order_idx = note_data["end_token_order_index"]
            if order_idx in token_map and token_map[order_idx].id:
                note.end_token = token_map[order_idx].id
            else:
                note.end_token = None
        else:
            note.end_token = None

        session.add(note)
        return note
