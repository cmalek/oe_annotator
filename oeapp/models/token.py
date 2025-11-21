"""Token model."""

import re
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.annotation import Annotation

if TYPE_CHECKING:
    from oeapp.models.sentence import Sentence


class Token(Base):
    """Represents a tokenized word in a sentence."""

    __tablename__ = "tokens"
    __table_args__ = (
        UniqueConstraint("sentence_id", "order_index", name="uq_tokens_sentence_order"),
    )

    #: The Old English characters. These are the characters that are allowed in
    #: the surface form of a token beyond the basic Latin characters.
    OE_CHARS: ClassVar[str] = "þÞðÐæǣÆǢȝġĠċĊāĀȳȲēĒīĪūŪōŌū"
    #: The value of the order index that indicates a token is no longer in the
    #: sentence.
    NO_ORDER_INDEX: ClassVar[int] = -1

    #: The token ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The sentence ID.
    sentence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False
    )
    #: The order index of the token in the sentence.
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The surface form of the token.
    surface: Mapped[str] = mapped_column(String, nullable=False)
    #: The lemma of the token.
    lemma: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The date and time the token was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    #: The date and time the token was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    sentence: Mapped[Sentence] = relationship("Sentence", back_populates="tokens")
    annotation: Mapped[Annotation | None] = relationship(
        "Annotation",
        back_populates="token",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @classmethod
    def create_from_sentence(
        cls, session, sentence_id: int, sentence_text: str
    ) -> list[Token]:
        """
        Create new tokens for a sentence.

        There's no need to deal with individual tokens, as they are explicitly
        bound to the sentence, thus instead of :meth:`import` taking a token id
        or surface, it takes the sentence text and sentence id.

        Args:
            session: SQLAlchemy session
            sentence_id: Sentence ID
            sentence_text: Text of the sentence to tokenize

        Returns:
            List of :class:`~oeapp.models.token.Token` objects

        """
        # Tokenize sentence
        token_strings = cls.tokenize(sentence_text)
        tokens = []
        for token_index, token_surface in enumerate(token_strings):
            token = cls(
                sentence_id=sentence_id,
                order_index=token_index,
                surface=token_surface,
            )
            session.add(token)
            session.flush()  # Get the ID

            existing_annotation = session.scalar(
                select(Annotation).where(Annotation.token_id == token.id)
            )
            if not existing_annotation:
                annotation = Annotation(token_id=token.id)
                session.add(annotation)

            tokens.append(token)
        session.flush()
        return tokens

    @classmethod
    def tokenize(cls, sentence_text: str) -> list[str]:
        """
        Tokenize a sentence.

        Args:
            sentence_text: Text of the sentence to tokenize

        Returns:
            List of token strings

        """
        # Split on whitespace, but preserve punctuation as separate tokens
        # This handles Old English characters like þ, ð, æ, etc.
        tokens = []
        # Use regex to split on whitespace while preserving punctuation
        words = re.split(r"\s+", sentence_text.strip())
        for word in words:
            if not word:
                continue
            # Skip standalone punctuation marks
            if word in [",", ";", ":", "!", "?", "-", "—", '"', "'", "."]:
                continue
            # Check for punctuation-quote combinations (?" ." !") - skip these
            if re.match(r'^[.!?]+["\']+$', word):
                continue
            # Split punctuation from words
            # Match word characters (including Old English chars) and punctuation
            # separately
            pattern = rf'[\w{re.escape(cls.OE_CHARS)}]+|[.,;:!?\-—"\'.]+'
            parts = re.findall(pattern, word)
            # Filter out quotes and standalone punctuation
            # Also filter out punctuation-quote combinations
            filtered_parts = []
            for part in parts:
                # Skip standalone punctuation marks
                if part in [",", ";", ":", "!", "?", "-", "—", '"', "'", "."]:
                    continue
                # Skip punctuation-quote combinations (like ?" ." !")
                if re.match(r'^[.!?]+["\']+$', part):
                    continue
                filtered_parts.append(part)
            tokens.extend(filtered_parts)

        # Filter out closing punctuation at the end of the token list
        # Remove trailing .!? tokens (even without quotes) - these are closing
        # punctuation that should remain in sentence text but not be tokenized
        while tokens and tokens[-1] in (".", "!", "?"):
            tokens.pop()

        return tokens

    @classmethod
    def update_from_sentence(  # noqa: PLR0912, PLR0915
        cls, session, sentence_text: str, sentence_id: int
    ) -> None:
        """
        Update all the tokens in the sentence, removing any tokens that are no
        longer in the sentence, and adding any new tokens.

        We will also re-order the tokens to match the order of the tokens in the
        sentence.

        There's no need to deal with individual tokens, as they are explicitly
        bound to the sentence, thus instead of :meth:`update` taking a token id
        or surface, it takes the sentence text and sentence id.

        The goal is to update the text of the sentence without losing any
        annotations on the tokens that need to remain.

        The algorithm uses a two-phase matching approach:
        1. Phase 1: Match tokens at same position with same surface (exact matches)
        2. Phase 2: Match remaining tokens by surface only (handles reordering,
           edits, duplicates)

        Each existing token can only be matched once, ensuring duplicate tokens
        (e.g., "swā swā") are handled correctly.

        Args:
            session: SQLAlchemy session
            sentence_text: Text of the sentence to tokenize
            sentence_id: Sentence ID

        """
        # Tokenize the new sentence text
        token_strings = cls.tokenize(sentence_text)

        # Get existing tokens ordered by order_index
        stmt = (
            select(cls).where(cls.sentence_id == sentence_id).order_by(cls.order_index)
        )
        existing_tokens = list(session.scalars(stmt).all())

        # Phase 1: Match tokens at same position
        # (handles exact matches and position-based surface updates)
        matched_positions: dict[int, Token] = {}
        matched_token_ids: set[int] = set()

        # Build a mapping of position -> existing token for quick lookup
        position_to_token = {token.order_index: token for token in existing_tokens}

        for new_index, new_surface in enumerate(token_strings):
            if new_index in position_to_token:
                existing_token = position_to_token[new_index]
                if existing_token.id is not None:
                    # Token exists at this position - match it (even if surface differs)
                    matched_positions[new_index] = existing_token
                    matched_token_ids.add(existing_token.id)
                    # Update surface if it changed (preserves annotation and notes)
                    if existing_token.surface != new_surface:
                        existing_token.surface = new_surface
                        session.add(existing_token)

        # Phase 2: Match remaining unmatched tokens by surface only
        # Get list of unmatched existing tokens
        unmatched_existing = [
            token
            for token in existing_tokens
            if token.id is not None and token.id not in matched_token_ids
        ]

        # Move all unmatched existing tokens to temporary negative positions
        # to avoid unique constraint violations during updates
        temp_offset = -(len(existing_tokens) + len(token_strings) + 1)
        for token in unmatched_existing:
            token.order_index = temp_offset
            session.add(token)
            temp_offset += 1
        session.flush()

        # Now match remaining positions by surface
        for new_index, new_surface in enumerate(token_strings):
            if new_index not in matched_positions:
                # Try to find an unmatched existing token with matching surface
                matched = False
                for existing_token in unmatched_existing:
                    if (
                        existing_token.surface == new_surface
                        and existing_token.id is not None
                    ):
                        # Match found - use this existing token
                        matched_positions[new_index] = existing_token
                        matched_token_ids.add(existing_token.id)
                        unmatched_existing.remove(existing_token)
                        # Update surface (in case it changed) and order_index
                        # Safe to update now since we moved all tokens to temp positions
                        existing_token.surface = new_surface
                        existing_token.order_index = new_index
                        session.add(existing_token)
                        matched = True
                        break

                if not matched:
                    # No match found - create a new token
                    new_token = cls(
                        sentence_id=sentence_id,
                        order_index=new_index,
                        surface=new_surface,
                    )
                    session.add(new_token)
                    session.flush()  # Get the ID

                    # Create empty annotation for new token
                    existing_annotation = session.scalar(
                        select(Annotation).where(Annotation.token_id == new_token.id)
                    )
                    if not existing_annotation:
                        annotation = Annotation(token_id=new_token.id)
                        session.add(annotation)

                    matched_positions[new_index] = new_token

        session.flush()

        # Update order_index for tokens that were matched in Phase 1 but may need
        # their order_index updated (shouldn't happen, but ensure consistency)
        for new_index, token in matched_positions.items():
            if token.order_index != new_index:
                token.order_index = new_index
                session.add(token)

        session.flush()

        # Delete tokens that weren't matched (they no longer exist in the sentence)
        # Cascade delete will handle annotations and notes
        for token in existing_tokens:
            if token.id and token.id not in matched_token_ids:
                session.delete(token)

        session.flush()

        # Final verification: ensure all positions are filled and sequential
        if len(matched_positions) != len(token_strings):
            msg = (
                f"Position count mismatch: expected {len(token_strings)} "
                f"positions, found {len(matched_positions)} in matched_positions"
            )
            raise ValueError(msg)

        # Ensure all tokens are numbered sequentially (0, 1, 2, ...)
        for new_index in range(len(token_strings)):
            if new_index not in matched_positions:
                msg = f"Missing token at position {new_index}"
                raise ValueError(msg)
            token = matched_positions[new_index]
            if token.order_index != new_index:
                token.order_index = new_index
                session.add(token)

        session.commit()
