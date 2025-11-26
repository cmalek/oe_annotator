"""DOCX export service for Ænglisc Toolkit."""

from typing import TYPE_CHECKING, cast

from docx import Document
from docx.shared import Pt, RGBColor

from oeapp.mixins import AnnotationTextualMixin, TokenOccurrenceMixin
from oeapp.models.project import Project

if TYPE_CHECKING:
    from pathlib import Path

    from docx.document import Document as DocumentObject
    from sqlalchemy.orm import Session

    from oeapp.models.annotation import Annotation
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


class DOCXExporter(AnnotationTextualMixin, TokenOccurrenceMixin):
    """
    Exports annotated Old English text to DOCX format.

    Args:
        session: SQLAlchemy session

    """

    def __init__(self, session: Session) -> None:
        """
        Initialize exporter.

        Args:
            session: SQLAlchemy session

        """
        self.session = session

    def export(self, project_id: int, output_path: Path) -> bool:
        """
        Export project to DOCX file.

        Args:
            project_id: Project ID to export
            output_path: Path to output DOCX file

        Returns:
            True if successful, False otherwise

        """
        doc: DocumentObject = Document()
        self._setup_document_styles(doc)
        project = Project.get(self.session, project_id)
        if project is None:
            return False

        # Add title
        doc.add_heading(project.name, level=1)
        doc.add_paragraph()  # Blank line after title

        for sentence in project.sentences:
            display_order = sentence.display_order
            text_modern = sentence.text_modern

            # Add sentence number
            sentence_num_para = doc.add_paragraph()
            sentence_num_run = sentence_num_para.add_run(f"[{display_order}] ")
            sentence_num_run.bold = True

            # Build Old English sentence with annotations
            self._add_oe_sentence_with_annotations(doc, sentence)

            # Add translation
            if text_modern:
                translation_para = doc.add_paragraph()
                translation_run = translation_para.add_run(text_modern)
                translation_run.font.size = Pt(12)
                translation_run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
            else:
                # Empty translation paragraph
                doc.add_paragraph()

            # Blank line
            doc.add_paragraph()

            # Add notes
            self._add_notes(doc, sentence)

            # Blank line between sentences
            doc.add_paragraph()

        try:
            doc.save(str(output_path))
        except OSError as e:
            print(f"Export error: {e}")  # noqa: T201
            return False
        else:
            return True

    def _setup_document_styles(self, doc: DocumentObject) -> None:
        """
        Set up document styles.

        Args:
            doc: Document to set up

        """
        # Styles are already available in python-docx
        # Title, Body, Default are standard styles

    def _add_oe_sentence_with_annotations(
        self,
        doc: DocumentObject,
        sentence: Sentence,
    ) -> None:
        """
        Add Old English sentence with superscript/subscript annotations.

        Uses the original sentence.text_oe to preserve all punctuation and spacing,
        then adds annotations (pos, gender, context) for each token.

        Args:
            doc: Document to add to
            sentence: Sentence to add

        """
        # Build paragraph with annotations
        para = doc.add_paragraph()  # type: ignore[attr-defined]

        # Use original sentence text to preserve punctuation
        text = sentence.text_oe
        tokens = list(sentence.tokens)

        if not tokens:
            # No tokens, just add the text as-is
            para.add_run(text)
            return

        # Sort tokens by order_index to process them in order
        sorted_tokens = sorted(tokens, key=lambda t: t.order_index)

        # Find token positions in the original text
        # (start, end, token) positions
        token_positions: list[tuple[int, int, Token]] = []
        used_positions: set[tuple[int, int]] = set()

        for token in sorted_tokens:
            if not token.surface:
                continue
            token_start = self._find_token_occurrence(text, token, tokens)
            if token_start is not None:
                token_end = token_start + len(token.surface)
                position_key = (token_start, token_end)

                # Only add if this position hasn't been used yet
                if position_key not in used_positions:
                    token_positions.append((token_start, token_end, token))
                    used_positions.add(position_key)

        # Sort by position
        token_positions.sort(key=lambda x: x[0])

        # Build document by preserving text between tokens
        last_pos = 0
        for token_start, token_end, token in token_positions:
            # Skip if this token overlaps with a previous one
            if token_start < last_pos:
                continue

            # Add text before token (preserving punctuation and spacing)
            if token_start > last_pos:
                para.add_run(text[last_pos:token_start])

            # Add token with annotations
            annotation = token.annotation

            # POS label (superscript)
            pos_label = self.format_pos(cast("Annotation", annotation))
            if pos_label:
                pos_run = para.add_run(pos_label)
                pos_run.font.size = Pt(8)
                pos_run.font.superscript = True
                pos_run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

            # Gender label (subscript)
            gender_label = self.format_gender(cast("Annotation", annotation))
            if gender_label:
                gender_run = para.add_run(gender_label)
                gender_run.font.size = Pt(8)
                gender_run.font.subscript = True
                gender_run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

            # Add word
            word_run = para.add_run(token.surface)
            word_run.font.size = Pt(12)

            # Context label (subscript)
            context_label = self.format_context(cast("Annotation", annotation))
            if context_label:
                context_run = para.add_run(context_label)
                context_run.font.size = Pt(8)
                context_run.font.subscript = True
                context_run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

            last_pos = token_end

        # Add remaining text after last token
        if last_pos < len(text):
            para.add_run(text[last_pos:])

    def _add_notes(self, doc: DocumentObject, sentence: Sentence) -> None:
        """
        Add notes for a sentence.

        Notes are sorted by their position in the sentence (by start token
        order_index) and numbered accordingly.

        Args:
            doc: Document to add to
            sentence: Sentence to add notes for

        """
        if not sentence.notes:
            return

        # Sort notes by token position in sentence (earlier tokens = lower numbers)
        notes = self._sort_notes_by_position(sentence)

        # Build token ID to order_index mapping for token lookups
        token_id_to_order: dict[int, int] = {}
        for token in sentence.tokens:
            if token.id:
                token_id_to_order[token.id] = token.order_index

        # Display each note with dynamic numbering (1-based index)
        for note_idx, note in enumerate(notes, start=1):
            # Get token text for the note
            token_text = self._get_note_token_text(note, sentence, token_id_to_order)

            # Format note: "1. "quoted tokens" in italics - note text"
            if token_text:
                note_line = f'{note_idx}. "{token_text}" - {note.note_text_md}'
            else:
                note_line = f"{note_idx}. {note.note_text_md}"

            note_para = doc.add_paragraph()
            note_run = note_para.add_run(note_line)
            note_run.font.size = Pt(10)
            note_run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    def _sort_notes_by_position(self, sentence: Sentence) -> list:
        """
        Sort notes by their position in the sentence (by start token order_index).

        Args:
            sentence: Sentence to get notes from

        Returns:
            Sorted list of notes

        """
        # Build token ID to order_index mapping
        token_id_to_order: dict[int, int] = {}
        for token in sentence.tokens:
            if token.id:
                token_id_to_order[token.id] = token.order_index

        def get_note_position(note) -> int:
            """Get position of note in sentence based on start token."""
            if note.start_token and note.start_token in token_id_to_order:
                return token_id_to_order[note.start_token]
            # Fallback to end_token if start_token not found
            if note.end_token and note.end_token in token_id_to_order:
                return token_id_to_order[note.end_token]
            # Fallback to very high number if neither found
            return 999999

        # Sort notes by position
        return sorted(sentence.notes, key=get_note_position)

    def _get_note_token_text(
        self,
        note,
        sentence: Sentence,
        token_id_to_order: dict[int, int],  # noqa: ARG002
    ) -> str:
        """
        Get token text for a note.

        Args:
            note: Note to get tokens for
            sentence: Sentence containing the tokens
            token_id_to_order: Map of token ID to order_index

        Returns:
            Token text string (space-separated tokens)

        """
        if not note.start_token or not note.end_token:
            return ""

        # Find tokens by ID
        start_token = None
        end_token = None
        for token in sentence.tokens:
            if token.id == note.start_token:
                start_token = token
            if token.id == note.end_token:
                end_token = token

        if not start_token or not end_token:
            return ""

        # Get all tokens in range
        tokens_in_range = []
        in_range = False
        for token in sorted(sentence.tokens, key=lambda t: t.order_index):
            if token.id == start_token.id:
                in_range = True
            if in_range:
                tokens_in_range.append(token.surface)
            if token.id == end_token.id:
                break

        return " ".join(tokens_in_range)
