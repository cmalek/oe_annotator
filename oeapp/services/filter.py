"""Filter service for querying annotations based on criteria."""

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oeapp.services.db import Database


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

    def __init__(self, db: Database):
        """
        Initialize filter service.

        Args:
            db: Database connection

        """
        self.db = db

    def find_tokens(  # noqa: PLR0912, PLR0915
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
        query_parts = []
        params = []

        # Base query joins tokens with annotations
        base_query = """
            SELECT
                t.id as token_id,
                t.sentence_id,
                t.order_index,
                t.surface,
                t.lemma,
                s.display_order as sentence_order,
                s.text_oe as sentence_text,
                a.pos,
                a.gender,
                a.number,
                a."case",
                a.declension,
                a.pronoun_type,
                a.verb_class,
                a.verb_tense,
                a.verb_person,
                a.verb_mood,
                a.verb_aspect,
                a.verb_form,
                a.prep_case,
                a.uncertain,
                a.alternatives_json,
                a.confidence
            FROM tokens t
            JOIN sentences s ON t.sentence_id = s.id
            LEFT JOIN annotations a ON t.id = a.token_id
            WHERE s.project_id = ?
        """
        params.append(project_id)

        # Filter by POS
        if criteria.pos:
            if criteria.pos == "ANY":
                query_parts.append("a.pos IS NOT NULL")
            else:
                query_parts.append("a.pos = ?")
                params.append(criteria.pos)

        # Filter by uncertainty
        if criteria.uncertain is not None:
            if criteria.uncertain:
                query_parts.append("a.uncertain = 1")
            else:
                query_parts.append("(a.uncertain = 0 OR a.uncertain IS NULL)")

        # Filter by confidence range
        if criteria.min_confidence is not None:
            query_parts.append("(a.confidence >= ? OR a.confidence IS NULL)")
            params.append(criteria.min_confidence)
        if criteria.max_confidence is not None:
            query_parts.append("(a.confidence <= ? OR a.confidence IS NULL)")
            params.append(criteria.max_confidence)

        # Filter by alternatives
        if criteria.has_alternatives is not None:
            if criteria.has_alternatives:
                query_parts.append(
                    "a.alternatives_json IS NOT NULL AND a.alternatives_json != ''"
                )
            else:
                query_parts.append(
                    "(a.alternatives_json IS NULL OR a.alternatives_json = '')"
                )

        # Filter incomplete annotations
        if criteria.incomplete:
            incomplete_conditions = []
            if criteria.pos == "N" or criteria.pos is None:
                # Nouns missing gender, number, or case
                incomplete_conditions.append(
                    "(a.pos = 'N' AND (a.gender IS NULL OR a.number IS NULL OR a.\"case\" IS NULL))"  # noqa: E501
                )
            if criteria.pos == "V" or criteria.pos is None:
                # Verbs missing tense, mood, person, or number
                incomplete_conditions.append(
                    "(a.pos = 'V' AND (a.verb_tense IS NULL OR a.verb_mood IS NULL OR a.verb_person IS NULL OR a.number IS NULL))"  # noqa: E501
                )
            if criteria.pos == "A" or criteria.pos is None:
                # Adjectives missing gender, number, case, or degree
                incomplete_conditions.append(
                    "(a.pos = 'A' AND (a.gender IS NULL OR a.number IS NULL OR a.\"case\" IS NULL))"  # noqa: E501
                )
            if criteria.pos == "R" or criteria.pos is None:
                # Pronouns missing type, gender, number, or case
                incomplete_conditions.append(
                    "(a.pos = 'R' AND (a.pronoun_type IS NULL OR a.gender IS NULL OR a.number IS NULL OR a.\"case\" IS NULL))"  # noqa: E501
                )
            if criteria.pos == "E" or criteria.pos is None:
                # Prepositions missing case
                incomplete_conditions.append("(a.pos = 'E' AND a.prep_case IS NULL)")
            if incomplete_conditions:
                query_parts.append(f"({' OR '.join(incomplete_conditions)})")
            else:
                # If specific POS but no incomplete conditions, return empty
                query_parts.append("1 = 0")

        # Filter by specific missing field
        if criteria.missing_field:
            query_parts.append(f"a.{criteria.missing_field} IS NULL")
            query_parts.append("a.pos IS NOT NULL")  # Must have annotation

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
                    pos_conditions = " OR ".join(
                        [f"a.pos = '{p}'" for p in required_pos]
                    )
                    query_parts.append(f"({pos_conditions})")
                else:
                    query_parts.append(f"a.pos = '{required_pos}'")

        # Combine query parts
        if query_parts:
            query = base_query + " AND " + " AND ".join(query_parts)
        else:
            query = base_query

        query += " ORDER BY s.display_order, t.order_index"

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

        # Convert rows to dictionaries
        results = []
        for row in rows:
            results.append(  # noqa: PERF401
                {
                    "token_id": row["token_id"],
                    "sentence_id": row["sentence_id"],
                    "order_index": row["order_index"],
                    "surface": row["surface"],
                    "lemma": row["lemma"],
                    "sentence_order": row["sentence_order"],
                    "sentence_text": row["sentence_text"],
                    "pos": row["pos"],
                    "gender": row["gender"],
                    "number": row["number"],
                    "case": row["case"],
                    "declension": row["declension"],
                    "pronoun_type": row["pronoun_type"],
                    "verb_class": row["verb_class"],
                    "verb_tense": row["verb_tense"],
                    "verb_person": row["verb_person"],
                    "verb_mood": row["verb_mood"],
                    "verb_aspect": row["verb_aspect"],
                    "verb_form": row["verb_form"],
                    "prep_case": row["prep_case"],
                    "uncertain": bool(row["uncertain"]) if row["uncertain"] else False,
                    "alternatives_json": row["alternatives_json"],
                    "confidence": row["confidence"],
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
        try:
            cursor = self.db.conn.cursor()

            # Total tokens
            cursor.execute(
                """
                SELECT COUNT(*) as total
                FROM tokens t
                JOIN sentences s ON t.sentence_id = s.id
                WHERE s.project_id = ?
            """,
                (project_id,),
            )
            total_tokens = cursor.fetchone()["total"]
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return {}

        try:
            # Annotated tokens
            cursor.execute(
                """
                SELECT COUNT(*) as total
                FROM tokens t
                JOIN sentences s ON t.sentence_id = s.id
                JOIN annotations a ON t.id = a.token_id
                WHERE s.project_id = ?
            """,
                (project_id,),
            )
            annotated_tokens = cursor.fetchone()["total"]
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return {}

        try:
            # POS distribution
            cursor.execute(
                """
                SELECT a.pos, COUNT(*) as count
                FROM annotations a
                JOIN tokens t ON a.token_id = t.id
                JOIN sentences s ON t.sentence_id = s.id
                WHERE s.project_id = ?
                GROUP BY a.pos
            """,
                (project_id,),
            )
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return {}

        pos_distribution = {row["pos"]: row["count"] for row in rows}

        try:
            # Uncertain annotations
            cursor.execute(
                """
                SELECT COUNT(*) as total
                FROM annotations a
                JOIN tokens t ON a.token_id = t.id
                JOIN sentences s ON t.sentence_id = s.id
                WHERE s.project_id = ? AND a.uncertain = 1
            """,
                (project_id,),
            )
            uncertain_count = cursor.fetchone()["total"]
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return {}

        # Incomplete annotations (simplified - any annotation missing key fields)
        incomplete_query = """
            SELECT COUNT(*) as total
            FROM annotations a
            JOIN tokens t ON a.token_id = t.id
            JOIN sentences s ON t.sentence_id = s.id
            WHERE s.project_id = ? AND (
                (a.pos = 'N' AND (a.gender IS NULL OR a.number IS NULL OR a."case" IS NULL)) OR
                (a.pos = 'V' AND (a.verb_tense IS NULL OR a.verb_mood IS NULL OR a.verb_person IS NULL OR a.number IS NULL)) OR
                (a.pos = 'A' AND (a.gender IS NULL OR a.number IS NULL OR a."case" IS NULL)) OR
                (a.pos = 'R' AND (a.pronoun_type IS NULL OR a.gender IS NULL OR a.number IS NULL OR a."case" IS NULL)) OR
                (a.pos = 'E' AND a.prep_case IS NULL)
            )
        """  # noqa: E501
        try:
            cursor.execute(incomplete_query, (project_id,))
            incomplete_count = cursor.fetchone()["total"]
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return {}

        return {
            "total_tokens": total_tokens,
            "annotated_tokens": annotated_tokens,
            "unannotated_tokens": total_tokens - annotated_tokens,
            "pos_distribution": pos_distribution,
            "uncertain_count": uncertain_count,
            "incomplete_count": incomplete_count,
        }
