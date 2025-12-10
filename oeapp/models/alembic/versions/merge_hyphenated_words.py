"""
Merge hyphenated words

Revision ID: merge_hyphenated_words
Revises: fix_check_constraints
Create Date: 2025-01-27 12:00:00.000000

"""

import logging
import re
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "merge_hyphenated_words"
down_revision: str | Sequence[str] | None = "0d9ebcdd2591"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger(__name__)

# Old English characters for matching hyphenated words
OE_CHARS = "þÞðÐæǣÆǢȝġĠċĊāĀȳȲēĒīĪūŪōŌū"


def _find_hyphenated_words(text: str) -> list[tuple[str, int, int]]:
    """
    Find all hyphenated words in text with their positions.

    Args:
        text: The sentence text to search

    Returns:
        List of tuples: (hyphenated_word, start_pos, end_pos)

    """
    # Build character class for word characters including Old English chars
    oe_chars_escaped = re.escape(OE_CHARS)
    word_char_class = rf"[\w{oe_chars_escaped}]"

    # Pattern to match hyphenated words: word_chars + hyphen/en-dash/em-dash +
    # word_chars
    pattern = rf"{word_char_class}+[-–—]{word_char_class}+"  # noqa: RUF001

    matches = []
    for match in re.finditer(pattern, text):
        matches.append((match.group(), match.start(), match.end()))  # noqa: PERF401

    return matches


def _map_tokens_to_positions(
    text: str, tokens: list[dict]
) -> list[tuple[int | None, int | None]]:
    """
    Map tokens to their character positions in the text.

    Uses order_index to determine which occurrence each token represents,
    similar to :meth:`oeapp.mixins.TokenOccurrenceMixin._find_token_occurrence`.

    Args:
        text: The sentence text
        tokens: List of token dicts with 'surface' and 'order_index' keys

    Returns:
        List of (start_pos, end_pos) tuples for each token, in order_index order

    """
    # Sort tokens by order_index
    sorted_tokens = sorted(tokens, key=lambda t: t["order_index"])

    positions: list[tuple[int | None, int | None]] = []

    for token in sorted_tokens:
        surface = token["surface"]

        # Find all occurrences of this surface text
        occurrences = []
        start = 0
        while True:
            pos = text.find(surface, start)
            if pos == -1:
                break
            occurrences.append(pos)
            start = pos + 1

        if not occurrences:
            # Token not found
            positions.append((None, None))
            continue

        # Use order_index to determine which occurrence this token represents
        # Count how many tokens with the same surface appear before this one
        same_surface_count = 0
        for t in sorted_tokens:
            if t["order_index"] >= token["order_index"]:
                break
            if t["surface"] == surface:
                same_surface_count += 1

        # Select the occurrence at the same_surface_count index
        if same_surface_count < len(occurrences):
            pos = occurrences[same_surface_count]
        else:
            # Fallback to first occurrence
            pos = occurrences[0]

        end_pos = pos + len(surface)
        positions.append((pos, end_pos))

    return positions


def _merge_tokens_for_hyphenated_word(  # noqa: PLR0913
    conn,
    hyphenated_word: str,
    word_start: int,
    word_end: int,
    tokens: list[dict],
    token_positions: list[tuple[int | None, int | None]],
    matched_token_ids: set[int],
) -> bool:
    """
    Merge tokens to form a hyphenated word.

    Args:
        conn: Database connection
        hyphenated_word: The hyphenated word text (e.g., "ġe-wāt")
        word_start: Start position of hyphenated word in text
        word_end: End position of hyphenated word in text
        tokens: List of all tokens for the sentence
        token_positions: List of (start, end) positions for each token
        matched_token_ids: Set of token IDs that have already been matched

    Returns:
        True if merge was successful, False otherwise

    """
    # Find consecutive tokens that match this hyphenated word
    # Sort tokens by order_index
    sorted_tokens = sorted(tokens, key=lambda t: t["order_index"])

    # Find tokens whose positions overlap with or are contained within the
    # hyphenated word
    matching_tokens = []
    for i, token in enumerate(sorted_tokens):
        if token["id"] in matched_token_ids:
            continue

        pos_start, pos_end = token_positions[i]
        if pos_start is None or pos_end is None:
            continue

        # Check if token position overlaps with hyphenated word position
        if pos_start < word_end and pos_end > word_start:
            matching_tokens.append((i, token))

    if len(matching_tokens) < 2:  # noqa: PLR2004
        # Need at least 2 tokens to merge
        return False

    # Verify consecutive tokens
    matching_indices = [idx for idx, _ in matching_tokens]
    matching_indices.sort()

    # Check if tokens are consecutive
    for i in range(len(matching_indices) - 1):
        if matching_indices[i + 1] - matching_indices[i] != 1:
            # Not consecutive, try to find a better match
            # For now, just use the first two overlapping tokens
            matching_tokens = matching_tokens[:2]
            break

    if len(matching_tokens) < 2:  # noqa: PLR2004
        return False

    # Get the tokens to merge
    token_indices = [idx for idx, _ in matching_tokens]
    token_indices.sort()
    tokens_to_merge = [sorted_tokens[idx] for idx in token_indices]

    # Verify combined surfaces match hyphenated word (accounting for hyphens)
    # Remove hyphens/dashes from hyphenated word for comparison
    hyphenated_word_no_dash = (
        hyphenated_word.replace("-", "").replace("–", "").replace("—", "")  # noqa: RUF001
    )
    combined_surfaces = "".join(t["surface"] for t in tokens_to_merge)

    # Check if combined surfaces match (without hyphens)
    if combined_surfaces != hyphenated_word_no_dash:
        # Try with hyphen inserted between tokens
        combined_with_hyphen = (
            tokens_to_merge[0]["surface"] + "-" + tokens_to_merge[1]["surface"]
        )
        combined_with_endash = (
            tokens_to_merge[0]["surface"] + "–" + tokens_to_merge[1]["surface"]  # noqa: RUF001
        )
        combined_with_emdash = (
            tokens_to_merge[0]["surface"] + "—" + tokens_to_merge[1]["surface"]
        )

        if hyphenated_word not in (
            combined_with_hyphen,
            combined_with_endash,
            combined_with_emdash,
        ):
            # Doesn't match, skip
            return False

    # Merge: update the last token's surface to the hyphenated word
    # Delete the earlier tokens
    main_token = tokens_to_merge[-1]
    prefix_tokens = tokens_to_merge[:-1]

    # Update main token surface
    conn.execute(
        sa.text("UPDATE tokens SET surface = :surface WHERE id = :token_id"),
        {"surface": hyphenated_word, "token_id": main_token["id"]},
    )

    # Delete prefix tokens (cascade will handle annotations)
    for prefix_token in prefix_tokens:
        conn.execute(
            sa.text("DELETE FROM tokens WHERE id = :token_id"),
            {"token_id": prefix_token["id"]},
        )
        matched_token_ids.add(prefix_token["id"])

    matched_token_ids.add(main_token["id"])

    return True


def upgrade() -> None:
    """
    Upgrade: Merge hyphenated words that were split into separate tokens.
    """
    conn = op.get_bind()

    # Get all sentences
    sentences_result = conn.execute(
        sa.text("SELECT id, text_oe FROM sentences ORDER BY id")
    )
    sentences = sentences_result.fetchall()

    total_sentences = len(sentences)
    processed = 0
    errors = 0

    logger.info(f"Processing {total_sentences} sentences for hyphenated word merging")

    for sentence_id, text_oe in sentences:
        try:
            # Find hyphenated words in the text
            hyphenated_words = _find_hyphenated_words(text_oe)

            if not hyphenated_words:
                # No hyphenated words, skip
                processed += 1
                continue

            # Get all tokens for this sentence
            tokens_result = conn.execute(
                sa.text("""
                    SELECT id, order_index, surface
                    FROM tokens
                    WHERE sentence_id = :sentence_id
                    ORDER BY order_index
                """),
                {"sentence_id": sentence_id},
            )
            tokens = [
                {"id": row[0], "order_index": row[1], "surface": row[2]}
                for row in tokens_result.fetchall()
            ]

            if not tokens:
                processed += 1
                continue

            # Map tokens to positions in text
            token_positions = _map_tokens_to_positions(text_oe, tokens)

            # Track matched tokens to avoid reusing them
            matched_token_ids: set[int] = set()

            # Process each hyphenated word occurrence (in order of appearance)
            for hyphenated_word, word_start, word_end in hyphenated_words:
                success = _merge_tokens_for_hyphenated_word(
                    conn,
                    hyphenated_word,
                    word_start,
                    word_end,
                    tokens,
                    token_positions,
                    matched_token_ids,
                )

                if not success:
                    logger.warning(
                        f"Failed to merge hyphenated word '{hyphenated_word}' "
                        f"in sentence {sentence_id}"
                    )

            # Reorder remaining tokens' order_index values to fill gaps
            # Get updated tokens
            tokens_result = conn.execute(
                sa.text("""
                    SELECT id FROM tokens
                    WHERE sentence_id = :sentence_id
                    ORDER BY order_index
                """),
                {"sentence_id": sentence_id},
            )
            remaining_tokens = [row[0] for row in tokens_result.fetchall()]

            # Update order_index to be sequential (0, 1, 2, ...)
            for new_index, token_id in enumerate(remaining_tokens):
                conn.execute(
                    sa.text(
                        "UPDATE tokens SET order_index = :order_index WHERE id = :token_id"  # noqa: E501
                    ),
                    {"order_index": new_index, "token_id": token_id},
                )

            processed += 1

            if processed % 100 == 0:
                logger.info(f"Processed {processed}/{total_sentences} sentences")

        except Exception as e:
            errors += 1
            logger.error(f"Error processing sentence {sentence_id}: {e}", exc_info=True)  # noqa: G201
            # Continue with next sentence
            continue

    logger.info(f"Migration complete: {processed} sentences processed, {errors} errors")


def downgrade() -> None:
    """
    Downgrade: Cannot automatically split hyphenated words back.

    This migration merges tokens, and there's no reliable way to automatically
    determine where to split them again. Manual intervention would be required.
    """
    # No automatic downgrade possible
    logger.warning(
        "Downgrade not supported: Cannot automatically split merged hyphenated words"
    )
