"""Note model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class Note:
    """Represents a note attached to tokens, spans, or sentences."""

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
