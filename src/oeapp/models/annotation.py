"""Annotation model."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class Annotation:
    """Represents grammatical/morphological annotations for a token."""

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
