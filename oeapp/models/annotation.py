"""Annotation model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from oeapp.db import Base
from oeapp.mixins import AnnotationTextualMixin
from oeapp.utils import from_utc_iso, to_utc_iso

if TYPE_CHECKING:
    from oeapp.models.token import Token


class Annotation(AnnotationTextualMixin, Base):
    """Represents grammatical/morphological annotations for a token."""

    __tablename__ = "annotations"
    __table_args__ = (
        CheckConstraint(
            "pos IN ('N','V','A','R','D','B','C','E','I')", name="ck_annotations_pos"
        ),
        CheckConstraint("gender IN ('m','f','n')", name="ck_annotations_gender"),
        CheckConstraint("number IN ('s','p')", name="ck_annotations_number"),
        CheckConstraint(
            "\"case\" IN ('n','a','g','d','i')", name="ck_annotations_case"
        ),
        CheckConstraint(
            "pronoun_type IN ('p','r','d','i')", name="ck_annotations_pronoun_type"
        ),
        CheckConstraint(
            "pronoun_number IN ('s','d','pl')", name="ck_annotations_pronoun_number"
        ),
        CheckConstraint(
            "article_type IN ('d','i','p','D')", name="ck_annotations_article_type"
        ),
        CheckConstraint(
            "verb_class IN ('a','w1','w2','w3','s1','s2','s3','s4','s5','s6','s7')",
            name="ck_annotations_verb_class",
        ),
        CheckConstraint("verb_tense IN ('p','n')", name="ck_annotations_verb_tense"),
        CheckConstraint(
            "verb_person IN ('1','2','3')", name="ck_annotations_verb_person"
        ),
        CheckConstraint(
            "verb_mood IN ('i','s','imp')", name="ck_annotations_verb_mood"
        ),
        CheckConstraint(
            "verb_aspect IN ('p','f','prg','gn')", name="ck_annotations_verb_aspect"
        ),
        CheckConstraint(
            "verb_form IN ('f','i','p', 'inf')", name="ck_annotations_verb_form"
        ),
        CheckConstraint("prep_case IN ('a','d','g')", name="ck_annotations_prep_case"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 100", name="ck_annotations_confidence"
        ),
        CheckConstraint(
            "adjective_inflection IN ('s','w')",
            name="ck_annotations_adjective_inflection",
        ),
        CheckConstraint(
            "adjective_degree IN ('p','c','s')", name="ck_annotations_adjective_degree"
        ),
        CheckConstraint(
            "conjunction_type IN ('c','s')", name="ck_annotations_conjunction_type"
        ),
        CheckConstraint(
            "adverb_degree IN ('p','c','s')", name="ck_annotations_adverb_degree"
        ),
    )

    #: The token ID (primary key and foreign key).
    token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), primary_key=True
    )
    #: The Part of Speech.
    pos: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # N, V, A, R, D, B, C, E, I
    #: The gender.
    gender: Mapped[str | None] = mapped_column(String, nullable=True)  # m, f, n
    #: The number.
    number: Mapped[str | None] = mapped_column(String, nullable=True)  # s, p
    #: The case (using db_column_name to handle reserved keyword).
    case: Mapped[str | None] = mapped_column(
        String, nullable=True, name="case"
    )  # n, a, g, d, i
    #: The declension.
    declension: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The article type.
    article_type: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # d, i, p, D
    #: The pronoun type.
    pronoun_type: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # p, r, d, i
    #: The pronoun number.
    pronoun_number: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # 1, 2, pl
    #: The verb class.
    verb_class: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The verb tense.
    verb_tense: Mapped[str | None] = mapped_column(String, nullable=True)  # p, n
    #: The verb person.
    verb_person: Mapped[str | None] = mapped_column(String, nullable=True)  # 1, 2,
    #: The verb mood.
    verb_mood: Mapped[str | None] = mapped_column(String, nullable=True)  # i, s, imp
    #: The verb aspect.
    verb_aspect: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # p, f, prg, gn
    #: The verb form.
    verb_form: Mapped[str | None] = mapped_column(String, nullable=True)  # f, i, p
    #: The preposition case.
    prep_case: Mapped[str | None] = mapped_column(String, nullable=True)  # a, d, g
    #: The adjective inflection.
    adjective_inflection: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # s, w
    #: The adjective degree.
    adjective_degree: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # p, c, s
    #: The conjuncion type.
    conjunction_type: Mapped[str | None] = mapped_column(String, nullable=True)  # c, s
    #: The adverb degree.
    adverb_degree: Mapped[str | None] = mapped_column(String, nullable=True)  # p, c, s
    #: Whether the annotation is uncertain.
    uncertain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: The alternatives in JSON format.
    alternatives_json: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The confidence in the annotation.
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100
    #: The last inferred JSON.
    last_inferred_json: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The modern English meaning.
    modern_english_meaning: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The root.
    root: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The date and time the annotation was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    token: Mapped[Token] = relationship("Token", back_populates="annotation")

    @classmethod
    def exists(cls, session: Session, token_id: int) -> bool:
        """
        Check if an annotation exists for a token.
        """
        return session.scalar(select(cls).where(cls.token_id == token_id)) is not None

    @classmethod
    def get(cls, session: Session, annotation_id: int) -> Annotation | None:
        """
        Get an annotation by ID.
        """
        return session.get(cls, annotation_id)

    def to_json(self) -> dict:
        """
        Serialize annotation to JSON-compatible dictionary.

        Returns:
            Dictionary containing annotation data

        """
        return {
            "pos": self.pos,
            "gender": self.gender,
            "number": self.number,
            "case": self.case,
            "declension": self.declension,
            "article_type": self.article_type,
            "pronoun_type": self.pronoun_type,
            "pronoun_number": self.pronoun_number,
            "verb_class": self.verb_class,
            "verb_tense": self.verb_tense,
            "verb_person": self.verb_person,
            "verb_mood": self.verb_mood,
            "verb_aspect": self.verb_aspect,
            "verb_form": self.verb_form,
            "prep_case": self.prep_case,
            "adjective_inflection": self.adjective_inflection,
            "adjective_degree": self.adjective_degree,
            "conjunction_type": self.conjunction_type,
            "adverb_degree": self.adverb_degree,
            "uncertain": self.uncertain,
            "alternatives_json": self.alternatives_json,
            "confidence": self.confidence,
            "last_inferred_json": self.last_inferred_json,
            "modern_english_meaning": self.modern_english_meaning,
            "root": self.root,
            "updated_at": to_utc_iso(self.updated_at),
        }

    @classmethod
    def from_json(cls, session: Session, token_id: int, ann_data: dict) -> Annotation:
        """
        Create an annotation from JSON import data.

        Args:
            session: SQLAlchemy session
            token_id: Token ID to attach annotation to
            ann_data: Annotation data dictionary from JSON

        Returns:
            Created Annotation entity

        """
        annotation = cls(
            token_id=token_id,
            pos=ann_data.get("pos"),
            gender=ann_data.get("gender"),
            number=ann_data.get("number"),
            case=ann_data.get("case"),
            declension=ann_data.get("declension"),
            article_type=ann_data.get("article_type"),
            pronoun_type=ann_data.get("pronoun_type"),
            pronoun_number=ann_data.get("pronoun_number"),
            verb_class=ann_data.get("verb_class"),
            verb_tense=ann_data.get("verb_tense"),
            verb_person=ann_data.get("verb_person"),
            verb_mood=ann_data.get("verb_mood"),
            verb_aspect=ann_data.get("verb_aspect"),
            verb_form=ann_data.get("verb_form"),
            prep_case=ann_data.get("prep_case"),
            adjective_inflection=ann_data.get("adjective_inflection"),
            adjective_degree=ann_data.get("adjective_degree"),
            conjunction_type=ann_data.get("conjunction_type"),
            adverb_degree=ann_data.get("adverb_degree"),
            uncertain=ann_data.get("uncertain", False),
            alternatives_json=ann_data.get("alternatives_json"),
            confidence=ann_data.get("confidence"),
            last_inferred_json=ann_data.get("last_inferred_json"),
            modern_english_meaning=ann_data.get("modern_english_meaning"),
            root=ann_data.get("root"),
        )
        updated_at = from_utc_iso(ann_data.get("updated_at"))
        if updated_at:
            annotation.updated_at = updated_at

        session.add(annotation)
        return annotation
