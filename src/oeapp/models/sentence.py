"""Sentence model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class Sentence:
    """Represents a sentence."""

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
