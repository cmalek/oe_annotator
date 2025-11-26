"""Note dialog for adding/editing notes."""

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from oeapp.db import get_session
from oeapp.models.note import Note
from oeapp.services.commands import AddNoteCommand, DeleteNoteCommand, UpdateNoteCommand

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from oeapp.models.sentence import Sentence
    from oeapp.services.commands import CommandManager


class NoteDialog(QDialog):
    """
    Dialog for adding or editing notes.

    Args:
        sentence: Sentence the note belongs to
        start_token_id: Start token ID for the note
        end_token_id: End token ID for the note
        note: Existing note (if editing), None if creating new
        session: SQLAlchemy session (optional, will create if not provided)
        command_manager: Command manager for undo/redo (optional)

    """

    note_saved = Signal(int)  # Emits note_id when saved

    def __init__(  # noqa: PLR0913
        self,
        sentence: Sentence,
        start_token_id: int,
        end_token_id: int,
        note: Note | None = None,
        session: Session | None = None,
        command_manager: CommandManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize note dialog.
        """
        super().__init__(parent)
        self.sentence = sentence
        self.start_token_id = start_token_id
        self.end_token_id = end_token_id
        self.note = note
        self.is_editing = note is not None
        self.session = session
        self.command_manager = command_manager
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        if self.is_editing:
            self.setWindowTitle("Edit Note")
        else:
            self.setWindowTitle("Add Note")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # Token range display
        token_range_label = QLabel("Selected tokens:")
        token_range_label.setFont(QFont("Helvetica", 16))
        layout.addWidget(token_range_label)

        # Get token text for display
        token_text = self._get_token_range_text()
        token_display = QLabel(f'<i>"{token_text}"</i>')
        token_display.setFont(QFont("Helvetica", 16))
        token_display.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(token_display)

        layout.addSpacing(10)

        # Note text area
        note_label = QLabel("Note text:")
        note_label.setFont(QFont("Helvetica", 16))
        layout.addWidget(note_label)

        self.note_text_edit = QTextEdit()
        self.note_text_edit.setFont(QFont("Helvetica", 16))
        self.note_text_edit.setPlaceholderText("Enter your note here...")
        if self.note:
            self.note_text_edit.setPlainText(self.note.note_text_md)
        layout.addWidget(self.note_text_edit)

        layout.addSpacing(10)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if self.is_editing:
            # Delete button (only when editing)
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(self._on_delete_clicked)
            button_layout.addWidget(delete_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Save")
        save_button.setDefault(True)
        save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def _get_token_range_text(self) -> str:
        """
        Get the text representation of the selected token range.

        Returns:
            String containing tokens in range

        """
        if not self.sentence.tokens:
            return ""

        # Find tokens by ID
        start_token = None
        end_token = None
        for token in self.sentence.tokens:
            if token.id == self.start_token_id:
                start_token = token
            if token.id == self.end_token_id:
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

    def _on_save_clicked(self) -> None:  # noqa: PLR0912
        """Handle Save button click."""
        note_text = self.note_text_edit.toPlainText().strip()

        if not note_text:
            # Empty note - don't save
            self.reject()
            return

        session: Session = self.session or get_session()
        command: UpdateNoteCommand | AddNoteCommand | None = None
        try:
            if self.is_editing and self.note:
                # Update existing note
                before_text = self.note.note_text_md
                # Ensure None instead of False or 0 for nullable foreign keys
                before_start = (
                    self.note.start_token if self.note.start_token is not None else None
                )
                before_end = (
                    self.note.end_token if self.note.end_token is not None else None
                )
                # Ensure None instead of False or 0 for nullable foreign keys
                after_start = (
                    self.start_token_id if self.start_token_id is not None else None
                )
                after_end = self.end_token_id if self.end_token_id is not None else None

                if self.command_manager:
                    command = UpdateNoteCommand(
                        session=session,
                        note_id=self.note.id,
                        before_text=before_text or "",
                        after_text=note_text,
                        before_start_token=before_start,
                        before_end_token=before_end,
                        after_start_token=after_start,
                        after_end_token=after_end,
                    )
                    if self.command_manager.execute(command):
                        self.note_saved.emit(self.note.id)
                        self.accept()
                        return
                else:
                    # Direct update without command manager
                    self.note.note_text_md = note_text
                    # Ensure None instead of False or 0 for nullable foreign keys
                    self.note.start_token = (
                        self.start_token_id if self.start_token_id is not None else None
                    )
                    self.note.end_token = (
                        self.end_token_id if self.end_token_id is not None else None
                    )
                    session.add(self.note)
                    session.commit()
                    self.note_saved.emit(self.note.id)
                    self.accept()
                    return
            else:
                # Create new note
                if not self.sentence.id:
                    return

                if self.command_manager:
                    command = AddNoteCommand(
                        session=session,
                        sentence_id=self.sentence.id,
                        start_token_id=self.start_token_id,
                        end_token_id=self.end_token_id,
                        note_text=note_text,
                    )
                    if self.command_manager.execute(command):
                        if command.note_id:
                            self.note_saved.emit(command.note_id)
                        self.accept()
                        return
                else:
                    # Direct creation without command manager
                    # Ensure None instead of False or 0 for nullable foreign keys
                    start_token_id = (
                        self.start_token_id if self.start_token_id is not None else None
                    )
                    end_token_id = (
                        self.end_token_id if self.end_token_id is not None else None
                    )
                    note = Note(
                        sentence_id=self.sentence.id,
                        start_token=start_token_id,
                        end_token=end_token_id,
                        note_text_md=note_text,
                        note_type="span",
                    )
                    session.add(note)
                    session.commit()
                    session.refresh(note)
                    if note.id:
                        self.note_saved.emit(note.id)
                    self.accept()
                    return
        except Exception:
            if not self.session:  # Only rollback if we created the session
                session.rollback()
            raise

    def _on_delete_clicked(self) -> None:
        """Handle Delete button click."""
        if not self.note or not self.note.id:
            return

        session: Session = self.session or get_session()
        try:
            note_id = self.note.id

            if self.command_manager:
                command = DeleteNoteCommand(
                    session=session,
                    note_id=note_id,
                )
                if self.command_manager.execute(command):
                    # Emit signal with note_id for cleanup (even though deleted)
                    self.note_saved.emit(note_id)
                    self.accept()
                    return
            else:
                # Direct deletion without command manager
                session.delete(self.note)
                session.commit()
                # Emit signal with note_id for cleanup (even though deleted)
                self.note_saved.emit(note_id)
                self.accept()
                return
        except Exception:
            if not self.session:  # Only rollback if we created the session
                session.rollback()
            raise
