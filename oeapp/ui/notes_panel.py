"""Notes panel UI component."""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from oeapp.models.note import Note
    from oeapp.models.sentence import Sentence


class ClickableNoteLabel(QLabel):
    """
    QLabel that emits signals when clicked or double-clicked.

    Args:
        note: Note to display
        parent: Parent widget

    """

    clicked = Signal(object)  # Emits Note
    double_clicked = Signal(object)  # Emits Note

    def __init__(self, note: Note, parent: QWidget | None = None):
        """
        Initialize clickable note label.
        """
        super().__init__(parent)
        self.note = note
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.note)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse double-click event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.note)
        super().mouseDoubleClickEvent(event)


class NotesPanel(QWidget):
    """
    Widget displaying notes panel.

    Args:
        sentence: Sentence to display notes for
        parent: Parent widget

    """

    note_clicked = Signal(object)  # Emits Note when clicked
    note_double_clicked = Signal(object)  # Emits Note when double-clicked

    def __init__(
        self,
        sentence: Sentence | None = None,
        parent: QWidget | None = None,
    ):
        """
        Initialize notes panel.

        Args:
            sentence: Sentence to display notes for
            parent: Parent widget

        """
        super().__init__(parent)
        self.sentence = sentence
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Will be populated by update_notes()
        self.note_labels: list[ClickableNoteLabel] = []

    def update_notes(self, sentence: Sentence | None = None) -> None:
        """
        Update notes display.

        Args:
            sentence: Sentence to display notes for (optional, uses
                :attr:`sentence` if None)

        """
        if sentence is not None:
            self.sentence = sentence

        # Clear existing labels
        for label in self.note_labels:
            label.deleteLater()
        self.note_labels.clear()

        layout = self.layout()
        if layout is None:
            return

        # Clear layout
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()

        if not self.sentence:
            # Show empty state
            empty_label = QLabel("(No notes yet)")
            empty_label.setStyleSheet("color: #666; font-style: italic;")
            empty_label.setFont(QFont("Helvetica", 10))
            layout.addWidget(empty_label)
            return

        # Safely access notes relationship (may be lazy-loaded)
        try:
            notes_list = list(self.sentence.notes) if self.sentence.notes else []
        except Exception:
            # If relationship access fails, show empty state
            notes_list = []

        if not notes_list:
            # Show empty state
            empty_label = QLabel("(No notes yet)")
            empty_label.setStyleSheet("color: #666; font-style: italic;")
            empty_label.setFont(QFont("Helvetica", 10))
            layout.addWidget(empty_label)
            return

        # Sort notes by token position in sentence (earlier tokens = lower numbers)
        # Note: Numbers are computed dynamically, so if a note is deleted,
        # remaining notes are automatically renumbered (e.g., if note 2 is
        # deleted, note 3 becomes note 2)
        notes = self._sort_notes_by_position(notes_list)

        # Display each note with dynamic numbering (1-based index)
        for note_idx, note in enumerate(notes, start=1):
            note_text = self._format_note(note_idx, note)
            note_label = ClickableNoteLabel(note, self)
            note_label.setText(note_text)
            note_label.setFont(QFont("Helvetica", 12))
            note_label.setWordWrap(True)
            note_label.clicked.connect(self.note_clicked.emit)
            note_label.double_clicked.connect(self.note_double_clicked.emit)
            layout.addWidget(note_label)
            self.note_labels.append(note_label)

        # Add spacer at the end
        spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        layout.addItem(spacer)

    def _format_note(self, note_number: int, note: Note) -> str:
        """
        Format note for display.

        Args:
            note_number: Note number (1-based)
            note: Note to format

        Returns:
            Formatted note string

        """
        # Get token text
        token_text = self._get_token_text(note)

        # Format: "1. "quoted tokens" in italics - note text"
        if token_text:
            return f'{note_number}. <i>"{token_text}"</i> - {note.note_text_md}'
        return f"{note_number}. {note.note_text_md}"

    def _get_token_text(self, note: Note) -> str:
        """
        Get token text for a note.

        Args:
            note: Note to get tokens for

        Returns:
            Token text string

        """
        if not self.sentence or not self.sentence.tokens:
            return ""

        # Find tokens by ID
        start_token = None
        end_token = None
        for token in self.sentence.tokens:
            if token.id == note.start_token:
                start_token = token
            if token.id == note.end_token:
                end_token = token

        if not start_token or not end_token:
            return ""

        # Get all tokens in range
        tokens_in_range = []
        in_range = False
        for token in sorted(self.sentence.tokens, key=lambda t: t.order_index):
            if token.id == start_token.id:
                in_range = True
            if in_range:
                tokens_in_range.append(token.surface)
            if token.id == end_token.id:
                break

        return " ".join(tokens_in_range)

    def _sort_notes_by_position(self, notes: list[Note]) -> list[Note]:
        """
        Sort notes by their position in the sentence (by start token order_index).

        Args:
            notes: List of notes to sort

        Returns:
            Sorted list of notes

        """
        if not self.sentence or not self.sentence.tokens:
            return notes

        # Build token ID to order_index mapping
        token_id_to_order: dict[int, int] = {}
        for token in self.sentence.tokens:
            if token.id:
                token_id_to_order[token.id] = token.order_index

        def get_note_position(note: Note) -> int:
            """Get position of note in sentence based on start token."""
            if note.start_token and note.start_token in token_id_to_order:
                return token_id_to_order[note.start_token]
            # Fallback to end_token if start_token not found
            if note.end_token and note.end_token in token_id_to_order:
                return token_id_to_order[note.end_token]
            # Fallback to very high number if neither found
            return 999999

        return sorted(notes, key=get_note_position)
