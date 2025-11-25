from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation


class AnnotationTextualMixin:
    """Mixin for annotation textual representation."""

    # ===============================
    # General
    # ===============================

    #: A lookup map for part of speech codes to their short form.
    PART_OF_SPEECH_MAP: Final[dict[str, str]] = {
        "N": "n",
        "V": "v",
        "A": "adj",
        "R": "pron",
        "D": "det",
        "B": "adv",
        "C": "conj",
        "E": "prep",
        "I": "int",
    }

    #: A lookup map for gender codes to their short form.
    GENDER_MAP: Final[dict[str, str]] = {
        "m": "m",
        "f": "f",
        "n": "n",
    }

    # ===============================
    # Articles/Determiners
    # ===============================

    #: Article type map.
    ARTICLE_TYPE_MAP: Final[dict[str, str]] = {
        "d": "def",
        "i": "ind",
        "p": "poss",
        "D": "dem",
    }

    # ===============================
    # Nouns
    # ===============================

    #: A lookup map for number codes to their long form.
    CASE_MAP: Final[dict[str, str]] = {
        "n": "nom",
        "a": "acc",
        "g": "gen",
        "d": "dat",
        "i": "inst",
    }

    #: A lookup map for number codes to their short form.
    NUMBER_MAP: Final[dict[str, str]] = {
        "s": "1",
        "p": "pl",
    }

    #: A lookup map for declension codes to their short form.
    DECLENSION_MAP: Final[dict[str, str]] = {
        "s": "strong",
        "w": "weak",
        "o": "other",
        "i": "i",
        "u": "u",
        "ja": "ja",
        "jo": "jo",
        "wa": "wa",
        "wo": "wo",
    }

    # ===============================
    # Pronouns
    # ===============================

    #: Pronoun type map.
    PRONOUN_TYPE_MAP: Final[dict[str, str]] = {
        "p": "pers",
        "r": "rel",
        "d": "dem",
        "i": "int",
    }

    #: Pronoun number map.
    PRONOUN_NUMBER_MAP: Final[dict[str, str]] = {
        "s": "1",
        "d": "D",
        "pl": "pl",
    }

    # ===============================
    # Verbs
    # ===============================

    #: Verb class map.
    VERB_CLASS_MAP: Final[dict[str, str]] = {
        "a": "a",
        "w1": "weak1",
        "w2": "weak2",
        "w3": "weak3",
        "s1": "strong1",
        "s2": "strong2",
        "s3": "strong3",
        "s4": "strong4",
        "s5": "strong5",
        "s6": "strong6",
        "s7": "strong7",
    }

    #: Verb tense map.
    VERB_TENSE_MAP: Final[dict[str, str]] = {
        "p": "pa",
        "n": "pr",
    }

    #: Verb mood map.
    VERB_MOOD_MAP: Final[dict[str, str]] = {
        "i": "i",
        "s": "subj",
        "imp": "I",
    }

    #: Verb aspect map.
    VERB_ASPECT_MAP: Final[dict[str, str]] = {
        "p": "perf",
        "f": "fut",
        "prg": "prg",
        "gn": "gn",
    }

    #: Verb person map.
    VERB_PERSON_MAP: Final[dict[str, str]] = {
        "1": "1",
        "2": "2",
        "3": "3",
        "pl": "pl",
    }

    VERB_FORM_MAP: Final[dict[str, str]] = {
        "f": "",
        "i": "inf",
        "p": "part",
    }

    #: Verb number map.
    VERB_NUMBER_MAP: Final[dict[str, str]] = {
        "s": "s",
        "p": "pl",
    }

    # ===============================
    # Adjectives
    # ===============================

    #: Adjective degree map.
    ADJECTIVE_DEGREE_MAP: Final[dict[str, str]] = {
        "p": "pos",
        "c": "comp",
        "s": "sup",
    }

    #: Adjective inflection map.
    ADJECTIVE_INFLECTION_MAP: Final[dict[str, str]] = {
        "s": "strong",
        "w": "weak",
    }

    # ===============================
    # Adverbs
    # ===============================

    #: Adverb degree map.
    ADVERB_DEGREE_MAP: Final[dict[str, str]] = {
        "p": "pos",
        "c": "comp",
        "s": "sup",
    }

    # ===============================
    # Prepositions
    # ===============================

    #: Preposition case map.
    PREP_CASE_MAP: Final[dict[str, str]] = {
        "a": "acc",
        "d": "dat",
        "g": "gen",
    }

    # ===============================
    # Conjunctions
    # ===============================

    #: Conjunction type map.
    CONJUNCTION_TYPE_MAP: Final[dict[str, str]] = {
        "c": "coord",
        "s": "sub",
    }

    def format_pos(self, annotation: Annotation) -> str:  # noqa: PLR0911, PLR0912
        """
        Format part of speech abbreviation for display.  This is the bit
        that comes as a superscript before the token and gender.

        Args:
            annotation: Annotation object

        Returns:
            Formatted POS string

        """
        if annotation.pos is None:
            return ""

        # Start with the part of speech abbreviation
        pos_str = self.PART_OF_SPEECH_MAP[annotation.pos]
        if annotation.pos == "N":
            # Nouns get declension
            if not annotation.declension:
                return pos_str
            noun_declension_str = self.DECLENSION_MAP[annotation.declension]
            pos_str += f":{noun_declension_str}"
        elif annotation.pos == "V":
            # Verbs get class
            if not annotation.verb_class:
                return pos_str
            verb_class_str = self.VERB_CLASS_MAP[annotation.verb_class]
            pos_str += f":{verb_class_str}"
        elif annotation.pos == "A":
            # Adjectives get inflection and degree
            if not annotation.adjective_inflection:
                return pos_str
            adjective_inflection_str = self.ADJECTIVE_INFLECTION_MAP[
                annotation.adjective_inflection
            ]
            pos_str += f":{adjective_inflection_str}"
            if not annotation.adjective_degree:
                return pos_str
            adjective_degree_str = self.ADJECTIVE_DEGREE_MAP[
                annotation.adjective_degree
            ]
            pos_str += f":{adjective_degree_str}"
        elif annotation.pos == "R":
            # Pronouns get type
            if not annotation.pronoun_type:
                return pos_str
            pronoun_type_str = self.PRONOUN_TYPE_MAP[annotation.pronoun_type]
            pos_str += f":{pronoun_type_str}"
        elif annotation.pos == "D":
            # Articles/Determiners get type
            if not annotation.article_type:
                return pos_str
            article_type_str = self.ARTICLE_TYPE_MAP[annotation.article_type]
            pos_str += f":{article_type_str}"
        elif annotation.pos == "B":
            # Adverbs get degree
            if not annotation.adverb_degree:
                return pos_str
            adverb_degree_str = self.ADVERB_DEGREE_MAP[annotation.adverb_degree]
            pos_str += f":{adverb_degree_str}"
        elif annotation.pos == "C":
            # Conjunctions get type
            if not annotation.conjunction_type:
                return pos_str
            conjunction_type_str = self.CONJUNCTION_TYPE_MAP[
                annotation.conjunction_type
            ]
            pos_str += f":{conjunction_type_str}"
        elif annotation.pos in {"E", "I"}:
            # Prepositions and interjections don't get any additional information
            pass
        return pos_str

    def format_gender(self, annotation: Annotation) -> str:
        """
        Format gender abbreviation for display.  This is the bit
        that comes as a superscript before the token and after the POS.

        Args:
            annotation: Annotation object

        Returns:
            Formatted gender string

        """
        if not annotation.pos:
            return ""
        # Only nouns, verbs, adjectives, pronouns, and articles/determiners can
        # have gender
        if annotation.pos in {"N", "V", "A", "R", "D"}:
            if not annotation.gender:
                return ""
            return self.GENDER_MAP[annotation.gender]
        return ""

    def format_context(self, annotation: Annotation) -> str:  # noqa: PLR0911, PLR0912
        """
        Format context abbreviation for display.  This is the bit
        tha comes as a subscript after the token.

        Args:
            annotation: Annotation object

        Returns:
            Formatted context string

        """
        if not annotation.pos:
            return ""
        context_str = ""
        if annotation.pos in {"N", "A", "R", "D"}:
            # Nouns, adjectives, pronouns, and articles/determiners get case and number
            if not annotation.case:
                return context_str
            context_str += self.CASE_MAP[annotation.case]
            if annotation.pos == "R":
                print(f"annotation.pronoun_number: {annotation.pronoun_number}")
                if not annotation.pronoun_number:
                    return context_str
                context_str += self.PRONOUN_NUMBER_MAP[annotation.pronoun_number]
            else:
                if not annotation.number:
                    return context_str
                context_str += self.NUMBER_MAP[annotation.number]
        elif annotation.pos == "V":
            if annotation.verb_form == "part":
                # If it's a participle, just return the form, and the tense
                context_str += "part"
                if not annotation.verb_tense:
                    return context_str
                context_str += self.VERB_TENSE_MAP[annotation.verb_tense]
            elif annotation.verb_form == "inf":
                # If it's an infinitive, just return the form
                context_str = "inf"
            else:
                # If it's a finite verb, return the tense, mood, person and number
                if not annotation.verb_tense:
                    return context_str
                context_str += self.VERB_TENSE_MAP[annotation.verb_tense]
                if not annotation.verb_mood:
                    return context_str
                context_str += self.VERB_MOOD_MAP[annotation.verb_mood]
                if not annotation.verb_person:
                    return context_str
                context_str += self.VERB_PERSON_MAP[annotation.verb_person]
                if not annotation.number:
                    return context_str
                context_str += self.VERB_NUMBER_MAP[annotation.number]
        elif annotation.pos == "E":
            # Prepositions get preposition case
            if not annotation.prep_case:
                return context_str
            context_str += self.PREP_CASE_MAP[annotation.prep_case]
        return context_str
