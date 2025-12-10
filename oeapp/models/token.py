"""Token model."""

import builtins
import re
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.annotation import Annotation
from oeapp.utils import from_utc_iso, to_utc_iso

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

    def to_json(self) -> dict:
        """
        Serialize token to JSON-compatible dictionary (without PKs).

        Returns:
            Dictionary containing token data with annotation if exists

        """
        token_data: dict = {
            "order_index": self.order_index,
            "surface": self.surface,
            "lemma": self.lemma,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
        }

        # Add annotation if it exists
        if self.annotation:
            token_data["annotation"] = self.annotation.to_json()

        return token_data

    @classmethod
    def from_json(cls, session: Session, sentence_id: int, token_data: dict) -> Token:
        """
        Create a token and annotation from JSON import data.

        Args:
            session: SQLAlchemy session
            sentence_id: Sentence ID to attach token to
            token_data: Token data dictionary from JSON

        Returns:
            Created Token entity

        """
        token = cls(
            sentence_id=sentence_id,
            order_index=token_data["order_index"],
            surface=token_data["surface"],
            lemma=token_data.get("lemma"),
        )
        created_at = from_utc_iso(token_data.get("created_at"))
        if created_at:
            token.created_at = created_at
        updated_at = from_utc_iso(token_data.get("updated_at"))
        if updated_at:
            token.updated_at = updated_at

        session.add(token)
        session.flush()

        # Create annotation if it exists
        if "annotation" in token_data:
            Annotation.from_json(session, token.id, token_data["annotation"])

        return token

    @classmethod
    def get(cls, session: Session, token_id: int) -> Token | None:
        """
        Get a token by ID.

        Args:
            session: SQLAlchemy session
            token_id: Token ID

        Returns:
            Token or None if not found

        """
        return session.get(cls, token_id)

    @classmethod
    def list(cls, session: Session, sentence_id: int) -> builtins.list[Token]:
        """
        Get all tokens by sentence ID, ordered by order index.

        Args:
            session: SQLAlchemy session
            sentence_id: Sentence ID

        Returns:
            List of tokens ordered by order index

        """
        return builtins.list(
            session.scalars(
                select(cls)
                .where(cls.sentence_id == sentence_id)
                .order_by(cls.order_index)
            ).all()
        )

    @classmethod
    def create_from_sentence(
        cls, session, sentence_id: int, sentence_text: str
    ) -> builtins.list[Token]:
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

            if not Annotation.exists(session, token.id):
                annotation = Annotation(token_id=token.id)
                session.add(annotation)

            tokens.append(token)
        session.flush()
        return tokens

    @classmethod
    def _update_notes_for_token_changes(  # noqa: PLR0912, PLR0915
        cls,
        session,
        sentence_id: int,
        old_tokens: builtins.list[Token],
        new_token_positions: dict[int, Token],
        matched_token_ids: set[int],
    ) -> None:
        """
        Update notes when tokens change.

        Args:
            session: SQLAlchemy session
            sentence_id: Sentence ID
            old_tokens: List of old tokens
            new_token_positions: Dict mapping new position to token
            matched_token_ids: Set of token IDs that were matched (kept)

        """
        from oeapp.models.sentence import Sentence  # noqa: PLC0415

        sentence = Sentence.get(session, sentence_id)
        if not sentence or not sentence.notes:
            return

        # Build mapping of old token ID to new token
        old_token_id_to_new: dict[int, Token] = {}
        for token in new_token_positions.values():
            if token.id:
                old_token_id_to_new[token.id] = token

        # Build mapping of old order_index to new token
        old_order_to_new_token: dict[int, Token] = {}
        for old_token in old_tokens:
            if old_token.id and old_token.id in matched_token_ids:
                # This token was kept, find its new position
                for new_token in new_token_positions.values():
                    if new_token.id == old_token.id:
                        old_order_to_new_token[old_token.order_index] = new_token
                        break

        # Process each note
        notes_to_delete = []
        for note in sentence.notes:
            if not note.start_token or not note.end_token:
                # Invalid note, mark for deletion
                notes_to_delete.append(note)
                continue

            # Check if start/end tokens still exist
            start_exists = note.start_token in matched_token_ids
            end_exists = note.end_token in matched_token_ids

            if not start_exists or not end_exists:
                # One or both tokens were deleted
                # Try to find replacement tokens based on position
                # Get old token order indices
                old_start_token = None
                old_end_token = None
                for old_token in old_tokens:
                    if old_token.id == note.start_token:
                        old_start_token = old_token
                    if old_token.id == note.end_token:
                        old_end_token = old_token

                if old_start_token and old_end_token:
                    # Try to find new tokens at same or nearby positions
                    old_start_order = old_start_token.order_index
                    old_end_order = old_end_token.order_index

                    # Find closest new tokens
                    new_start_token = None
                    new_end_token = None
                    min_start_dist = float("inf")
                    min_end_dist = float("inf")

                    for new_pos, new_token in new_token_positions.items():
                        if new_token.id:
                            # Check distance to old start position
                            dist = abs(new_pos - old_start_order)
                            if dist < min_start_dist:
                                min_start_dist = dist
                                new_start_token = new_token

                            # Check distance to old end position
                            dist = abs(new_pos - old_end_order)
                            if dist < min_end_dist:
                                min_end_dist = dist
                                new_end_token = new_token

                    if (
                        new_start_token
                        and new_end_token
                        and new_start_token.id
                        and new_end_token.id
                    ):
                        # Update note with new token IDs
                        note.start_token = new_start_token.id
                        note.end_token = new_end_token.id
                        session.add(note)
                    else:
                        # Cannot find replacement tokens, mark for deletion
                        notes_to_delete.append(note)
                else:
                    # Cannot find old tokens, mark for deletion
                    notes_to_delete.append(note)
            else:
                # Both tokens exist, but check if range is still valid
                # Get new tokens
                new_start_token = old_token_id_to_new.get(note.start_token)
                new_end_token = old_token_id_to_new.get(note.end_token)

                if new_start_token and new_end_token:
                    # Ensure start comes before end
                    if new_start_token.order_index > new_end_token.order_index:
                        # Swap them
                        note.start_token = new_end_token.id
                        note.end_token = new_start_token.id
                        session.add(note)

        # Delete notes that became invalid
        for note in notes_to_delete:
            session.delete(note)

        session.flush()

    @classmethod
    def tokenize(cls, sentence_text: str) -> builtins.list[str]:  # noqa: PLR0912, PLR0915
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

        # Build character class for word characters including Old English chars
        # Escape special regex characters in OE_CHARS
        oe_chars_escaped = re.escape(cls.OE_CHARS)
        word_char_class = rf"[\w{oe_chars_escaped}]"

        # Pattern to match hyphenated words: word_chars + hyphen/en-dash/em-dash
        # + word_chars
        hyphenated_pattern = rf"{word_char_class}+[-–—]{word_char_class}+"  # noqa: RUF001

        # Pattern for remaining words and punctuation
        word_pattern = rf"{word_char_class}+"
        punct_pattern = r'[.,;:!?\-—"\'.]+'

        for word in words:
            if not word:
                continue
            # Skip standalone punctuation marks
            if word in [",", ";", ":", "!", "?", "-", "—", '"', "'", "."]:
                continue
            # Check for punctuation-quote combinations (?" ." !") - skip these
            if re.match(r'^[.!?]+["\']+$', word):
                continue

            # First, extract hyphenated words
            hyphenated_matches = list(re.finditer(hyphenated_pattern, word))

            if hyphenated_matches:
                # Process hyphenated words and remaining text
                last_end = 0
                processed_ranges = []

                for match in hyphenated_matches:
                    # Add any text before this hyphenated word
                    before_text = word[last_end : match.start()]
                    if before_text:
                        # Tokenize the text before the hyphenated word
                        parts = re.findall(
                            rf"{word_pattern}|{punct_pattern}", before_text
                        )
                        for part in parts:
                            # Skip commas, colons, semicolons, hyphens, quotes
                            # (attached punctuation)
                            if part in [",", ";", ":", "-", "—", '"', "'"]:
                                continue
                            # Skip punctuation-quote combinations
                            if re.match(r'^[.!?]+["\']+$', part):
                                continue
                            tokens.append(part)

                    # Add the hyphenated word as a single token
                    tokens.append(match.group())
                    processed_ranges.append((match.start(), match.end()))
                    last_end = match.end()

                # Add any remaining text after the last hyphenated word
                remaining_text = word[last_end:]
                if remaining_text:
                    # Tokenize remaining text, but skip parts that overlap with
                    # hyphenated words
                    parts = re.findall(
                        rf"{word_pattern}|{punct_pattern}", remaining_text
                    )
                    for part in parts:
                        # Skip commas, colons, semicolons, hyphens, quotes
                        # (attached punctuation)
                        if part in [",", ";", ":", "-", "—", '"', "'"]:
                            continue
                        # Skip punctuation-quote combinations
                        if re.match(r'^[.!?]+["\']+$', part):
                            continue
                        # Check if this part overlaps with any processed hyphenated word
                        part_start_in_word = word.find(part, last_end)
                        if part_start_in_word != -1:
                            part_end_in_word = part_start_in_word + len(part)
                            overlaps = any(
                                start < part_end_in_word and end > part_start_in_word
                                for start, end in processed_ranges
                            )
                            if not overlaps:
                                tokens.append(part)
            else:
                # No hyphenated words, use original logic
                parts = re.findall(rf"{word_pattern}|{punct_pattern}", word)
                for part in parts:
                    # Skip commas, colons, semicolons, hyphens, quotes (attached
                    # punctuation)
                    if part in [",", ";", ":", "-", "—", '"', "'"]:
                        continue
                    # Skip punctuation-quote combinations
                    if re.match(r'^[.!?]+["\']+$', part):
                        continue
                    tokens.append(part)

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
        existing_tokens = cls.list(session, sentence_id)

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
                    if not Annotation.exists(session, new_token.id):
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

        # Update notes for token changes
        cls._update_notes_for_token_changes(
            session, sentence_id, existing_tokens, matched_positions, matched_token_ids
        )

        session.commit()
