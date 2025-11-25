"""Annotation lookup maps mixin."""

from typing import Final


class AnnotationLookupsMixin:
    """Mixin class providing lookup maps for annotation fields."""

    #: A lookup map for part of speech codes to their long form.
    PART_OF_SPEECH_MAP: Final[dict[str, str | None]] = {
        "": None,
        "N": "Noun (N)",
        "V": "Verb (V)",
        "A": "Adjective (A)",
        "R": "Pronoun (R)",
        "D": "Determiner/Article (D)",
        "B": "Adverb (B)",
        "C": "Conjunction (C)",
        "E": "Preposition (E)",
        "I": "Interjection (I)",
    }
    #: A Reverse lookup map for part of speech long form to code.  The key
    # is the long form, and the value is the code.
    PART_OF_SPEECH_REVERSE_MAP: Final[dict[str, str]] = {
        v: k for k, v in PART_OF_SPEECH_MAP.items() if v is not None
    }

    #: A lookup map for article type codes to their long form.
    ARTICLE_TYPE_MAP: Final[dict[str | None, str]] = {
        None: "",
        "d": "Definite (d)",
        "i": "Indefinite (i)",
        "p": "Possessive (p)",
        "D": "Demonstrative (D)",
    }
    #: A Reverse lookup map for article type long form to code.  The key
    #: is the index of the long form in the ARTICLE_TYPE_MAP, and the value
    #: is the code.
    ARTICLE_TYPE_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(ARTICLE_TYPE_MAP.keys()) if k is not None
    }

    #: A lookup map for gender codes to their long form.
    GENDER_MAP: Final[dict[str | None, str]] = {
        None: "",
        "m": "Masculine (m)",
        "f": "Feminine (f)",
        "n": "Neuter (n)",
    }
    #: A Reverse lookup map for gender long form to code.  The key
    #: is the index of the long form in the GENDER_MAP, and the value
    #: is the code.
    GENDER_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(GENDER_MAP.keys()) if k is not None
    }

    #: A lookup map for number codes to their long form.
    NUMBER_MAP: Final[dict[str | None, str]] = {
        None: "",
        "s": "Singular (s)",
        "p": "Plural (p)",
    }
    #: A Reverse lookup map for number long form to code.  The key
    #: is the index of the long form in the NUMBER_MAP, and the value
    #: is the code.
    NUMBER_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(NUMBER_MAP.keys()) if k is not None
    }

    #: A lookup map for case codes to their long form.
    CASE_MAP: Final[dict[str | None, str]] = {
        None: "",
        "n": "Nominative (n)",
        "a": "Accusative (a)",
        "g": "Genitive (g)",
        "d": "Dative (d)",
        "i": "Instrumental (i)",
    }
    #: A Reverse lookup map for case long form to code.  The key
    #: is the index of the long form in the CASE_MAP, and the value
    #: is the code.
    CASE_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(CASE_MAP.keys()) if k is not None
    }

    #: A lookup map for declension codes to their long form.
    DECLENSION_MAP: Final[dict[str | None, str]] = {
        None: "",
        "s": "Strong (s)",
        "w": "Weak (w)",
        "o": "Other (o)",
        "i": "i-stem (i)",
        "u": "u-stem (u)",
        "ja": "ja-stem (ja)",
        "jo": "jo-stem (jo)",
        "wa": "wa-stem (wa)",
        "wo": "wo-stem (wo)",
    }
    #: A Reverse lookup map for declension long form to code.  The key
    #: is the index of the long form in the DECLENSION_MAP, and the value
    #: is the code.
    DECLENSION_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(DECLENSION_MAP.values()) if k is not None
    }

    #: A lookup map for verb class codes to their long form.
    VERB_CLASS_MAP: Final[dict[str | None, str]] = {
        None: "",
        "a": "Anomolous (a)",
        "w1": "Weak Class I (w1)",
        "w2": "Weak Class II (w2)",
        "w3": "Weak Class III (w3)",
        "s1": "Strong Class 1 (s1)",
        "s2": "Strong Class 2 (s2)",
        "s3": "Strong Class 3 (s3)",
        "s4": "Strong Class 4 (s4)",
        "s5": "Strong Class 5 (s5)",
        "s6": "Strong Class 6 (s6)",
        "s7": "Strong Class 7 (s7)",
    }
    #: A Reverse lookup map for verb class long form to code.  The key
    #: is the index of the long form in the VERB_CLASS_MAP, and the value
    #: is the code.
    VERB_CLASS_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(VERB_CLASS_MAP.keys()) if k is not None
    }

    #: A lookup map for verb tense codes to their long form.
    VERB_TENSE_MAP: Final[dict[str | None, str]] = {
        None: "",
        "p": "Past (p)",
        "n": "Present (n)",
    }
    VERB_TENSE_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(VERB_TENSE_MAP.keys()) if k is not None
    }

    #: A lookup map for verb mood codes to their long form.
    VERB_MOOD_MAP: Final[dict[str | None, str]] = {
        None: "",
        "i": "Indicative (i)",
        "s": "Subjunctive (s)",
        "imp": "Imperative (imp)",
    }
    #: A Reverse lookup map for verb mood long form to code.  The key
    #: is the index of the long form in the VERB_MOOD_MAP, and the value
    #: is the code.
    VERB_MOOD_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(VERB_MOOD_MAP.keys()) if k is not None
    }

    #: A lookup map for verb person codes to their long form.
    VERB_PERSON_MAP: Final[dict[str | None, str]] = {
        None: "",
        "1": "1st",
        "2": "2nd",
        "3": "3rd",
    }

    #: A Reverse lookup map for verb person long form to code.  The key
    #: is the index of the long form in the VERB_PERSON_MAP, and the value
    #: is the code.
    VERB_PERSON_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(VERB_PERSON_MAP.keys()) if k is not None
    }

    #: A lookup map for verb aspect codes to their long form.
    VERB_ASPECT_MAP: Final[dict[str | None, str]] = {
        None: "",
        "p": "Perfect (p)",
        "prg": "Progressive (prg)",
        "gn": "Gnomic (gn)",
    }
    #: A Reverse lookup map for verb aspect long form to code.  The key
    #: is the index of the long form in the VERB_ASPECT_MAP, and the value
    #: is the code.
    VERB_ASPECT_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(VERB_ASPECT_MAP.keys()) if k is not None
    }

    #: A lookup map for verb form codes to their long form.
    VERB_FORM_MAP: Final[dict[str | None, str]] = {
        None: "",
        "f": "Finite (f)",
        "i": "Infinitive (i)",
        "p": "Participle (p)",
    }
    VERB_FORM_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(VERB_FORM_MAP.keys()) if k is not None
    }

    # Pronoun
    # -------

    #: A lookup map for pronoun type codes to their long form.
    PRONOUN_TYPE_MAP: Final[dict[str | None, str]] = {
        None: "",
        "p": "Personal (p)",
        "r": "Relative (r)",
        "d": "Demonstrative (d)",
        "i": "Interrogative (i)",
    }
    #: A Reverse lookup map for pronoun type long form to code.  The key
    #: is the index of the long form in the PRONOUN_TYPE_MAP, and the value
    #: is the code.
    PRONOUN_TYPE_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(PRONOUN_TYPE_MAP.keys()) if k is not None
    }

    #: A lookup map for pronoun number codes to their long form.
    PRONOUN_NUMBER_MAP: Final[dict[str | None, str]] = {
        None: "",
        "s": "Singular (s)",
        "d": "Dual (d)",
        "pl": "Plural (pl)",
    }
    #: A Reverse lookup map for pronoun number long form to code.  The key
    #: is the index of the long form in the PRONOUN_NUMBER_MAP, and the value
    #: is the code.
    PRONOUN_NUMBER_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(PRONOUN_NUMBER_MAP.keys()) if k is not None
    }

    #: A lookup map for adjective degree codes to their long form.
    ADJECTIVE_DEGREE_MAP: Final[dict[str | None, str]] = {
        None: "",
        "p": "Positive (p)",
        "c": "Comparative (c)",
        "s": "Superlative (s)",
    }
    #: A Reverse lookup map for adjective degree long form to code.  The key
    #: is the index of the long form in the ADJECTIVE_DEGREE_MAP, and the value
    #: is the code.
    ADJECTIVE_DEGREE_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(ADJECTIVE_DEGREE_MAP.keys()) if k is not None
    }

    #: A lookup map for adjective inflection codes to their long form.
    ADJECTIVE_INFLECTION_MAP: Final[dict[str | None, str]] = {
        None: "",
        "s": "Strong (s)",
        "w": "Weak (w)",
    }
    #: A Reverse lookup map for adjective inflection long form to code.  The key
    #: is the index of the long form in the ADJECTIVE_INFLECTION_MAP, and the value
    #: is the code.
    ADJECTIVE_INFLECTION_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(ADJECTIVE_INFLECTION_MAP.keys()) if k is not None
    }

    #: A lookup map for adverb degree codes to their long form.
    ADVERB_DEGREE_MAP: Final[dict[str | None, str]] = {
        None: "",
        "p": "Positive (p)",
        "c": "Comparative (c)",
        "s": "Superlative (s)",
    }
    #: A Reverse lookup map for adverb degree long form to code.  The key
    #: is the index of the long form in the ADVERB_DEGREE_MAP, and the value
    #: is the code.
    ADVERB_DEGREE_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(ADVERB_DEGREE_MAP.keys()) if k is not None
    }

    #: A lookup map for preposition case codes to their long form.
    PREPOSITION_CASE_MAP: Final[dict[str | None, str]] = {
        None: "",
        "a": "Accusative (a)",
        "d": "Dative (d)",
        "g": "Genitive (g)",
    }
    #: A Reverse lookup map for preposition case long form to code.  The key
    #: is the index of the long form in the PREPOSITION_CASE_MAP, and the value
    #: is the code.
    PREPOSITION_CASE_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(PREPOSITION_CASE_MAP.keys()) if k is not None
    }

    #: A lookup map for conjunction type codes to their long form.
    CONJUNCTION_TYPE_MAP: Final[dict[str | None, str]] = {
        None: "",
        "c": "Coordinating (c)",
        "s": "Subordinating (s)",
    }
    #: A Reverse lookup map for conjunction type long form to code.  The key
    #: is the index of the long form in the CONJUNCTION_TYPE_MAP, and the value
    #: is the code.
    CONJUNCTION_TYPE_REVERSE_MAP: Final[dict[int, str]] = {
        i: k for i, k in enumerate(CONJUNCTION_TYPE_MAP.keys()) if k is not None
    }
