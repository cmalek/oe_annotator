"""Sentence model."""

from __future__ import annotations

import builtins
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.note import Note
from oeapp.models.token import Token
from oeapp.utils import from_utc_iso, to_utc_iso

if TYPE_CHECKING:
    from collections.abc import Callable

    from oeapp.models.project import Project


class Sentence(Base):
    """
    Represents a sentence.

    A sentences has these characteristics:
    - A project ID
    - A display order
    - An Old English text
    - A Modern English translation
    - A list of tokens
    - A list of notes

    A sentence is related to a project by the project ID.
    A sentence is related to a list of tokens by the token ID.
    A sentence is related to a list of notes by the note ID.
    """

    __tablename__ = "sentences"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "display_order", name="uq_sentences_project_order"
        ),
    )

    #: The sentence ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The project ID.
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    #: The display order of the sentence in the project.
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The Old English text.
    text_oe: Mapped[str] = mapped_column(String, nullable=False)
    #: The Modern English translation.
    text_modern: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The date and time the sentence was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    #: The date and time the sentence was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="sentences")
    tokens: Mapped[builtins.list[Token]] = relationship(
        "Token",
        back_populates="sentence",
        cascade="all, delete-orphan",
        order_by="Token.order_index",
        lazy="select",  # Load tokens when accessed
    )
    notes: Mapped[builtins.list[Note]] = relationship(
        "Note", back_populates="sentence", cascade="all, delete-orphan"
    )

    @classmethod
    def get(cls, session: Session, sentence_id: int) -> Sentence | None:
        """
        Get a sentence by ID.
        """
        return session.get(cls, sentence_id)

    @classmethod
    def list(cls, session: Session, project_id: int) -> builtins.list[Sentence]:
        """
        Check if a sentence exists by project ID and display order.
        """
        return builtins.list(
            session.scalars(
                select(cls)
                .where(
                    cls.project_id == project_id,
                )
                .order_by(cls.display_order)
            ).all()
        )

    @classmethod
    def get_next_sentence(
        cls, session: Session, project_id: int, display_order: int
    ) -> Sentence | None:
        """
        Get the next sentence by project ID and display order.

        Args:
            session: SQLAlchemy session
            project_id: Project ID
            display_order: Display order

        Returns:
            The next sentence or None if there is no next sentence

        """
        stmt = (
            select(Sentence)
            .where(
                cls.project_id == project_id,
                cls.display_order == display_order,
            )
            .limit(1)
        )
        return session.scalar(stmt)

    @classmethod
    def create(
        cls, session: Session, project_id: int, display_order: int, text_oe: str
    ) -> Sentence:
        """
        Import an entire OE text into a project.

        The text is split into sentences and each sentence is imported into
        the project.  The display order is the index of the sentence in the
        text.

        Args:
            session: SQLAlchemy session
            project_id: Project ID
            display_order: Display order
            text_oe: Old English text

        Returns:
            The new :class:`~oeapp.models.sentence.Sentence` object

        """
        sentence = cls(
            project_id=project_id,
            display_order=display_order,
            text_oe=text_oe,
        )
        session.add(sentence)
        session.flush()  # Get the ID

        # Create tokens from sentence text
        tokens = Token.create_from_sentence(
            session=session, sentence_id=sentence.id, sentence_text=text_oe
        )
        sentence.tokens = tokens

        session.commit()
        return sentence

    @classmethod
    def subsequent_sentences(
        cls, session: Session, project_id: int, display_order: int
    ) -> builtins.list[Sentence]:
        """
        Get the subsequent sentences by project ID and display order.

        Args:
            session: SQLAlchemy session
            project_id: Project ID
            display_order: Display order

        Returns:
            List of subsequent sentences

        """
        return builtins.list(
            session.scalars(
                select(cls)
                .where(cls.project_id == project_id, cls.display_order > display_order)
                .order_by(cls.display_order)
            ).all()
        )

    @classmethod
    def renumber_sentences(
        cls,
        session: Session,
        sentences: builtins.list[Sentence],
        order_mapping: dict[int, int] | None = None,
        order_function: Callable[[Sentence], int] | None = None,
    ) -> builtins.list[tuple[int, int, int]]:
        """
        Update display_order for multiple sentences using two-phase approach.

        This method safely updates display_order values for multiple sentences
        to avoid unique constraint violations on (project_id, display_order).

        Args:
            session: SQLAlchemy session
            sentences: List of sentences to update
            order_mapping: Optional dict mapping sentence.id -> new display_order
            order_function: Optional function taking Sentence -> new display_order

        Returns:
            List of (sentence_id, old_order, new_order) tuples tracking changes

        Raises:
            ValueError: If neither order_mapping nor order_function is provided

        """
        if not sentences:
            return []

        if order_mapping is None and order_function is None:
            msg = "Either order_mapping or order_function must be provided"
            raise ValueError(msg)

        # Track old orders before Phase 1
        old_orders = {s.id: s.display_order for s in sentences}

        # Phase 1: Move to temporary positions
        temp_offset = -10000
        for sentence in sentences:
            sentence.display_order = temp_offset
            temp_offset -= 1
            session.add(sentence)
        session.flush()

        # Phase 2: Move to final positions
        # CRITICAL: Use old_orders for computation, not current sentence.display_order
        # because sentences have been moved to temporary positions in Phase 1
        changes: builtins.list[tuple[int, int, int]] = []
        for sentence in sentences:
            old_order = old_orders[sentence.id]
            if order_mapping:
                new_order = order_mapping[sentence.id]
            else:
                assert order_function is not None  # noqa: S101
                # Temporarily restore display_order for order_function computation
                # The order_function needs to see the original display_order value
                sentence.display_order = old_order
                new_order = order_function(sentence)
            sentence.display_order = new_order
            changes.append((sentence.id, old_order, new_order))
            session.add(sentence)
        session.flush()

        return changes

    @classmethod
    def restore_display_orders(
        cls,
        session: Session,
        changes: builtins.list[tuple[int, int, int]],
    ) -> None:
        """
        Restore display_order values using two-phase approach.

        This method safely restores display_order values from a list of changes,
        where each change is (sentence_id, old_order, new_order). It restores
        sentences to their old_order values.

        Args:
            session: SQLAlchemy session
            changes: List of (sentence_id, old_order, new_order) tuples

        """
        if not changes:
            return

        # Phase 1: Move to temporary positions
        temp_offset = -10000
        for sentence_id, _old_order, _new_order in changes:
            sentence = cls.get(session, sentence_id)
            if sentence:
                sentence.display_order = temp_offset
                temp_offset -= 1
                session.add(sentence)
        session.flush()

        # Phase 2: Restore original display_order values
        # Sort by old_order descending (process in reverse order)
        sorted_changes: builtins.list[tuple[int, int, int]] = sorted(
            changes, key=lambda x: x[1], reverse=True
        )
        for sentence_id, old_order, _new_order in sorted_changes:
            sentence = cls.get(session, sentence_id)
            if sentence:
                sentence.display_order = old_order
                session.add(sentence)
        session.flush()

    def to_json(self, session: Session) -> dict:
        """
        Serialize sentence to JSON-compatible dictionary (without PKs).

        Args:
            session: SQLAlchemy session (needed for token lookups in notes)

        Returns:
            Dictionary containing sentence data with tokens and notes

        """
        sentence_data: dict = {
            "display_order": self.display_order,
            "text_oe": self.text_oe,
            "text_modern": self.text_modern,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
            "tokens": [],
            "notes": [],
        }

        # Sort tokens by order_index
        tokens = sorted(self.tokens, key=lambda t: t.order_index)
        for token in tokens:
            sentence_data["tokens"].append(token.to_json())

        # Add notes
        for note in self.notes:
            note_data = note.to_json(session)
            sentence_data["notes"].append(note_data)

        return sentence_data

    @classmethod
    def from_json(
        cls, session: Session, project_id: int, sentence_data: dict
    ) -> Sentence:
        """
        Create a sentence and all related entities from JSON import data.

        Args:
            session: SQLAlchemy session
            project_id: Project ID to attach sentence to
            sentence_data: Sentence data dictionary from JSON

        Returns:
            Created Sentence entity

        """
        sentence = cls(
            project_id=project_id,
            display_order=sentence_data["display_order"],
            text_oe=sentence_data["text_oe"],
            text_modern=sentence_data.get("text_modern"),
        )
        created_at = from_utc_iso(sentence_data.get("created_at"))
        if created_at:
            sentence.created_at = created_at
        updated_at = from_utc_iso(sentence_data.get("updated_at"))
        if updated_at:
            sentence.updated_at = updated_at

        session.add(sentence)
        session.flush()

        # Create tokens and build token map
        token_map: dict[int, Token] = {}
        for token_data in sentence_data.get("tokens", []):
            token = Token.from_json(session, sentence.id, token_data)
            token_map[token.order_index] = token

        # Create notes
        for note_data in sentence_data.get("notes", []):
            Note.from_json(session, sentence.id, note_data, token_map)

        return sentence

    def update(self, session, text_oe: str) -> Sentence:
        """
        Update the sentence.

        Args:
            session: SQLAlchemy session
            text_oe: New Old English text

        Returns:
            Updated sentence

        """
        self.text_oe = text_oe
        Token.update_from_sentence(session, text_oe, self.id)
        session.commit()
        # Refresh to get updated tokens
        session.refresh(self)
        return self
