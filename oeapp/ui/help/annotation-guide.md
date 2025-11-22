# Annotation Guide

## Overview

The Ænglisc Toolkit allows you to add detailed morphological annotations
to tokens in your text. Annotations include Part of Speech (POS), grammatical
features, and metadata.

## Starting an Annotation

1. Select a token in the token table (use arrow keys or click)
2. Press **A** to open the annotation modal
3. Select the Part of Speech from the dropdown or use keyboard shortcuts:

   - **N** - Noun
   - **V** - Verb
   - **A** - Adjective
   - **R** - Pronoun
   - **D** - Determiner/Article
   - **B** - Adverb
   - **C** - Conjunction
   - **E** - Preposition
   - **I** - Interjection

## Annotation Fields by POS

### Nouns

- **Gender**: Masculine (m), Feminine (f), Neuter (n)
- **Number**: Singular (s), Plural (p)
- **Case**: Nominative (n), Accusative (a), Genitive (g), Dative (d), Instrumental (i)
- **Declension**: Strong (s), Weak (w), Other (o), i-stem (i), u-stem (u), ja-stem (ja), jo-stem (jo), wa-stem (wa), wo-stem (wo)

### Verbs

- **Verb Class**: Anomolous (a), Weak Class I (w1), Weak Class II (w2), Weak Class III (w3), Strong Class I-VII (s1-s7)
- **Tense**: Past (p), Present (n)
- **Mood**: Indicative (i), Subjunctive (s), Imperative (imp)
- **Person**: First (1), Second (2), Third (3)
- **Number**: Singular (s), Plural (p)
- **Aspect**: Perfect (p), Progressive (prg), Gnomic (gn)
- **Form**: Finite (f), Infinitive (i), Participle (p)

### Adjectives

- **Gender**: Masculine (m), Feminine (f), Neuter (n)
- **Number**: Singular (s), Plural (p)
- **Case**: Nominative (n), Accusative (a), Genitive (g), Dative (d), Instrumental (i)
- **Degree**: Positive (p), Comparative (c), Superlative (s)
- **Inflection**: Strong (s), Weak (w)

### Pronouns

- **Pronoun Type**: Personal (p), Relative (r), Demonstrative (d), Interrogative (i)
- **Gender**: Masculine (m), Feminine (f), Neuter (n)
- **Number**: Singular (s), Plural (p)
- **Case**: Nominative (n), Accusative (a), Genitive (g), Dative (d), Instrumental (i)

### Determiners/Articles

- **Type**: Definite (d), Indefinite (i), Possessive (p), Demonstrative (D)
- **Gender**: Masculine (m), Feminine (f), Neuter (n)
- **Number**: Singular (s), Plural (p)
- **Case**: Nominative (n), Accusative (a), Genitive (g), Dative (d), Instrumental (i)

### Prepositions

- **Object Case**: Accusative (a), Dative (d), Genitive (g)

### Adverbs

- Adverbs have minimal grammatical fields in the current system.

## Metadata Fields

The following fields are available for all POS types in the Metadata section:

- **Uncertain**: Mark the annotation as uncertain (displays with a "?" in exports)
- **Alternatives**: Enter alternative interpretations (e.g., "w2 / s3")
- **Confidence**: Set confidence level from 0-100% using the slider
- **TODO**: Mark annotation as needing review
- **Modern English Meaning**: Enter the modern English translation/meaning of the word (e.g., "time, season")
- **Root**: Enter the root form of the word (e.g., "sumor")

These metadata fields are displayed in the token table as "ModE" and "Root" columns.

## Applying Annotations

- Click **Apply** or press **Enter** to save your annotation
- Click **Clear** to remove all fields and start over
- Click **Cancel** or press **Escape** to discard changes

## Incremental Annotation

You don't need to fill in all fields at once! You can:

1. Start with just the Part of Speech
2. Add grammatical features later
3. Refine annotations as you work through the text

The system remembers your last-used values for each POS type, making it faster to annotate similar tokens.
