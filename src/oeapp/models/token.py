"""Token model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class Token:
    """Represents a tokenized word in a sentence."""

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
