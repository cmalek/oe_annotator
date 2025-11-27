"""Sentence card UI component."""

from contextlib import suppress
from typing import TYPE_CHECKING, ClassVar, cast

from PySide6.QtCore import QPoint, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QMouseEvent,
    QShortcut,
    Qt,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from oeapp.mixins import TokenOccurrenceMixin
from oeapp.models.annotation import Annotation
from oeapp.models.sentence import Sentence
from oeapp.services import (
    AddSentenceCommand,
    AnnotateTokenCommand,
    CommandManager,
    DeleteSentenceCommand,
    EditSentenceCommand,
    MergeSentenceCommand,
)
from oeapp.ui.dialogs import (
    AnnotationModal,
    CaseFilterDialog,
    NoteDialog,
    POSFilterDialog,
)
from oeapp.ui.notes_panel import NotesPanel
from oeapp.ui.token_table import TokenTable
from oeapp.utils import get_logo_pixmap

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from oeapp.models.note import Note
    from oeapp.models.token import Token


class ClickableTextEdit(QTextEdit):
    """QTextEdit that emits a signal when clicked."""

    clicked = Signal(QPoint, object)  # position, modifiers
    double_clicked = Signal(QPoint)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse press event and emit clicked signal."""
        super().mousePressEvent(event)
        self.clicked.emit(event.position().toPoint(), event.modifiers())

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse double-click event and emit double_clicked signal."""
        super().mouseDoubleClickEvent(event)
        self.double_clicked.emit(event.position().toPoint())


class SentenceCard(TokenOccurrenceMixin, QWidget):
    """
    Widget representing a sentence card with annotations.

    Args:
        sentence: Sentence model instance

    Keyword Args:
        session: SQLAlchemy session
        command_manager: Command manager for undo/redo
        parent: Parent widget

    """

    # Signal emitted when a sentence is merged
    sentence_merged = Signal(int)  # Emits current sentence ID
    # Signal emitted when a sentence is added
    sentence_added = Signal(int)  # Emits new sentence ID
    # Signal emitted when a sentence is deleted
    sentence_deleted = Signal(int)  # Emits deleted sentence ID
    # Signal emitted when a token is selected for details sidebar
    # Note: Using object for SentenceCard to avoid circular import
    token_selected_for_details = Signal(
        object, object, object
    )  # Token, Sentence, SentenceCard
    # Signal emitted when an annotation is applied
    annotation_applied = Signal(Annotation)

    # Color maps for highlighting
    POS_COLORS: ClassVar[dict[str | None, QColor]] = {
        "N": QColor(173, 216, 230),  # Light blue for Noun
        "V": QColor(255, 182, 193),  # Light pink for Verb
        "A": QColor(144, 238, 144),  # Light green for Adjective
        "R": QColor(255, 165, 0),  # Orange for Pronoun
        "D": QColor(221, 160, 221),  # Plum for Determiner/Article
        "B": QColor(175, 238, 238),  # Pale turquoise for Adverb
        "C": QColor(255, 20, 147),  # Deep pink for Conjunction
        "E": QColor(255, 255, 0),  # Yellow for Preposition
        "I": QColor(255, 192, 203),  # Pink for Interjection
        None: QColor(255, 255, 255),  # White (no highlight) for unannotated
    }

    CASE_COLORS: ClassVar[dict[str | None, QColor]] = {
        "n": QColor(173, 216, 230),  # Light blue for Nominative
        "a": QColor(144, 238, 144),  # Light green for Accusative
        "g": QColor(255, 255, 153),  # Light yellow for Genitive
        "d": QColor(255, 200, 150),  # Light orange for Dative
        "i": QColor(255, 182, 193),  # Light pink for Instrumental
        None: QColor(255, 255, 255),  # White (no highlight) for unannotated
    }

    NUMBER_COLORS: ClassVar[dict[str | None, QColor]] = {
        "s": QColor(173, 216, 230),  # Light blue for Singular
        "p": QColor(255, 127, 127),  # Light coral for Plural
        None: QColor(255, 255, 255),  # White (no highlight) for unannotated
    }

    def __init__(
        self,
        sentence: Sentence,
        session: Session | None = None,
        command_manager: CommandManager | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.sentence = sentence
        self.session = session
        self.command_manager = command_manager
        self.token_table = TokenTable()
        self.tokens: list[Token] = sentence.tokens
        self.annotations: dict[int, Annotation | None] = {
            cast("int", token.id): token.annotation for token in self.tokens if token.id
        }
        # Track current highlight position to clear it later
        self._current_highlight_start: int | None = None
        self._current_highlight_length: int | None = None
        # Track current highlight mode (None, 'pos', 'case', 'number')
        self._current_highlight_mode: str | None = None
        # Track selected cases for highlighting (default: all cases)
        self._selected_cases: set[str] = {"n", "a", "g", "d", "i"}
        # Track selected POS tags for highlighting (default: all POS tags)
        self._selected_pos: set[str] = {"N", "V", "A", "R", "D", "B", "C", "E", "I"}
        # Case filter dialog reference
        self._case_filter_dialog: CaseFilterDialog | None = None
        # POS filter dialog reference
        self._pos_filter_dialog: POSFilterDialog | None = None
        # Track selected token index for details sidebar
        self.selected_token_index: int | None = None
        # Track selected token range for notes (start_index, end_index inclusive)
        self._selected_token_range: tuple[int, int] | None = None
        # Timer to delay deselection to allow double-click to cancel it
        self._deselect_timer = QTimer(self)
        self._deselect_timer.setSingleShot(True)
        self._deselect_timer.timeout.connect(self._perform_deselection)
        self._pending_deselect_token_index: int | None = None
        # Track OE edit mode state
        self._oe_edit_mode: bool = False
        self._original_oe_text: str | None = None
        self._setup_ui()
        self._setup_shortcuts()

    @property
    def has_focus(self) -> bool:
        """
        Check if this sentence card has focus.
        """
        return any(
            [
                self.hasFocus(),
                self.token_table.has_focus,
                self.translation_edit.hasFocus(),
                self.oe_text_edit.hasFocus(),
            ]
        )

    def _setup_shortcuts(self):
        """
        Set up keyboard shortcuts.

        The following shortcuts are set up:
        - 'A' key to annotate selected token
        - Arrow keys for token navigation
        - 'Ctrl+Enter' to split sentence
        - 'Ctrl+M' to merge sentence
        - 'Ctrl+Delete' to delete sentence
        """
        # 'A' key to annotate selected token
        annotate_shortcut = QShortcut(QKeySequence("A"), self)
        annotate_shortcut.activated.connect(self._open_annotation_modal)

        # Arrow keys for token navigation
        next_token_shortcut = QShortcut(QKeySequence("Right"), self)
        next_token_shortcut.activated.connect(self._next_token)
        prev_token_shortcut = QShortcut(QKeySequence("Left"), self)
        prev_token_shortcut.activated.connect(self._prev_token)

    def _next_token(self) -> None:
        """Navigate to next token."""
        current_row = self.token_table.current_row
        if current_row < len(self.tokens) - 1:
            self.token_table.select_token(current_row + 1)

    def _prev_token(self):
        """Navigate to previous token."""
        current_row = self.token_table.current_row
        if current_row > 1 and self.tokens:
            self.token_table.select_token(current_row - 1)

    def _setup_ui(self):  # noqa: PLR0915
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header with sentence number and actions
        header_layout = QHBoxLayout()
        self.sentence_number_label = QLabel(f"[{self.sentence.display_order}]")
        self.sentence_number_label.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        header_layout.addWidget(self.sentence_number_label)

        # Action buttons
        # self.split_button = QPushButton("Split")
        self.add_sentence_button = QPushButton("Add Sentence")
        # Create menu for Add Sentence button
        add_sentence_menu = QMenu(self)
        before_action = add_sentence_menu.addAction("Before")
        before_action.triggered.connect(self._on_add_sentence_before_clicked)
        after_action = add_sentence_menu.addAction("After")
        after_action.triggered.connect(self._on_add_sentence_after_clicked)
        self.add_sentence_button.setMenu(add_sentence_menu)
        self.merge_button = QPushButton("Merge with next")
        self.merge_button.clicked.connect(self._on_merge_clicked)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self._on_delete_clicked)
        header_layout.addStretch()
        # header_layout.addWidget(self.split_button)
        header_layout.addWidget(self.add_sentence_button)
        header_layout.addWidget(self.merge_button)
        header_layout.addWidget(self.delete_button)
        layout.addLayout(header_layout)

        # Old English text line (editable) with highlighting dropdown
        oe_label_layout = QHBoxLayout()
        oe_label = QLabel("Old English:")
        oe_label.setFont(QFont("Anvers", 18))
        oe_label_layout.addWidget(oe_label)
        oe_label_layout.addStretch()

        # Add Note button
        self.add_note_button = QPushButton("Add Note")
        self.add_note_button.clicked.connect(self._on_add_note_clicked)
        self.add_note_button.setEnabled(False)  # Disabled until tokens are selected
        oe_label_layout.addWidget(self.add_note_button)

        # Edit OE button
        self.edit_oe_button = QPushButton("Edit OE")
        self.edit_oe_button.clicked.connect(self._on_edit_oe_clicked)
        oe_label_layout.addWidget(self.edit_oe_button)

        # Save OE and Cancel Edit buttons (initially hidden)
        self.save_oe_button = QPushButton("Save OE")
        self.save_oe_button.clicked.connect(self._on_save_oe_clicked)
        self.save_oe_button.setVisible(False)
        oe_label_layout.addWidget(self.save_oe_button)

        self.cancel_edit_button = QPushButton("Cancel Edit")
        self.cancel_edit_button.clicked.connect(self._on_cancel_edit_clicked)
        self.cancel_edit_button.setVisible(False)
        oe_label_layout.addWidget(self.cancel_edit_button)

        # Dropdown for highlighting options
        highlighting_label = QLabel("Highlighting:")
        oe_label_layout.addWidget(highlighting_label)
        self.highlighting_combo = QComboBox()
        self.highlighting_combo.addItems(["None", "Part of Speech", "Case", "Number"])
        self.highlighting_combo.currentIndexChanged.connect(
            self._on_highlighting_changed
        )
        oe_label_layout.addWidget(self.highlighting_combo)

        layout.addLayout(oe_label_layout)

        self.oe_text_edit = ClickableTextEdit()
        self.oe_text_edit.setPlainText(self.sentence.text_oe)
        self.oe_text_edit.setFont(QFont("Anvers", 18))
        self.oe_text_edit.setPlaceholderText("Enter Old English text...")
        # Make read-only by default (selectable but not editable)
        self.oe_text_edit.setReadOnly(True)
        self.oe_text_edit.textChanged.connect(self._on_oe_text_changed)
        self.oe_text_edit.clicked.connect(self._on_oe_text_clicked)
        self.oe_text_edit.double_clicked.connect(self._on_oe_text_double_clicked)
        layout.addWidget(self.oe_text_edit)
        # Render OE text with superscripts after setting up the widget
        # Use QTimer.singleShot to ensure widget is fully initialized
        QTimer.singleShot(0, self._render_oe_text_with_superscripts)

        # Token annotation grid (hidden by default)
        self.token_table.annotation_requested.connect(self._open_annotation_modal)
        self.token_table.token_selected.connect(self._highlight_token_in_text)
        self.token_table.setVisible(False)
        layout.addWidget(self.token_table)
        self.set_tokens(self.tokens)

        # Modern English translation with toggle button
        translation_label_layout = QHBoxLayout()
        translation_label = QLabel("Modern English Translation:")
        translation_label.setFont(QFont("Helvetica", 16))
        translation_label_layout.addWidget(translation_label)
        translation_label_layout.addStretch()

        # Toggle button for token table
        self.token_table_toggle_button = QPushButton("Show Token Table")
        self.token_table_toggle_button.clicked.connect(self._toggle_token_table)
        translation_label_layout.addWidget(self.token_table_toggle_button)

        layout.addLayout(translation_label_layout)

        self.translation_edit = QTextEdit()
        self.translation_edit.setPlainText(self.sentence.text_modern or "")
        self.translation_edit.setFont(QFont("Helvetica", 16))
        self.translation_edit.setPlaceholderText("Enter Modern English translation...")
        self.translation_edit.setMaximumHeight(100)
        self.translation_edit.textChanged.connect(self._on_translation_changed)
        layout.addWidget(self.translation_edit)

        # Notes section
        notes_label = QLabel("Notes:")
        notes_label.setFont(QFont("Helvetica", 10))
        layout.addWidget(notes_label)

        self.notes_panel = NotesPanel(sentence=self.sentence, parent=self)
        self.notes_panel.note_clicked.connect(self._on_note_clicked)
        self.notes_panel.note_double_clicked.connect(self._on_note_double_clicked)
        layout.addWidget(self.notes_panel)
        # Update notes display on initialization
        self._update_notes_display()

        layout.addStretch()

    def set_tokens(self, tokens: list[Token]):
        """
        Set tokens for this sentence card.  This will also load the annotations
        for the tokens.

        Args:
            tokens: List of tokens

        """
        self.tokens = tokens
        self.annotations = {
            cast("int", token.id): token.annotation for token in self.tokens if token.id
        }
        self.token_table.set_tokens(tokens)

        # Re-apply highlighting if a mode is active
        if self._current_highlight_mode == "pos":
            self._apply_pos_highlighting()
        elif self._current_highlight_mode == "case":
            self._apply_case_highlighting()
        elif self._current_highlight_mode == "number":
            self._apply_number_highlighting()

    def _open_annotation_modal(self) -> None:
        """
        Open annotation modal for selected token.
        """
        token: Token | None = self.token_table.get_selected_token()
        if not token:
            # Select first token if none selected
            if self.tokens:
                token = self.tokens[0]
                self.token_table.select_token(0)
            else:
                return

        # Open modal - get or create annotation
        annotation = token.annotation
        if annotation is None and self.session and token.id:
            annotation = Annotation.get(self.session, token.id)
        modal = AnnotationModal(token, annotation, self)
        modal.annotation_applied.connect(self._on_annotation_applied)
        modal.exec()

    def _on_annotation_applied(self, annotation: Annotation) -> None:
        """
        Handle annotation applied signal.

        Args:
            annotation: Applied annotation

        """
        # Get before state
        before_annotation = self.annotations.get(annotation.token_id)
        before_state = {}
        if before_annotation:
            before_state = {
                "pos": before_annotation.pos,
                "gender": before_annotation.gender,
                "number": before_annotation.number,
                "case": before_annotation.case,
                "declension": before_annotation.declension,
                "pronoun_type": before_annotation.pronoun_type,
                "pronoun_number": before_annotation.pronoun_number,
                "verb_class": before_annotation.verb_class,
                "verb_tense": before_annotation.verb_tense,
                "verb_person": before_annotation.verb_person,
                "verb_mood": before_annotation.verb_mood,
                "verb_aspect": before_annotation.verb_aspect,
                "verb_form": before_annotation.verb_form,
                "prep_case": before_annotation.prep_case,
                "uncertain": before_annotation.uncertain,
                "adverb_degree": before_annotation.adverb_degree,
                "adjective_inflection": before_annotation.adjective_inflection,
                "adjective_degree": before_annotation.adjective_degree,
                "conjunction_type": before_annotation.conjunction_type,
                "alternatives_json": before_annotation.alternatives_json,
                "confidence": before_annotation.confidence,
                "modern_english_meaning": before_annotation.modern_english_meaning,
                "root": before_annotation.root,
            }

        after_state = {
            "pos": annotation.pos,
            "gender": annotation.gender,
            "number": annotation.number,
            "case": annotation.case,
            "declension": annotation.declension,
            "pronoun_type": annotation.pronoun_type,
            "pronoun_number": annotation.pronoun_number,
            "verb_class": annotation.verb_class,
            "verb_tense": annotation.verb_tense,
            "verb_person": annotation.verb_person,
            "verb_mood": annotation.verb_mood,
            "verb_aspect": annotation.verb_aspect,
            "verb_form": annotation.verb_form,
            "prep_case": annotation.prep_case,
            "adverb_degree": annotation.adverb_degree,
            "adjective_inflection": annotation.adjective_inflection,
            "adjective_degree": annotation.adjective_degree,
            "conjunction_type": annotation.conjunction_type,
            "uncertain": annotation.uncertain,
            "alternatives_json": annotation.alternatives_json,
            "confidence": annotation.confidence,
            "modern_english_meaning": annotation.modern_english_meaning,
            "root": annotation.root,
        }

        # Create command for undo/redo
        if self.command_manager and self.session:
            assert self.command_manager is not None  # noqa: S101
            assert self.session is not None  # noqa: S101
            command = AnnotateTokenCommand(
                session=self.session,
                token_id=annotation.token_id,
                before=before_state,
                after=after_state,
            )
            if self.command_manager.execute(command):
                # Update local cache
                self.annotations[annotation.token_id] = annotation
                # Update token table display
                self.token_table.update_annotation(annotation)
                # Emit signal for annotation applied
                self.annotation_applied.emit(annotation)
                return

        # Fallback: direct save if command manager not available
        if self.session:
            self._save_annotation(annotation)

        # Update local cache
        self.annotations[annotation.token_id] = annotation

        # Update token table display
        self.token_table.update_annotation(annotation)

        # Emit signal for annotation applied
        self.annotation_applied.emit(annotation)

        # Re-apply highlighting if a mode is active
        if self._current_highlight_mode == "pos":
            self._apply_pos_highlighting()
        elif self._current_highlight_mode == "case":
            self._apply_case_highlighting()
        elif self._current_highlight_mode == "number":
            self._apply_number_highlighting()

    def _on_oe_text_clicked(
        self, position: QPoint, modifiers: Qt.KeyboardModifier
    ) -> None:
        """
        Handle click on Old English text to select corresponding token.

        Args:
            position: Mouse click position in widget coordinates
            modifiers: Keyboard modifiers (e.g., Shift key)

        """
        # Get cursor at click position
        cursor = self.oe_text_edit.cursorForPosition(position)
        cursor_pos = cursor.position()

        # Get the plain text
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        # Find which token contains this cursor position
        # We need to map cursor position to token by finding which token's
        # surface text spans that position
        token_index = self._find_token_at_position(text, cursor_pos)
        if token_index is not None:
            # Cancel any pending deselection (in case this is part of a double-click)
            if self._deselect_timer.isActive():
                self._deselect_timer.stop()
                self._pending_deselect_token_index = None

            # Check for Shift+click for range selection
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                # Shift+click: extend selection to create a range
                if self.selected_token_index is not None:
                    # Create range from selected_token_index to clicked token_index
                    start_idx = min(self.selected_token_index, token_index)
                    end_idx = max(self.selected_token_index, token_index)
                    self._selected_token_range = (start_idx, end_idx)
                    self._highlight_token_range(start_idx, end_idx)
                    # Clear single token selection and sidebar when range is selected
                    self.selected_token_index = None
                    # Emit signal to clear sidebar (main window checks
                    # selected_token_index)
                    token = self.tokens[start_idx]
                    self.token_selected_for_details.emit(token, self.sentence, self)
                    # Enable Add Note button when range is selected
                    self.add_note_button.setEnabled(True)
                else:
                    # No previous selection, just select this token
                    self.selected_token_index = token_index
                    self._selected_token_range = None
                    token = self.tokens[token_index]
                    self._highlight_token_in_text(token)
                    self.token_selected_for_details.emit(token, self.sentence, self)
                    # Enable Add Note button when token is selected
                    self.add_note_button.setEnabled(True)
            else:
                # Normal click: select single token
                self._selected_token_range = None
                # Check if clicking the same token (schedule deselection after delay)
                if self.selected_token_index == token_index:
                    # Schedule deselection with a delay to allow double-click to
                    # cancel it
                    self._pending_deselect_token_index = token_index
                    self._deselect_timer.start(
                        300
                    )  # 300ms delay, typical double-click timeout
                else:
                    # Select the token and emit signal for sidebar
                    self.selected_token_index = token_index
                    token = self.tokens[token_index]
                    self._highlight_token_in_text(token)
                    self.token_selected_for_details.emit(token, self.sentence, self)

    def _on_oe_text_double_clicked(self, position: QPoint) -> None:
        """
        Handle double-click on Old English text to open annotation dialog for token.

        Args:
            position: Mouse double-click position in widget coordinates

        """
        # Get cursor at click position
        cursor = self.oe_text_edit.cursorForPosition(position)
        cursor_pos = cursor.position()

        # Get the plain text
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        # Find which token contains this cursor position
        token_index = self._find_token_at_position(text, cursor_pos)
        if token_index is not None:
            # Cancel any pending deselection timer (from single-click)
            if self._deselect_timer.isActive():
                self._deselect_timer.stop()
                self._pending_deselect_token_index = None
            # Select the token in the table
            self.token_table.select_token(token_index)
            # Set selected token index and update sidebar
            self.selected_token_index = token_index
            token = self.tokens[token_index]
            self._highlight_token_in_text(token)
            self.token_selected_for_details.emit(token, self.sentence, self)
            # Open the annotation modal for this token
            # Get or create annotation
            annotation = token.annotation
            if annotation is None and self.session and token.id:
                annotation = Annotation.get(self.session, token.id)
            modal = AnnotationModal(token, annotation, self)
            modal.annotation_applied.connect(self._on_annotation_applied)
            modal.exec()

    def _find_token_at_position(self, text: str, position: int) -> int | None:
        """
        Find the token index that contains the given character position.

        Args:
            text: The full sentence text
            position: Character position in the text

        Returns:
            Token index if found, None otherwise

        """
        if not self.tokens:
            return None

        # Build a mapping of token positions in the text
        token_positions: list[tuple[int, int, int]] = []  # (start, end, token_index)

        for token_idx, token in enumerate(self.tokens):
            surface = token.surface
            if not surface:
                continue

            token_start = self._find_token_occurrence(text, token, self.tokens)
            if token_start is None:
                continue

            token_end = token_start + len(surface)
            token_positions.append((token_start, token_end, token_idx))

        # Find which token contains the position
        for start, end, token_idx in token_positions:
            if start <= position < end:
                return token_idx

        # If position is not within any token, find the nearest token
        # (useful for whitespace between tokens)
        return self._find_nearest_token(token_positions, position)

    def _find_nearest_token(
        self, token_positions: list[tuple[int, int, int]], position: int
    ) -> int | None:
        """
        Find the nearest token to the given position.

        Args:
            token_positions: List of (start, end, token_index) tuples
            position: Character position in the text

        Returns:
            Token index of nearest token, or None if no tokens found

        """
        nearest_token = None
        min_distance = float("inf")
        for start, end, token_idx in token_positions:
            # Check distance to start and end of token
            if position < start:
                distance = start - position
            elif position >= end:
                distance = position - end + 1
            else:
                # Position is within token (shouldn't happen here, but handle it)
                return token_idx

            if distance < min_distance:
                min_distance = distance
                nearest_token = token_idx

        return nearest_token

    def _on_oe_text_changed(self) -> None:
        """Handle Old English text change."""
        # Don't process changes if not in edit mode (shouldn't happen if signal
        # is disconnected)
        if not self._oe_edit_mode:
            return

        # Clear temporary selection highlight when text is edited
        self._clear_highlight()
        # Re-apply highlighting mode if active (though highlights will be
        # cleared when entering edit mode)
        if self._current_highlight_mode == "pos":
            self._apply_pos_highlighting()
        elif self._current_highlight_mode == "case":
            self._apply_case_highlighting()
        elif self._current_highlight_mode == "number":
            self._apply_number_highlighting()

    def _on_edit_oe_clicked(self) -> None:
        """Handle Edit OE button click - enter edit mode."""
        # Set edit mode
        self._oe_edit_mode = True
        # Store original text (plain text without superscripts)
        self._original_oe_text = self.sentence.text_oe
        # Set plain text (remove superscripts)
        self.oe_text_edit.setPlainText(self._original_oe_text)
        # Clear all highlighting
        self._clear_all_highlights()
        # Clear token selection highlight
        self._clear_highlight()
        # Reset highlighting dropdown to None (index 0)
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
        self._current_highlight_mode = None
        # Hide any open filter dialogs
        if self._pos_filter_dialog is not None:
            self._pos_filter_dialog.hide()
        if self._case_filter_dialog is not None:
            self._case_filter_dialog.hide()
        # Hide Edit OE button and Add Note button
        self.edit_oe_button.setVisible(False)
        self.add_note_button.setVisible(False)
        # Show Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(True)
        self.cancel_edit_button.setVisible(True)
        # Enable editing
        self.oe_text_edit.setReadOnly(False)
        # Disconnect textChanged signal to prevent auto-tokenization
        with suppress(TypeError):
            self.oe_text_edit.textChanged.disconnect(self._on_oe_text_changed)

    def _on_save_oe_clicked(self) -> None:
        """Handle Save OE button click - save changes and exit edit mode."""
        # Exit edit mode
        self._oe_edit_mode = False
        # Make read-only again
        self.oe_text_edit.setReadOnly(True)
        # Hide Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        # Show Edit OE button
        self.edit_oe_button.setVisible(True)
        # Reconnect textChanged signal
        self.oe_text_edit.textChanged.connect(self._on_oe_text_changed)

        # Get new text and save
        if not self.session or not self.command_manager or not self.sentence.id:
            self._original_oe_text = None
            # Re-render with superscripts
            self._render_oe_text_with_superscripts()
            return

        new_text = self.oe_text_edit.toPlainText()
        old_text = self.sentence.text_oe

        if new_text != old_text:
            command = EditSentenceCommand(
                session=self.session,
                sentence_id=self.sentence.id,
                field="text_oe",
                before=old_text,
                after=new_text,
            )
            if self.command_manager.execute(command):
                self.sentence.text_oe = new_text
                # Refresh tokens after retokenization
                self.session.refresh(self.sentence)
                self.set_tokens(self.sentence.tokens)
                # Update notes display
                self._update_notes_display()
                # Re-apply highlighting if a mode is active
                if self._current_highlight_mode == "pos":
                    self._apply_pos_highlighting()
                elif self._current_highlight_mode == "case":
                    self._apply_case_highlighting()
                elif self._current_highlight_mode == "number":
                    self._apply_number_highlighting()

        # Re-render with superscripts
        self._render_oe_text_with_superscripts()
        # Clear original text
        self._original_oe_text = None

    def _on_cancel_edit_clicked(self) -> None:
        """Handle Cancel Edit button click - discard changes and exit edit mode."""
        # Exit edit mode
        self._oe_edit_mode = False
        # Restore original text
        if self._original_oe_text is not None:
            self.oe_text_edit.setPlainText(self._original_oe_text)
        # Make read-only again
        self.oe_text_edit.setReadOnly(True)
        # Hide Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        # Show Edit OE button and Add Note button
        self.edit_oe_button.setVisible(True)
        self.add_note_button.setVisible(True)
        # Reconnect textChanged signal
        self.oe_text_edit.textChanged.connect(self._on_oe_text_changed)
        # Re-render with superscripts
        self._render_oe_text_with_superscripts()
        # Clear original text
        self._original_oe_text = None

    def enter_edit_mode(self) -> bool:
        """
        Programmatically enter edit mode and focus the Old English text box.

        Returns:
            True if successful, False otherwise

        """
        if self._oe_edit_mode:
            # Already in edit mode, just focus
            self.oe_text_edit.setFocus()
            return True

        # Enter edit mode
        self._on_edit_oe_clicked()
        # Set focus on OE text edit
        self.oe_text_edit.setFocus()
        return True

    def _on_translation_changed(self) -> None:
        """Handle translation text change."""
        if not self.session or not self.command_manager or not self.sentence.id:
            return

        new_text = self.translation_edit.toPlainText()
        old_text = self.sentence.text_modern or ""

        if new_text != old_text:
            command = EditSentenceCommand(
                session=self.session,
                sentence_id=self.sentence.id,
                field="text_modern",
                before=old_text,
                after=new_text,
            )
            if self.command_manager.execute(command):
                self.sentence.text_modern = new_text

    def _on_highlighting_changed(self, index: int) -> None:
        """
        Handle highlighting dropdown selection change.

        Args:
            index: Selected index (0=None, 1=Part of Speech, 2=Case, 3=Number)

        """
        # Block signals to prevent recursive calls when updating dropdown
        # programmatically
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003

        if index == 0:  # None
            self._current_highlight_mode = None
            self._clear_all_highlights()
            # Hide dialogs if they exist
            if self._pos_filter_dialog is not None:
                self._pos_filter_dialog.hide()
            if self._case_filter_dialog is not None:
                self._case_filter_dialog.hide()
        elif index == 1:  # Part of Speech
            self._current_highlight_mode = "pos"
            # Create or show the POS filter dialog
            if self._pos_filter_dialog is None:
                self._pos_filter_dialog = POSFilterDialog(self)
                self._pos_filter_dialog.pos_changed.connect(self._on_pos_changed)
                self._pos_filter_dialog.dialog_closed.connect(
                    self._on_pos_dialog_closed
                )
                # Set initial selected POS tags
                self._pos_filter_dialog.set_selected_pos(self._selected_pos)
            self._pos_filter_dialog.show()
            self._apply_pos_highlighting()
        elif index == 2:  # Case  # noqa: PLR2004
            self._current_highlight_mode = "case"
            # Create or show the case filter dialog
            if self._case_filter_dialog is None:
                self._case_filter_dialog = CaseFilterDialog(self)
                self._case_filter_dialog.cases_changed.connect(self._on_cases_changed)
                self._case_filter_dialog.dialog_closed.connect(self._on_dialog_closed)
                # Set initial selected cases
                self._case_filter_dialog.set_selected_cases(self._selected_cases)
            self._case_filter_dialog.show()
            self._apply_case_highlighting()
        elif index == 3:  # Number  # noqa: PLR2004
            self._current_highlight_mode = "number"
            self._apply_number_highlighting()

        self.highlighting_combo.blockSignals(False)  # noqa: FBT003

    def _on_pos_toggle(self, checked: bool) -> None:  # noqa: FBT001
        """Handle POS highlighting toggle."""
        if checked:
            # Update dropdown to Part of Speech
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(1)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(1)
        else:
            # Update dropdown to None
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(0)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(0)

    def _on_case_toggle(self, checked: bool) -> None:  # noqa: FBT001
        """Handle case highlighting toggle."""
        if checked:
            # Update dropdown to Case
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(2)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(2)
        else:
            # Update dropdown to None
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(0)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(0)

    def _on_cases_changed(self, selected_cases: set[str]) -> None:
        """
        Handle case selection changes from the dialog.

        Args:
            selected_cases: Set of selected case codes

        """
        self._selected_cases = selected_cases
        # Re-apply highlighting if case highlighting is active
        if self._current_highlight_mode == "case":
            self._apply_case_highlighting()

    def _on_dialog_closed(self) -> None:
        """Handle dialog close event by resetting the dropdown to None."""
        # Reset dropdown to None and clear highlights
        # Block signals temporarily to avoid triggering change signal
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
        # Clear highlights and reset mode (dialog is already closing, so don't hide it)
        self._current_highlight_mode = None
        self._clear_all_highlights()

    def _on_pos_changed(self, selected_pos: set[str]) -> None:
        """
        Handle POS selection changes from the dialog.

        Args:
            selected_pos: Set of selected POS codes

        """
        self._selected_pos = selected_pos
        # Re-apply highlighting if POS highlighting is active
        if self._current_highlight_mode == "pos":
            self._apply_pos_highlighting()

    def _on_pos_dialog_closed(self) -> None:
        """Handle POS dialog close event by resetting the dropdown to None."""
        # Reset dropdown to None and clear highlights
        # Block signals temporarily to avoid triggering change signal
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
        # Clear highlights and reset mode (dialog is already closing, so don't hide it)
        self._current_highlight_mode = None
        self._clear_all_highlights()

    def _on_number_toggle(self, checked: bool) -> None:  # noqa: FBT001
        """Handle number highlighting toggle."""
        if checked:
            # Update dropdown to Number
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(3)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(3)
        else:
            # Update dropdown to None
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(0)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(0)

    def _apply_pos_highlighting(self) -> None:
        """
        Apply colors based on parts of speech.

        Only highlights POS tags that are in the :attr:`_selected_pos` set.
        """
        self._clear_all_highlights()
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        extra_selections = []
        for token in self.tokens:
            if not token.id:
                continue
            annotation = self.annotations.get(cast("int", token.id))
            if not annotation:
                continue

            pos = annotation.pos
            # Only highlight if POS is in selected POS tags
            if pos in self._selected_pos:
                color = self.POS_COLORS.get(pos, self.POS_COLORS[None])
                if color != self.POS_COLORS[None]:  # Only highlight if not default
                    selection = self._create_token_selection(token, text, color)
                    if selection:
                        extra_selections.append(selection)

        self.oe_text_edit.setExtraSelections(extra_selections)

    def _apply_case_highlighting(self) -> None:
        """
        Apply colors based on case values.

        Highlights articles, nouns, pronouns, adjectives, and prepositions.
        Only highlights cases that are in the :attr:`_selected_cases` set.
        """
        self._clear_all_highlights()
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        extra_selections = []
        for token in self.tokens:
            if not token.id:
                continue
            annotation = self.annotations.get(cast("int", token.id))
            if not annotation:
                continue

            pos = annotation.pos
            # Only highlight articles (D), nouns (N), pronouns (R),
            # adjectives (A), and prepositions (E)
            if pos not in ["D", "N", "R", "A", "E"]:
                continue

            # For prepositions, use prep_case; for others, use case
            case_value = annotation.prep_case if pos == "E" else annotation.case
            # Only highlight if case is in selected cases and not default
            if case_value in self._selected_cases:
                color = self.CASE_COLORS.get(case_value, self.CASE_COLORS[None])
                # Only highlight if not default
                if color != self.CASE_COLORS[None]:
                    selection = self._create_token_selection(token, text, color)
                    if selection:
                        extra_selections.append(selection)

        self.oe_text_edit.setExtraSelections(extra_selections)

    def _apply_number_highlighting(self) -> None:
        """
        Apply colors based on number values.

        Highlights articles, nouns, pronouns, and adjectives.
        """
        self._clear_all_highlights()
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        extra_selections = []
        for token in self.tokens:
            if not token.id:
                continue
            annotation = self.annotations.get(cast("int", token.id))
            if not annotation:
                continue

            pos = annotation.pos
            # Only highlight articles (D), nouns (N), pronouns (R),
            # and adjectives (A)
            if pos not in ["D", "N", "R", "A", "V"]:
                continue

            number_value = annotation.number
            color = self.NUMBER_COLORS.get(number_value, self.NUMBER_COLORS[None])
            # Only highlight if not default
            if color != self.NUMBER_COLORS[None]:
                selection = self._create_token_selection(token, text, color)
                if selection:
                    extra_selections.append(selection)

        self.oe_text_edit.setExtraSelections(extra_selections)

    def _create_token_selection(
        self, token: Token, text: str, color: QColor
    ) -> QTextEdit.ExtraSelection | None:
        """
        Create an extra selection for highlighting a token's surface text.

        Args:
            token: Token to highlight
            text: The full sentence text
            color: Color to use for highlighting

        Returns:
            ExtraSelection object or None if token not found

        """
        surface = token.surface
        if not surface:
            return None

        # Find the occurrence position of this token
        token_start = self._find_token_occurrence(text, token, self.tokens)
        if token_start is None:
            return None

        # Create cursor and highlight the text
        cursor = QTextCursor(self.oe_text_edit.document())
        cursor.setPosition(token_start)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            len(surface),
        )

        # Apply highlight format
        char_format = QTextCharFormat()
        char_format.setBackground(color)

        # Create extra selection
        extra_selection = QTextEdit.ExtraSelection()
        extra_selection.cursor = cursor  # type: ignore[attr-defined]
        extra_selection.format = char_format  # type: ignore[attr-defined]

        return extra_selection

    def _clear_all_highlights(self) -> None:
        """Clear all highlighting from the text."""
        self.oe_text_edit.setExtraSelections([])

    def _clear_highlight(self) -> None:
        """
        Clear the temporary selection highlight (yellow) while preserving
        highlighting mode highlights if active.
        """
        if (
            self._current_highlight_start is None
            or self._current_highlight_length is None
        ):
            return
        # Get existing selections and filter out the selection highlight
        # (we identify it by checking if it matches our stored position)
        existing_selections = self.oe_text_edit.extraSelections()
        filtered_selections = []

        for selection in existing_selections:
            cursor = selection.cursor  # type: ignore[attr-defined]
            # Check if this is the selection highlight (yellow) by position
            if (
                cursor.position() >= self._current_highlight_start
                and cursor.position()
                <= self._current_highlight_start + self._current_highlight_length
            ):
                # This is the selection highlight, skip it
                continue
            # Keep highlighting mode selections
            filtered_selections.append(selection)

        self.oe_text_edit.setExtraSelections(filtered_selections)
        self._current_highlight_start = None
        self._current_highlight_length = None

    def _highlight_token_in_text(self, token: Token) -> None:
        """
        Highlight the corresponding token in the oe_text_edit.

        Args:
            token: Token to highlight

        """
        # Clear any existing highlight first
        self._clear_highlight()

        # Get the text from the editor
        text = self.oe_text_edit.toPlainText()
        if not text:
            return

        # Get the token surface text
        surface = token.surface
        if not surface:
            return

        # Find all occurrences of the surface text
        occurrences = []
        start = 0
        while True:
            pos = text.find(surface, start)
            if pos == -1:
                break
            occurrences.append(pos)
            start = pos + 1

        # If no occurrences found, return
        if not occurrences:
            return

        # Use order_index to determine which occurrence to highlight
        # Count how many tokens with the same surface appear before this one
        same_surface_count = 0
        for t in self.tokens:
            if t.order_index >= token.order_index:
                break
            if t.surface == surface:
                same_surface_count += 1

        # Select the occurrence at the same_surface_count index
        if same_surface_count < len(occurrences):
            highlight_pos = occurrences[same_surface_count]
        else:
            # Fallback to first occurrence if index is out of range
            highlight_pos = occurrences[0]

        # Get existing extra selections (for highlighting mode)
        existing_selections = self.oe_text_edit.extraSelections()

        # Create cursor and highlight the text using extraSelections
        cursor = QTextCursor(self.oe_text_edit.document())
        cursor.setPosition(highlight_pos)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            len(surface),
        )

        # Apply highlight format for selection (yellow, semi-transparent)
        char_format = QTextCharFormat()
        # Use a yellow background color with transparency
        char_format.setBackground(QColor(200, 200, 0, 150))

        # Use extraSelections for temporary highlighting
        selection_highlight = QTextEdit.ExtraSelection()
        selection_highlight.cursor = cursor  # type: ignore[attr-defined]
        selection_highlight.format = char_format  # type: ignore[attr-defined]

        # Combine existing selections (from highlighting mode)
        # with the selection highlight
        all_selections = [*existing_selections, selection_highlight]
        self.oe_text_edit.setExtraSelections(all_selections)

        # Store position for reference
        self._current_highlight_start = highlight_pos
        self._current_highlight_length = len(surface)

    def _highlight_token_range(self, start_index: int, end_index: int) -> None:
        """
        Highlight a range of tokens in the oe_text_edit.

        Args:
            start_index: Starting token index (inclusive)
            end_index: Ending token index (inclusive)

        """
        # Clear any existing highlight first
        self._clear_highlight()

        # Get the text from the editor
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        # Validate indices
        if start_index < 0 or end_index >= len(self.tokens) or start_index > end_index:
            return

        # Get existing extra selections (for highlighting mode)
        existing_selections = self.oe_text_edit.extraSelections()

        # Build list of token positions
        token_positions: list[tuple[int, int]] = []  # (start_pos, end_pos)
        for token_idx in range(start_index, end_index + 1):
            token = self.tokens[token_idx]
            surface = token.surface
            if not surface:
                continue

            token_start = self._find_token_occurrence(text, token, self.tokens)
            if token_start is not None:
                token_end = token_start + len(surface)
                token_positions.append((token_start, token_end))

        if not token_positions:
            return

        # Create highlights for all tokens in range
        range_highlights = []
        for token_start, token_end in token_positions:
            cursor = QTextCursor(self.oe_text_edit.document())
            cursor.setPosition(token_start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Right,
                QTextCursor.MoveMode.KeepAnchor,
                token_end - token_start,
            )

            # Apply highlight format for selection (yellow, semi-transparent)
            char_format = QTextCharFormat()
            char_format.setBackground(QColor(200, 200, 0, 150))

            selection_highlight = QTextEdit.ExtraSelection()
            selection_highlight.cursor = cursor  # type: ignore[attr-defined]
            selection_highlight.format = char_format  # type: ignore[attr-defined]
            range_highlights.append(selection_highlight)

        # Combine existing selections with range highlights
        all_selections = [*existing_selections, *range_highlights]
        self.oe_text_edit.setExtraSelections(all_selections)

        # Store range for clearing later
        if token_positions:
            first_start = token_positions[0][0]
            last_end = token_positions[-1][1]
            self._current_highlight_start = first_start
            self._current_highlight_length = last_end - first_start

    def _save_annotation(self, annotation: Annotation) -> None:
        """
        Save annotation to database.

        Args:
            annotation: Annotation to save

        """
        if not self.session:
            return

        # Check if annotation exists
        existing = Annotation.get(self.session, annotation.token_id)
        if existing:
            # Update existing annotation
            existing.pos = annotation.pos
            existing.gender = annotation.gender
            existing.number = annotation.number
            existing.case = annotation.case
            existing.declension = annotation.declension
            existing.pronoun_type = annotation.pronoun_type
            existing.pronoun_number = annotation.pronoun_number
            existing.verb_class = annotation.verb_class
            existing.verb_tense = annotation.verb_tense
            existing.verb_person = annotation.verb_person
            existing.verb_mood = annotation.verb_mood
            existing.verb_aspect = annotation.verb_aspect
            existing.verb_form = annotation.verb_form
            existing.prep_case = annotation.prep_case
            existing.uncertain = annotation.uncertain
            existing.adverb_degree = annotation.adverb_degree
            existing.adjective_inflection = annotation.adjective_inflection
            existing.adjective_degree = annotation.adjective_degree
            existing.conjunction_type = annotation.conjunction_type
            existing.alternatives_json = annotation.alternatives_json
            existing.confidence = annotation.confidence
            existing.modern_english_meaning = annotation.modern_english_meaning
            existing.root = annotation.root
            self.session.add(existing)
        else:
            # Insert new annotation
            self.session.add(annotation)

        self.session.commit()

    def _on_add_note_clicked(self) -> None:
        """
        Handle Add Note button click - open note dialog.

        """
        if not self.session or not self.sentence.id:
            return

        # Determine token range
        if self._selected_token_range:
            start_idx, end_idx = self._selected_token_range
        elif self.selected_token_index is not None:
            start_idx = self.selected_token_index
            end_idx = self.selected_token_index
        else:
            return

        # Get tokens
        if start_idx < 0 or end_idx >= len(self.tokens):
            return

        start_token = self.tokens[start_idx]
        end_token = self.tokens[end_idx]

        if not start_token.id or not end_token.id:
            return

        # Open dialog for creating new note
        dialog = NoteDialog(
            sentence=self.sentence,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
            session=self.session,
            command_manager=self.command_manager,
            parent=self,
        )
        dialog.note_saved.connect(self._on_note_saved)
        dialog.exec()

    def _on_note_saved(self, note_id: int) -> None:  # noqa: ARG002
        """
        Handle note saved signal - refresh display.

        This refreshes the notes display and re-renders the OE text with
        superscripts. Note numbers are computed dynamically based on creation
        time order, so remaining notes will be automatically renumbered after
        a deletion.

        Args:
            note_id: ID of saved/deleted note (may be deleted note ID)

        """
        if self.session:
            self.session.refresh(self.sentence)
            # Refresh notes display (will renumber notes dynamically)
            self._update_notes_display()
            # Re-render OE text with updated note numbers in superscripts
            self._render_oe_text_with_superscripts()

    def _update_notes_display(self) -> None:
        """Update notes panel display."""
        if hasattr(self, "notes_panel") and self.session:
            # Ensure notes relationship is loaded
            if self.sentence.id:
                self.session.refresh(self.sentence, ["notes"])
            self.notes_panel.update_notes(self.sentence)

    def _on_note_clicked(self, note: Note) -> None:
        """
        Handle note clicked - highlight associated tokens.

        Args:
            note: Note that was clicked

        """
        self._highlight_note_tokens(note)

    def _on_note_double_clicked(self, note: Note) -> None:
        """
        Handle note double-clicked - open edit dialog.

        Args:
            note: Note that was double-clicked

        """
        if not self.session or not note.start_token or not note.end_token:
            return

        # Open dialog for editing note
        dialog = NoteDialog(
            sentence=self.sentence,
            start_token_id=note.start_token,
            end_token_id=note.end_token,
            note=note,
            session=self.session,
            command_manager=self.command_manager,
            parent=self,
        )
        dialog.note_saved.connect(self._on_note_saved)
        dialog.exec()

    def _highlight_note_tokens(self, note: Note) -> None:
        """
        Highlight tokens associated with a note.

        Args:
            note: Note to highlight tokens for

        """
        if (
            not self.sentence
            or not self.sentence.tokens
            or not note.start_token
            or not note.end_token
        ):
            return

        # Find token indices
        start_idx = None
        end_idx = None
        for idx, token in enumerate(self.tokens):
            if token.id == note.start_token:
                start_idx = idx
            if token.id == note.end_token:
                end_idx = idx

        if start_idx is not None and end_idx is not None:
            self._highlight_token_range(start_idx, end_idx)

    def _render_oe_text_with_superscripts(self) -> None:  # noqa: PLR0912
        """
        Render OE text with note superscripts.

        Only renders superscripts when NOT in edit mode.

        """
        if self._oe_edit_mode or not self.sentence:
            return

        # Ensure notes relationship is loaded
        if self.session and self.sentence.id:
            self.session.refresh(self.sentence, ["notes"])

        # Check if notes exist (after ensuring they're loaded)
        notes_list = list(self.sentence.notes) if self.sentence.notes else []
        if not notes_list:
            # No notes, just show plain text
            self.oe_text_edit.setPlainText(self.sentence.text_oe)
            return

        # Get sorted notes by token position in sentence (earlier tokens = lower
        # numbers) Note: Numbers are computed dynamically, so if a note is
        # deleted, remaining notes are automatically renumbered in the
        # superscripts
        notes = self._sort_notes_by_position(notes_list)

        # Build mapping of token ID to note numbers (computed dynamically)
        token_to_notes: dict[int, list[int]] = {}  # token_id -> list of note numbers
        for note_idx, note in enumerate(notes, start=1):
            if note.end_token:
                if note.end_token not in token_to_notes:
                    token_to_notes[note.end_token] = []
                token_to_notes[note.end_token].append(note_idx)

        # Build HTML with tokens and superscripts
        html_parts = []
        text = self.sentence.text_oe

        # Tokenize to get token positions
        if not self.tokens:
            # Fallback to plain text if no tokens
            self.oe_text_edit.setPlainText(text)
            return

        # Build token positions map
        # Track which positions we've already used to avoid duplicates
        used_positions: set[tuple[int, int]] = set()  # (start, end) positions
        token_positions: list[tuple[int, int, int]] = []  # (start, end, token_id)

        # Sort tokens by order_index to process them in order
        sorted_tokens = sorted(self.tokens, key=lambda t: t.order_index)

        for token in sorted_tokens:
            if not token.id or not token.surface:
                continue
            token_start = self._find_token_occurrence(text, token, self.tokens)
            if token_start is not None:
                token_end = token_start + len(token.surface)
                position_key = (token_start, token_end)

                # Only add if this position hasn't been used yet
                if position_key not in used_positions:
                    token_positions.append((token_start, token_end, token.id))
                    used_positions.add(position_key)

        # Sort by position
        token_positions.sort(key=lambda x: x[0])

        # Build HTML
        last_pos = 0
        for token_start, token_end, token_id in token_positions:
            # Skip if this token overlaps with a previous one
            # (shouldn't happen, but safety check)
            if token_start < last_pos:
                # Token overlaps - skip it
                continue
            # Add text before token
            if token_start > last_pos:
                html_parts.append(self._escape_html(text[last_pos:token_start]))
            # Add token
            token_text = self._escape_html(text[token_start:token_end])
            # Add superscript if this token ends a note
            if token_id in token_to_notes:
                note_numbers = token_to_notes[token_id]
                superscripts = "".join(f"<sup>{n}</sup>" for n in note_numbers)
                html_parts.append(f"{token_text}{superscripts}")
            else:
                html_parts.append(token_text)
            last_pos = token_end

        # Add remaining text
        if last_pos < len(text):
            html_parts.append(self._escape_html(text[last_pos:]))

        # Set HTML content
        html_content = "".join(html_parts)
        self.oe_text_edit.setHtml(html_content)

    def _sort_notes_by_position(self, notes: list[Note]) -> list[Note]:
        """
        Sort notes by their position in the sentence (by start token order_index).

        Args:
            notes: List of notes to sort

        Returns:
            Sorted list of notes

        """
        if not self.tokens:
            return notes

        # Build token ID to order_index mapping
        token_id_to_order: dict[int, int] = {}
        for token in self.tokens:
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

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text

        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _on_merge_clicked(self) -> None:
        """
        Handle merge button click.

        - Queries for next sentence
        - Shows confirmation dialog
        - Executes merge command if confirmed
        - Emits signal to refresh UI
        """
        if not self.session or not self.sentence.id:
            return

        next_sentence = Sentence.get_next_sentence(
            self.session, self.sentence.project_id, self.sentence.display_order + 1
        )
        if next_sentence is None:
            QMessageBox.warning(
                self,
                "No Next Sentence",
                "There is no next sentence to merge with.",
            )
            return

        # Show confirmation dialog
        message = (
            f"Merge sentence {self.sentence.display_order} "
            f"with sentence {next_sentence.display_order}?\n\n"
            f"This will combine the Old English text, Modern English translation, "
            f"tokens, annotations, and notes from both sentences."
        )
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Confirm Merge",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        # Set custom icon
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        reply = msg_box.exec()

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Create and execute merge command
        if not self.command_manager:
            QMessageBox.warning(
                self,
                "Error",
                "Command manager not available. Cannot perform merge.",
            )
            return

        # Store before state
        before_text_oe = self.sentence.text_oe
        before_text_modern = self.sentence.text_modern

        command = MergeSentenceCommand(
            session=self.session,
            current_sentence_id=self.sentence.id,
            next_sentence_id=next_sentence.id,
            before_text_oe=before_text_oe,
            before_text_modern=before_text_modern,
        )

        if self.command_manager.execute(command):
            # Emit signal to refresh UI
            if self.sentence.id:
                self.sentence_merged.emit(self.sentence.id)
        else:
            QMessageBox.warning(
                self,
                "Merge Failed",
                "Failed to merge sentences. Please try again.",
            )

    def _on_add_sentence_before_clicked(self) -> None:
        """
        Handle Add Sentence Before button click.

        Creates a new empty sentence before the current sentence.
        """
        if not self.session or not self.sentence.id or not self.command_manager:
            return

        command = AddSentenceCommand(
            session=self.session,
            project_id=self.sentence.project_id,
            reference_sentence_id=self.sentence.id,
            position="before",
        )

        if self.command_manager.execute(command):
            if command.new_sentence_id:
                self.sentence_added.emit(command.new_sentence_id)
        else:
            QMessageBox.warning(
                self,
                "Add Sentence Failed",
                "Failed to add sentence. Please try again.",
            )

    def _on_add_sentence_after_clicked(self) -> None:
        """
        Handle Add Sentence After button click.

        Creates a new empty sentence after the current sentence.
        """
        if not self.session or not self.sentence.id or not self.command_manager:
            return

        command = AddSentenceCommand(
            session=self.session,
            project_id=self.sentence.project_id,
            reference_sentence_id=self.sentence.id,
            position="after",
        )

        if self.command_manager.execute(command):
            if command.new_sentence_id:
                self.sentence_added.emit(command.new_sentence_id)
        else:
            QMessageBox.warning(
                self,
                "Add Sentence Failed",
                "Failed to add sentence. Please try again.",
            )

    def _on_delete_clicked(self) -> None:
        """
        Handle Delete button click.

        Shows confirmation dialog and deletes the sentence if confirmed.
        """
        if not self.session or not self.sentence.id or not self.command_manager:
            return

        # Show confirmation dialog
        message = (
            f"Delete sentence {self.sentence.display_order}?\n\n"
            f"This will permanently delete the sentence, including its "
            f"Old English text, Modern English translation, tokens, "
            f"annotations, and notes. This action can be undone."
        )
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Confirm Delete",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        # Set custom icon
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        reply = msg_box.exec()

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Create and execute delete command
        command = DeleteSentenceCommand(
            session=self.session,
            sentence_id=self.sentence.id,
        )

        if self.command_manager.execute(command):
            # Emit signal to refresh UI
            if self.sentence.id:
                self.sentence_deleted.emit(self.sentence.id)
        else:
            QMessageBox.warning(
                self,
                "Delete Failed",
                "Failed to delete sentence. Please try again.",
            )

    def get_oe_text(self) -> str:
        """
        Get Old English text.

        Returns:
            Old English text string

        """
        return self.oe_text_edit.toPlainText()

    def get_translation(self) -> str:
        """
        Get Modern English translation.

        Returns:
            Translation text string

        """
        return self.translation_edit.toPlainText()

    def update_sentence(self, sentence: Sentence) -> None:
        """
        Update sentence data.

        Args:
            sentence: Updated sentence model

        """
        self.sentence = sentence
        self.sentence_number_label.setText(f"[{sentence.display_order}]")
        # If we're in edit mode, exit it first
        if self._oe_edit_mode:
            # Restore read-only state
            self.oe_text_edit.setReadOnly(True)
            # Hide Save/Cancel buttons
            self.save_oe_button.setVisible(False)
            self.cancel_edit_button.setVisible(False)
            # Show Edit OE button and Add Note button
            self.edit_oe_button.setVisible(True)
            self.add_note_button.setVisible(True)
            # Reconnect textChanged signal if it was disconnected
            with suppress(RuntimeError):
                self.oe_text_edit.textChanged.connect(self._on_oe_text_changed)
            # Reset edit mode state
            self._oe_edit_mode = False
            self._original_oe_text = None
        self.oe_text_edit.setText(sentence.text_oe)
        self.translation_edit.setPlainText(sentence.text_modern or "")

    def focus(self) -> None:
        """
        Focus this sentence card.
        """
        self.token_table.table.setFocus()
        self.token_table.select_token(0)

    def focus_translation(self) -> None:
        """
        Focus translation field.
        """
        self.translation_edit.setFocus()

    def unfocus(self) -> None:
        """
        Unfocus this sentence card.
        """
        self.token_table.table.clearFocus()
        self.token_table.select_token(0)

    def _perform_deselection(self) -> None:
        """
        Perform deselection if still pending. Called by timer after delay.
        """
        if self._pending_deselect_token_index is not None:
            # Only deselect if the token index still matches (user didn't select
            # different token)
            if self.selected_token_index == self._pending_deselect_token_index:
                self.selected_token_index = None
                self._selected_token_range = None
                self._clear_highlight()
                # Disable Add Note button when deselected
                self.add_note_button.setEnabled(False)
                # Emit signal to clear sidebar
                token = self.tokens[self._pending_deselect_token_index]
                self.token_selected_for_details.emit(token, self.sentence, self)
            self._pending_deselect_token_index = None

    def _clear_token_selection(self) -> None:
        """
        Clear token selection and highlight.
        """
        # Cancel any pending deselection timer
        if self._deselect_timer.isActive():
            self._deselect_timer.stop()
        self._pending_deselect_token_index = None
        self.selected_token_index = None
        self._clear_highlight()
        # Emit signal with None to clear sidebar (main window will handle it)
        # We'll emit with the sentence but no token to indicate clearing
        # Actually, let's emit a special signal or the main window can check
        # selected_token_index For now, the main window will check if
        # selected_token_index is None

    def _toggle_token_table(self) -> None:
        """Toggle token table visibility."""
        is_visible = self.token_table.isVisible()
        self.token_table.setVisible(not is_visible)
        self.token_table_toggle_button.setText(
            "Hide Token Table" if not is_visible else "Show Token Table"
        )
