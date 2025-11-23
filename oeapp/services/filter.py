"""Filter service for querying annotations based on criteria."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_

from oeapp.models.annotation import Annotation
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class FilterCriteria:
    """Filter criteria for annotations."""

    #: Filter by POS type
    pos: str | None = None
    #: Show only incomplete annotations
    incomplete: bool = False
    #: Specific field that must be missing
    missing_field: str | None = None
    #: Filter by uncertainty (True/False/None for all)
    uncertain: bool | None = None
    #: Minimum confidence level
    min_confidence: int | None = None
    #: Maximum confidence level
    max_confidence: int | None = None
    #: Has alternatives or not
    has_alternatives: bool | None = None


class FilterService:
    """Service for filtering annotations."""

    def __init__(self, session: Session):
        """
        Initialize filter service.

        Args:
            session: SQLAlchemy session

        """
        self.session = session

    def find_tokens(  # noqa: PLR0912
        self,
        project_id: int,
        criteria: FilterCriteria,
    ) -> list[dict]:
        """
        Find tokens matching filter criteria.

        Args:
            project_id: Project ID to filter within
            criteria: Filter criteria

        Returns:
            List of token dictionaries with sentence context

        """
        # Base query with joins
        query = (
            self.session.query(
                Token.id.label("token_id"),
                Token.sentence_id,
                Token.order_index,
                Token.surface,
                Token.lemma,
                Sentence.display_order.label("sentence_order"),
                Sentence.text_oe.label("sentence_text"),
                Annotation.pos,
                Annotation.gender,
                Annotation.number,
                Annotation.case,
                Annotation.declension,
                Annotation.pronoun_type,
                Annotation.verb_class,
                Annotation.verb_tense,
                Annotation.verb_person,
                Annotation.verb_mood,
                Annotation.verb_aspect,
                Annotation.verb_form,
                Annotation.prep_case,
                Annotation.uncertain,
                Annotation.alternatives_json,
                Annotation.confidence,
            )
            .join(Sentence, Token.sentence_id == Sentence.id)
            .outerjoin(Annotation, Token.id == Annotation.token_id)
            .filter(Sentence.project_id == project_id)
        )

        # Filter by POS
        if criteria.pos:
            if criteria.pos == "ANY":
                query = query.filter(Annotation.pos.isnot(None))
            else:
                query = query.filter(Annotation.pos == criteria.pos)

        # Filter by uncertainty
        if criteria.uncertain is not None:
            if criteria.uncertain:
                query = query.filter(Annotation.uncertain == True)  # noqa: E712
            else:
                query = query.filter(
                    or_(Annotation.uncertain == False, Annotation.uncertain.is_(None))  # noqa: E712
                )

        # Filter by confidence range
        if criteria.min_confidence is not None:
            query = query.filter(
                or_(
                    Annotation.confidence >= criteria.min_confidence,
                    Annotation.confidence.is_(None),
                )
            )
        if criteria.max_confidence is not None:
            query = query.filter(
                or_(
                    Annotation.confidence <= criteria.max_confidence,
                    Annotation.confidence.is_(None),
                )
            )

        # Filter by alternatives
        if criteria.has_alternatives is not None:
            if criteria.has_alternatives:
                query = query.filter(
                    and_(
                        Annotation.alternatives_json.isnot(None),
                        Annotation.alternatives_json != "",
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Annotation.alternatives_json.is_(None),
                        Annotation.alternatives_json == "",
                    )
                )

        # Filter incomplete annotations
        if criteria.incomplete:
            incomplete_conditions = []
            if criteria.pos == "N" or criteria.pos is None:
                incomplete_conditions.append(
                    and_(
                        Annotation.pos == "N",
                        or_(
                            Annotation.gender.is_(None),
                            Annotation.number.is_(None),
                            Annotation.case.is_(None),
                        ),
                    )
                )
            if criteria.pos == "V" or criteria.pos is None:
                incomplete_conditions.append(
                    and_(
                        Annotation.pos == "V",
                        or_(
                            Annotation.verb_tense.is_(None),
                            Annotation.verb_mood.is_(None),
                            Annotation.verb_person.is_(None),
                            Annotation.number.is_(None),
                        ),
                    )
                )
            if criteria.pos == "A" or criteria.pos is None:
                incomplete_conditions.append(
                    and_(
                        Annotation.pos == "A",
                        or_(
                            Annotation.gender.is_(None),
                            Annotation.number.is_(None),
                            Annotation.case.is_(None),
                        ),
                    )
                )
            if criteria.pos == "R" or criteria.pos is None:
                incomplete_conditions.append(
                    and_(
                        Annotation.pos == "R",
                        or_(
                            Annotation.pronoun_type.is_(None),
                            Annotation.gender.is_(None),
                            Annotation.number.is_(None),
                            Annotation.case.is_(None),
                        ),
                    )
                )
            if criteria.pos == "E" or criteria.pos is None:
                incomplete_conditions.append(
                    and_(Annotation.pos == "E", Annotation.prep_case.is_(None))
                )
            if incomplete_conditions:
                query = query.filter(or_(*incomplete_conditions))

        # Filter by specific missing field
        if criteria.missing_field:
            field = getattr(Annotation, criteria.missing_field, None)
            if field is not None:
                query = query.filter(field.is_(None))
                query = query.filter(Annotation.pos.isnot(None))  # Must have annotation

                # Only filter tokens where this field is relevant for the POS type
                field_pos_map = {
                    "verb_tense": "V",
                    "verb_mood": "V",
                    "verb_person": "V",
                    "verb_class": "V",
                    "verb_aspect": "V",
                    "verb_form": "V",
                    "prep_case": "E",
                    "pronoun_type": "R",
                    "declension": ["N", "A"],
                }

                if criteria.missing_field in field_pos_map:
                    required_pos = field_pos_map[criteria.missing_field]
                    if isinstance(required_pos, list):
                        query = query.filter(Annotation.pos.in_(required_pos))
                    else:
                        query = query.filter(Annotation.pos == required_pos)

        # Order results
        query = query.order_by(Sentence.display_order, Token.order_index)

        # Execute query and convert to dictionaries
        results = []
        for row in query.all():
            results.append(  # noqa: PERF401
                {
                    "token_id": row.token_id,
                    "sentence_id": row.sentence_id,
                    "order_index": row.order_index,
                    "surface": row.surface,
                    "lemma": row.lemma,
                    "sentence_order": row.sentence_order,
                    "sentence_text": row.sentence_text,
                    "pos": row.pos,
                    "gender": row.gender,
                    "number": row.number,
                    "case": row.case,
                    "declension": row.declension,
                    "pronoun_type": row.pronoun_type,
                    "verb_class": row.verb_class,
                    "verb_tense": row.verb_tense,
                    "verb_person": row.verb_person,
                    "verb_mood": row.verb_mood,
                    "verb_aspect": row.verb_aspect,
                    "verb_form": row.verb_form,
                    "prep_case": row.prep_case,
                    "uncertain": bool(row.uncertain) if row.uncertain else False,
                    "alternatives_json": row.alternatives_json,
                    "confidence": row.confidence,
                }
            )

        return results

    def get_statistics(self, project_id: int) -> dict:
        """
        Get annotation statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with statistics

        """
        # Total tokens
        project = Project.get(self.session, project_id)
        if project is None:
            msg = f"Project with ID {project_id} not found"
            raise ValueError(msg)
        total_tokens = project.total_token_count(self.session)

        # Annotated tokens
        annotated_tokens = (
            self.session.query(func.count(Token.id))
            .join(Sentence, Token.sentence_id == Sentence.id)
            .join(Annotation, Token.id == Annotation.token_id)
            .filter(Sentence.project_id == project_id)
            .scalar()
        )

        # POS distribution
        pos_rows = (
            self.session.query(Annotation.pos, func.count(Annotation.token_id))
            .join(Token, Annotation.token_id == Token.id)
            .join(Sentence, Token.sentence_id == Sentence.id)
            .filter(Sentence.project_id == project_id)
            .group_by(Annotation.pos)
            .all()
        )
        pos_distribution = {row[0]: row[1] for row in pos_rows}

        # Uncertain annotations
        uncertain_count = (
            self.session.query(func.count(Annotation.token_id))
            .join(Token, Annotation.token_id == Token.id)
            .join(Sentence, Token.sentence_id == Sentence.id)
            .filter(Sentence.project_id == project_id)
            .filter(Annotation.uncertain == True)  # noqa: E712
            .scalar()
        )

        # Incomplete annotations
        incomplete_conditions = or_(
            and_(
                Annotation.pos == "N",
                or_(
                    Annotation.gender.is_(None),
                    Annotation.number.is_(None),
                    Annotation.case.is_(None),
                ),
            ),
            and_(
                Annotation.pos == "V",
                or_(
                    Annotation.verb_tense.is_(None),
                    Annotation.verb_mood.is_(None),
                    Annotation.verb_person.is_(None),
                    Annotation.number.is_(None),
                ),
            ),
            and_(
                Annotation.pos == "A",
                or_(
                    Annotation.gender.is_(None),
                    Annotation.number.is_(None),
                    Annotation.case.is_(None),
                ),
            ),
            and_(
                Annotation.pos == "R",
                or_(
                    Annotation.pronoun_type.is_(None),
                    Annotation.gender.is_(None),
                    Annotation.number.is_(None),
                    Annotation.case.is_(None),
                ),
            ),
            and_(Annotation.pos == "E", Annotation.prep_case.is_(None)),
        )

        incomplete_count = (
            self.session.query(func.count(Annotation.token_id))
            .join(Token, Annotation.token_id == Token.id)
            .join(Sentence, Token.sentence_id == Sentence.id)
            .filter(Sentence.project_id == project_id)
            .filter(incomplete_conditions)
            .scalar()
        )

        return {
            "total_tokens": total_tokens or 0,
            "annotated_tokens": annotated_tokens or 0,
            "unannotated_tokens": (total_tokens or 0) - (annotated_tokens or 0),
            "pos_distribution": pos_distribution,
            "uncertain_count": uncertain_count or 0,
            "incomplete_count": incomplete_count or 0,
        }
