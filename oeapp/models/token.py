"""Token model."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Final, cast

from oeapp.exc import DoesNotExist
from oeapp.models.annotation import Annotation

if TYPE_CHECKING:
    import builtins
    from datetime import datetime

    from oeapp.models.sentence import Sentence
    from oeapp.services.db import Database


@dataclass
class Token:
    """Represents a tokenized word in a sentence."""

    #: The Old English characters. These are the characters that are allowed in
    #: the surface form of a token beyond the basic Latin characters.
    OE_CHARS: ClassVar[str] = "þÞðÐæǣÆǢȝġĠċĊāĀȳȲēĒīĪūŪōŌū"
    #: The value of the order index that indicates a token is no longer in the
    #: sentence.
    NO_ORDER_INDEX: ClassVar[int] = -1

    #: The Database object for the token.
    db: Database
    #: The token ID.
    id: int | None
    #: The sentence ID.
    sentence_id: int
    #: The order index of the token in the sentence.
    order_index: int
    #: The surface form of the token.
    surface: str
    #: The lemma of the token.
    lemma: str | None = None
    #: The date and time the token was created.
    created_at: datetime | None = None
    #: The date and time the token was last updated.
    updated_at: datetime | None = None

    @property
    def annotation(self) -> Annotation:
        """
        Get the sentence this token belongs to.
        """
        if not self.id:
            msg = "Token has not yet been saved to the database"
            raise ValueError(msg)
        return Annotation.get(self.db, self.id)

    @property
    def sentence(self) -> Sentence:
        """
        Get the sentence this token belongs to.
        """
        # Put this here to avoid circular imports
        from .sentence import Sentence  # noqa: PLC0415

        return Sentence.get(self.db, self.sentence_id)

    def save(self) -> None:
        """
        Save this token to the database.
        """
        cursor = self.db.cursor
        if not self.id:
            cursor.execute(
                "INSERT INTO tokens (sentence_id, order_index, surface, lemma) VALUES (?, ?, ?, ?)",  # noqa: E501
                (self.sentence_id, self.order_index, self.surface, self.lemma),
            )
            self.id = cursor.lastrowid
        else:
            cursor.execute(
                "UPDATE tokens SET surface = ?, lemma = ?, updated_at = CURRENT_TIMESTAMP, order_index = ? WHERE id = ?",  # noqa: E501
                (self.surface, self.lemma, self.order_index, self.id),
            )
        self.db.commit()
        try:
            annotation = self.annotation
        except DoesNotExist:
            annotation = Annotation.create(self.db, cast("int", self.id))
            annotation.save()

    def delete(self) -> None:
        """
        Delete this token.
        """
        # First delete the annotation for the token
        self.annotation.delete()
        # Then delete the token
        cursor = self.db.cursor
        cursor.execute("DELETE FROM tokens WHERE id = ?", (cast("int", self.id),))
        self.db.commit()

    @classmethod
    def list(cls, db: Database, sentence_id: int) -> builtins.list[Token]:
        """
        List all tokens for a sentence.

        Args:
            db: Database object
            sentence_id: Sentence ID

        Returns:
            List of :class:`~oeapp.models.token.Token` objects

        """
        cursor = db.cursor
        cursor.execute(
            "SELECT * FROM tokens WHERE sentence_id = ? ORDER BY order_index",
            (sentence_id,),
        )
        return [
            cls(
                db=db,
                id=row[0],
                sentence_id=row[1],
                order_index=row[2],
                surface=row[3],
                lemma=row[4],
                created_at=row[5],
                updated_at=row[6],
            )
            for row in cursor.fetchall()
        ]

    @classmethod
    def get_by_surface(cls, db: Database, surface: str) -> Token:
        """
        Get a token by surface.
        """
        cursor = db.cursor
        cursor.execute("SELECT * FROM tokens WHERE surface = ?", (surface,))
        row = cursor.fetchone()
        if not row:
            raise DoesNotExist("Token", f"surface: {surface}")  # noqa: EM101
        return cls(
            db=db,
            id=row[0],
            sentence_id=row[1],
            order_index=row[2],
            surface=row[3],
            lemma=row[4],
            created_at=row[5],
            updated_at=row[6],
        )

    @classmethod
    def get(cls, db: Database, token_id: int) -> Token:
        """
        Get a token by ID.

        Args:
            db: Database object
            token_id: Token ID

        Raises:
            DoesNotExist: If the token does not exist

        Returns:
            :class:`~oeapp.models.token.Token` object

        """
        cursor = db.cursor
        cursor.execute("SELECT * FROM tokens WHERE id = ?", (token_id,))
        row = cursor.fetchone()
        if not row:
            raise DoesNotExist("Token", f"id: {token_id}")  # noqa: EM101
        return cls(
            db=db,
            id=row[0],
            sentence_id=row[1],
            order_index=row[2],
            surface=row[3],
            lemma=row[4],
            created_at=row[5],
            updated_at=row[6],
        )

    @classmethod
    def create_from_sentence(
        cls, db: Database, sentence_id: int, sentence_text: str
    ) -> builtins.list[Token]:
        """
        Create new tokens for a sentence.

        There's no need to deal with individual tokens, as they are explicitly
        bound to the sentence, thus instead of :meth:`import` taking a token id
        or surface, it takes the sentence text and sentence id.

        Args:
            db: Database object
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
                db=db,
                id=None,
                sentence_id=sentence_id,
                order_index=token_index,
                surface=token_surface,
            )
            token.save()
            tokens.append(token)
        return tokens

    @classmethod
    def tokenize(cls, sentence_text: str) -> builtins.list[str]:
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
            # Split punctuation from words
            # Match word characters (including Old English chars) and punctuation
            # separately
            parts = re.findall(rf"[\w{re.escape(cls.OE_CHARS)}]+|[.,;:!?\-—]+", word)
            parts = [
                part
                for part in parts
                if part not in [",", ";", ":", "!", "?", "-", "—"]
            ]
            tokens.extend(parts)
        return tokens

    @classmethod
    def _find_matched_token_ids(
        cls,
        existing_tokens: builtins.list[Token],
        token_strings: builtins.list[str],
    ) -> tuple[set[int], dict[int, Token]]:
        """
        When updating a sentence, find matched tokens in the existing tokens and
        the new token strings.  This is called by :meth:`update_from_sentence`.

        Args:
            existing_tokens: List of existing tokens
            token_strings: List of new token strings

        Returns:
            Dictionary of matched tokens
            The key is the position of the token in the new token strings,
            the value is the matched token.

        """
        # Build a mapping of position -> existing token for quick lookup
        position_to_token = {token.order_index: token for token in existing_tokens}
        # Track which existing tokens have been matched (by their id)
        matched_token_ids = set()

        matched_positions = {}
        for new_index, new_surface in enumerate(token_strings):
            if new_index in position_to_token:
                existing_token = position_to_token[new_index]
                if (
                    existing_token.surface == new_surface
                    and existing_token.id is not None
                ):
                    # Perfect match at same position - no changes needed
                    matched_positions[new_index] = existing_token
                    matched_token_ids.add(existing_token.id)

        return matched_token_ids, matched_positions

    @classmethod
    def _process_unmatched_tokens(  # noqa: PLR0913
        cls,
        db: Database,
        existing_tokens: builtins.list[Token],
        matched_token_ids: set[int],
        matched_positions: dict[int, Token],
        token_strings: builtins.list[str],
        sentence_id: int,
    ) -> None:
        """
        Process unmatched tokens when updating a sentence.  Save the new tokens
        and update the existing tokens.  This is called by
        :meth:`update_from_sentence`.

        Args:
            db: Database object
            existing_tokens: List of existing tokens
            matched_token_ids: Set of matched token IDs
            matched_positions: Dictionary of matched positions
            token_strings: List of new token strings
            sentence_id: Sentence ID

        """
        unmatched_existing = [
            token
            for token in existing_tokens
            if token.id is not None and token.id not in matched_token_ids
        ]

        # First, move all unmatched existing tokens to temporary positions to avoid
        # conflicts when renumbering. Use negative offsets to avoid conflicts.
        temp_offset = -(len(existing_tokens) + len(token_strings))
        for token in unmatched_existing:
            if token.id is not None:
                token.order_index = temp_offset
                token.save()
                temp_offset += 1

        # Iterate over the new token strings and try to match them to existing
        # tokens
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
                        # Update order_index and surface (in case surface changed)
                        # Safe to update now since we moved all tokens to temp positions
                        existing_token.order_index = new_index
                        existing_token.surface = new_surface
                        existing_token.save()
                        matched = True
                        break

                if not matched:
                    # No match found - create a new token
                    new_token = cls(
                        db=db,
                        id=None,
                        sentence_id=sentence_id,
                        order_index=new_index,
                        surface=new_surface,
                    )
                    new_token.save()
                    matched_positions[new_index] = new_token

    @classmethod
    def update_from_sentence(
        cls, db: Database, sentence_text: str, sentence_id: int
    ) -> None:
        """
        Update all the tokens in the sentence, removing any tokens that are no
        longer in the sentence, and adding any new tokens.

        We will also re-order the tokens to match the order of the tokens in the
        sentence.

        There's no need to deal with individual tokens, as they are explicitly
        bound to the sentence, thus instead of :meth:`update` taking a token id
        or surface, it takes the sentence text and sentence id.

        Our here is to update the text of the sentence without losing any
        annotations on the tokens that need to remain.

        The algorithm handles duplicate tokens (e.g., multiple instances of "þā"
        or "him") by matching them positionally and by surface, ensuring each
        existing token is matched at most once.

        Args:
            db: Database object
            sentence_text: Text of the sentence to tokenize
            sentence_id: Sentence ID

        """
        token_strings = cls.tokenize(sentence_text)
        existing_tokens = cls.list(db, sentence_id)

        # First pass: Try to match tokens at the same position with same surface
        # This preserves tokens that haven't moved
        matched_token_ids, matched_positions = cls._find_matched_token_ids(
            existing_tokens, token_strings
        )
        # Second pass: For unmatched positions, try to find an unmatched
        # existing token with matching surface. This handles cases where tokens
        # have been reordered or where duplicates exist.
        cls._process_unmatched_tokens(
            db,
            existing_tokens,
            matched_token_ids,
            matched_positions,
            token_strings,
            sentence_id,
        )

        # Third pass: Delete tokens that weren't matched (they no longer exist
        # in the sentence)
        for token in existing_tokens:
            if token.id and token.id not in matched_token_ids:
                token.delete()

        # Fourth pass: Ensure all matched tokens have the correct order_index
        # (This handles any edge cases where order_index might be inconsistent)
        for new_index in range(len(token_strings)):
            if new_index in matched_positions:
                token = matched_positions[new_index]
                if token.order_index != new_index:
                    token.order_index = new_index
                    token.save()

        # Final pass: Ensure every position has a token and all tokens are
        # numbered sequentially. This catches any inconsistencies and ensures
        # proper sequential numbering.
        if len(matched_positions) != len(token_strings):
            # This should not happen, but if it does, we need to handle it
            msg = (
                f"Position count mismatch: expected {len(token_strings)} "
                f"positions, found {len(matched_positions)} in matched_positions"
            )
            raise ValueError(msg)
        # Ensure all tokens are numbered sequentially (0, 1, 2, ...)
        # This handles any edge cases where order_index might be inconsistent
        for new_index in range(len(token_strings)):
            if new_index not in matched_positions:
                msg = f"Missing token at position {new_index}"
                raise ValueError(msg)
            token = matched_positions[new_index]
            # Reload token from DB to get latest state (in case it was updated
            # elsewhere)
            if token.id is not None:
                token = cls.get(db, token.id)
            if token.order_index != new_index:
                token.order_index = new_index
                token.save()
