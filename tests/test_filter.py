"""Unit tests for FilterService."""

import unittest
import tempfile
import os

from src.oeapp.services.db import Database
from src.oeapp.services.filter import FilterService, FilterCriteria


class TestFilterService(unittest.TestCase):
    """Test cases for FilterService."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db = Database(self.temp_db.name)
        self.filter_service = FilterService(self.db)

        # Create test project
        cursor = self.db.conn.cursor()
        cursor.execute("INSERT INTO projects (name) VALUES (?)", ("Test Project",))
        self.project_id = cursor.lastrowid

        # Create test sentence
        cursor.execute(
            "INSERT INTO sentences (project_id, display_order, text_oe) VALUES (?, ?, ?)",
            (self.project_id, 1, "Se cyning fēoll on þǣm dæge")
        )
        self.sentence_id = cursor.lastrowid

        # Create tokens with various annotations
        self._create_test_tokens_and_annotations(cursor)
        self.db.conn.commit()

    def _create_test_tokens_and_annotations(self, cursor):
        """Create test tokens with different annotation states."""
        # Token 1: Complete pronoun annotation
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 0, "Se")
        )
        token_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case", pronoun_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (token_id, "R", "m", "s", "n", "d")
        )

        # Token 2: Incomplete noun annotation (missing case)
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 1, "cyning")
        )
        token_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number)
               VALUES (?, ?, ?, ?)""",
            (token_id, "N", "m", "s")
        )

        # Token 3: Complete verb annotation
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 2, "fēoll")
        )
        token_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, verb_tense, verb_mood, verb_person, number)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (token_id, "V", "p", "i", 3, "s")
        )

        # Token 4: Incomplete verb annotation (missing tense)
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 3, "wæs")
        )
        token_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, verb_mood, verb_person, number)
               VALUES (?, ?, ?, ?, ?)""",
            (token_id, "V", "i", 3, "s")
        )

        # Token 5: Preposition with missing case
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 4, "on")
        )
        token_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO annotations (token_id, pos) VALUES (?, ?)",
            (token_id, "E")
        )

        # Token 6: Uncertain adjective
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 5, "gōd")
        )
        token_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case", uncertain)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (token_id, "A", "m", "s", "n", 1)
        )

        # Token 7: No annotation
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 6, "þǣm")
        )

    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        os.unlink(self.temp_db.name)

    def test_filter_by_pos_noun(self):
        """Test filtering tokens by POS (Noun)."""
        criteria = FilterCriteria(pos="N")
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "cyning")
        self.assertEqual(results[0]["pos"], "N")

    def test_filter_by_pos_verb(self):
        """Test filtering tokens by POS (Verb)."""
        criteria = FilterCriteria(pos="V")
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        self.assertEqual(len(results), 2)
        surfaces = {r["surface"] for r in results}
        self.assertEqual(surfaces, {"fēoll", "wæs"})

    def test_filter_incomplete_nouns(self):
        """Test filtering incomplete noun annotations."""
        criteria = FilterCriteria(pos="N", incomplete=True)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find the noun with missing case
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "cyning")
        self.assertIsNone(results[0]["case"])

    def test_filter_incomplete_verbs(self):
        """Test filtering incomplete verb annotations."""
        criteria = FilterCriteria(pos="V", incomplete=True)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find the verb with missing tense
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "wæs")
        self.assertIsNone(results[0]["verb_tense"])

    def test_filter_incomplete_prepositions(self):
        """Test filtering incomplete preposition annotations."""
        criteria = FilterCriteria(pos="E", incomplete=True)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find the preposition with missing case
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "on")
        self.assertIsNone(results[0]["prep_case"])

    def test_filter_all_incomplete(self):
        """Test filtering all incomplete annotations regardless of POS."""
        criteria = FilterCriteria(incomplete=True)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find: incomplete noun, incomplete verb, incomplete preposition
        self.assertEqual(len(results), 3)
        surfaces = {r["surface"] for r in results}
        self.assertEqual(surfaces, {"cyning", "wæs", "on"})

    def test_filter_by_uncertainty(self):
        """Test filtering by uncertainty flag."""
        criteria = FilterCriteria(uncertain=True)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find the uncertain adjective
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "gōd")
        self.assertTrue(results[0]["uncertain"])

    def test_filter_by_certain_only(self):
        """Test filtering for certain annotations only."""
        criteria = FilterCriteria(uncertain=False)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find all annotated tokens except the uncertain one
        surfaces = {r["surface"] for r in results}
        self.assertIn("Se", surfaces)
        self.assertIn("cyning", surfaces)
        self.assertNotIn("gōd", surfaces)

    def test_filter_by_missing_field(self):
        """Test filtering by specific missing field."""
        criteria = FilterCriteria(missing_field="verb_tense")
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find verbs with missing tense
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "wæs")

    def test_filter_with_confidence_range(self):
        """Test filtering by confidence range."""
        # Add annotations with different confidence levels
        cursor = self.db.conn.cursor()
        
        # Update existing annotations with confidence
        cursor.execute(
            "UPDATE annotations SET confidence = 90 WHERE token_id = (SELECT id FROM tokens WHERE surface = 'Se')"
        )
        cursor.execute(
            "UPDATE annotations SET confidence = 50 WHERE token_id = (SELECT id FROM tokens WHERE surface = 'cyning')"
        )
        cursor.execute(
            "UPDATE annotations SET confidence = 80 WHERE token_id = (SELECT id FROM tokens WHERE surface = 'fēoll')"
        )
        self.db.conn.commit()

        # Filter for high confidence (>= 80)
        criteria = FilterCriteria(min_confidence=80)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        surfaces = {r["surface"] for r in results}
        self.assertIn("Se", surfaces)  # 90
        self.assertIn("fēoll", surfaces)  # 80
        self.assertNotIn("cyning", surfaces)  # 50

    def test_filter_combined_criteria(self):
        """Test filtering with multiple criteria combined."""
        # Filter for incomplete nouns that are uncertain
        criteria = FilterCriteria(pos="N", incomplete=True, uncertain=False)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find the incomplete noun that is not uncertain
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "cyning")

    def test_get_statistics(self):
        """Test getting annotation statistics for a project."""
        stats = self.filter_service.get_statistics(self.project_id)
        
        # 7 total tokens
        self.assertEqual(stats["total_tokens"], 7)
        
        # 6 annotated tokens (all except "þǣm")
        self.assertEqual(stats["annotated_tokens"], 6)
        
        # 1 unannotated token
        self.assertEqual(stats["unannotated_tokens"], 1)
        
        # POS distribution
        self.assertEqual(stats["pos_distribution"]["N"], 1)
        self.assertEqual(stats["pos_distribution"]["V"], 2)
        self.assertEqual(stats["pos_distribution"]["R"], 1)
        self.assertEqual(stats["pos_distribution"]["A"], 1)
        self.assertEqual(stats["pos_distribution"]["E"], 1)
        
        # 1 uncertain annotation
        self.assertEqual(stats["uncertain_count"], 1)
        
        # 3 incomplete annotations
        self.assertEqual(stats["incomplete_count"], 3)

    def test_filter_pronoun_incomplete(self):
        """Test filtering incomplete pronoun annotations."""
        # Add incomplete pronoun (missing type)
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 7, "hē")
        )
        token_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO annotations (token_id, pos, gender, number, "case")
               VALUES (?, ?, ?, ?, ?)""",
            (token_id, "R", "m", "s", "n")
        )
        self.db.conn.commit()

        criteria = FilterCriteria(pos="R", incomplete=True)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find the pronoun with missing type
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "hē")
        self.assertIsNone(results[0]["pronoun_type"])

    def test_filter_adjective_incomplete(self):
        """Test filtering incomplete adjective annotations."""
        # Add incomplete adjective (missing case)
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO tokens (sentence_id, order_index, surface) VALUES (?, ?, ?)",
            (self.sentence_id, 8, "micel")
        )
        token_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO annotations (token_id, pos, gender, number) VALUES (?, ?, ?, ?)",
            (token_id, "A", "m", "s")
        )
        self.db.conn.commit()

        criteria = FilterCriteria(pos="A", incomplete=True)
        results = self.filter_service.find_tokens(self.project_id, criteria)
        
        # Should find the adjective with missing case
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surface"], "micel")
        self.assertIsNone(results[0]["case"])


if __name__ == '__main__':
    unittest.main()
