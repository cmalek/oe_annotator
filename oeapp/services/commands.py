"""Command pattern for undo/redo functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from oeapp.models.annotation import Annotation
from oeapp.models.note import Note
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class Command(ABC):
    """Base class for undoable commands."""

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.

        Returns:
            True if successful, False otherwise

        """

    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command.

        Returns:
            True if successful, False otherwise

        """

    @abstractmethod
    def get_description(self) -> str:
        """
        Get human-readable description of the command.

        Returns:
            Description string

        """


@dataclass
class AnnotateTokenCommand(Command):
    """Command for annotating a token."""

    #: The SQLAlchemy session.
    session: Session
    #: The token ID.
    token_id: int
    #: The before state of the annotation.
    before: dict[str, Any]
    #: The after state of the annotation.
    after: dict[str, Any]

    def _update_annotation(self, annotation: Annotation, state: dict[str, Any]) -> None:
        """
        Update an annotation with a new state.

        This method updates an annotation with a new state.  The state is a
        dictionary of key-value pairs.  The keys are the fields of the annotation
        and the values are the new values for the fields.

        Args:
            annotation: Annotation to update
            state: New state of the annotation

        """
        annotation.pos = state.get("pos")
        annotation.gender = state.get("gender")
        annotation.number = state.get("number")
        annotation.case = state.get("case")
        annotation.declension = state.get("declension")
        annotation.pronoun_type = state.get("pronoun_type")
        annotation.verb_class = state.get("verb_class")
        annotation.verb_tense = state.get("verb_tense")
        annotation.verb_person = state.get("verb_person")
        annotation.verb_mood = state.get("verb_mood")
        annotation.verb_aspect = state.get("verb_aspect")
        annotation.verb_form = state.get("verb_form")
        annotation.prep_case = state.get("prep_case")
        annotation.uncertain = state.get("uncertain", False)
        annotation.alternatives_json = state.get("alternatives_json")
        annotation.confidence = state.get("confidence")
        annotation.modern_english_meaning = state.get("modern_english_meaning")
        annotation.root = state.get("root")
        self.session.add(annotation)
        self.session.commit()

    def execute(self) -> bool:
        """
        Execute annotation update.

        Returns:
            True if successful

        """
        annotation = Annotation.get(self.session, self.token_id)
        if annotation is None:
            # Create annotation if it doesn't exist
            annotation = Annotation(token_id=self.token_id)
            self.session.add(annotation)
            self.session.flush()
        self._update_annotation(annotation, self.after)
        return True

    def undo(self) -> bool:
        """
        Undo annotation update.

        Returns:
            True if successful

        """
        annotation = Annotation.get(self.session, self.token_id)
        if annotation is None:
            return False
        self._update_annotation(annotation, self.before)
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Annotate token {self.token_id}"


@dataclass
class EditSentenceCommand(Command):
    """Command for editing sentence text or translation."""

    #: The SQLAlchemy session.
    session: Session
    #: The sentence ID.
    sentence_id: int
    #: The field to edit.
    field: Literal["text_oe", "text_modern"]
    #: The before state of the sentence.
    before: str
    #: The after state of the sentence.
    after: str

    def execute(self) -> bool:
        """
        Execute sentence edit.

        - If the field is "text_oe", update the sentence text, and re-tokenize
          the sentence, updating the tokens in the sentence.
        - If the field is "text_modern", update the sentence translation.

        Returns:
            True if successful

        """
        sentence = Sentence.get(self.session, self.sentence_id)
        if sentence is None:
            return False

        if self.field == "text_oe":
            sentence.update(self.session, self.after)
        elif self.field == "text_modern":
            sentence.text_modern = self.after
            self.session.add(sentence)
            self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo sentence edit.

        Returns:
            True if successful, False otherwise

        """
        sentence = Sentence.get(self.session, self.sentence_id)
        if sentence is None:
            return False

        if self.field == "text_oe":
            sentence.update(self.session, self.before)
        elif self.field == "text_modern":
            sentence.text_modern = self.before
            self.session.add(sentence)
            self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Edit sentence {self.sentence_id} {self.field}"


@dataclass
class MergeSentenceCommand(Command):
    """Command for merging a sentence with the next sentence."""

    #: The SQLAlchemy session.
    session: Session
    #: The current sentence ID.
    current_sentence_id: int
    #: The next sentence ID.
    next_sentence_id: int
    #: Before state: current sentence text_oe
    before_text_oe: str
    #: Before state: current sentence text_modern
    before_text_modern: str | None
    #: Before state: next sentence data for restoration
    next_sentence_data: dict[str, Any] = field(default_factory=dict)
    #: Before state: tokens from next sentence (token_id, sentence_id,
    #: order_index, surface)
    next_sentence_tokens: list[dict[str, Any]] = field(default_factory=list)
    #: Before state: notes from next sentence
    next_sentence_notes: list[dict[str, Any]] = field(default_factory=list)
    #: Before state: display order changes (sentence_id, old_order, new_order)
    display_order_changes: list[tuple[int, int, int]] = field(default_factory=list)

    def execute(self) -> bool:
        """
        Execute merge operation.

        Returns:
            True if successful, False otherwise

        """
        current_sentence = Sentence.get(self.session, self.current_sentence_id)
        next_sentence = Sentence.get(self.session, self.next_sentence_id)

        if current_sentence is None or next_sentence is None:
            return False

        # Store next sentence data for undo
        self.next_sentence_data = {
            "id": next_sentence.id,
            "project_id": next_sentence.project_id,
            "display_order": next_sentence.display_order,
            "text_oe": next_sentence.text_oe,
            "text_modern": next_sentence.text_modern,
        }

        # Store tokens from next sentence (before moving them)
        next_tokens = list(next_sentence.tokens)
        self.next_sentence_tokens = [
            {
                "id": token.id,
                "sentence_id": token.sentence_id,
                "order_index": token.order_index,
                "surface": token.surface,
                "lemma": token.lemma,
            }
            for token in next_tokens
        ]

        # Store notes from next sentence
        next_notes = list(next_sentence.notes)
        self.next_sentence_notes = [
            {
                "id": note.id,
                "sentence_id": note.sentence_id,
                "start_token": note.start_token,
                "end_token": note.end_token,
                "note_text_md": note.note_text_md,
                "note_type": note.note_type,
            }
            for note in next_notes
        ]

        # Get current sentence token count
        current_token_count = len(current_sentence.tokens)

        # Move all tokens from next sentence to current sentence
        # CRITICAL: Update sentence_id and order_index, but keep token IDs the same
        # This preserves annotations which are linked by token_id
        for idx, token in enumerate(next_tokens):
            token.sentence_id = current_sentence.id
            token.order_index = current_token_count + idx
            self.session.add(token)

        self.session.flush()

        # Move all notes from next sentence to current sentence
        for note in next_notes:
            note.sentence_id = current_sentence.id
            self.session.add(note)

        # Merge texts
        merged_text_oe = current_sentence.text_oe + " " + next_sentence.text_oe
        current_modern = current_sentence.text_modern or ""
        next_modern = next_sentence.text_modern or ""
        merged_text_modern = (current_modern + " " + next_modern).strip() or None

        # Update current sentence text (this will re-tokenize and match existing tokens)
        current_sentence.update(self.session, merged_text_oe)
        current_sentence.text_modern = merged_text_modern
        self.session.add(current_sentence)

        # Store next sentence's display_order before deletion
        next_display_order = next_sentence.display_order
        next_project_id = next_sentence.project_id

        # Delete next sentence FIRST to avoid unique constraint violation
        # when updating display_order of subsequent sentences
        self.session.delete(next_sentence)
        self.session.flush()  # Flush to ensure deletion happens before updates

        # Update display_order for all subsequent sentences
        # Query using stored values since next_sentence is now deleted
        subsequent_sentences = Sentence.subsequent_sentences(
            self.session, next_project_id, next_display_order
        )
        for sentence in subsequent_sentences:
            old_order = sentence.display_order
            sentence.display_order -= 1
            self.display_order_changes.append(
                (sentence.id, old_order, sentence.display_order)
            )
            self.session.add(sentence)

        self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo merge operation.

        Returns:
            True if successful, False otherwise

        """
        current_sentence = Sentence.get(self.session, self.current_sentence_id)
        if current_sentence is None:
            return False

        # CRITICAL: Restore display_order for subsequent sentences FIRST
        # This must happen before recreating the next sentence to avoid
        # unique constraint violations
        # Use a two-phase approach to avoid conflicts:
        # 1. Move all sentences to temporary positions (negative values)
        # 2. Then move them to their final positions
        if self.display_order_changes:
            # Phase 1: Move to temporary positions
            temp_offset = -10000  # Use a large negative offset to avoid conflicts
            for sentence_id, _old_order, _new_order in self.display_order_changes:
                sentence = Sentence.get(self.session, sentence_id)
                if sentence:
                    sentence.display_order = temp_offset
                    temp_offset -= 1
                    self.session.add(sentence)
            self.session.flush()

            # Phase 2: Move to final positions (process in reverse order)
            sorted_changes = sorted(
                self.display_order_changes, key=lambda x: x[1], reverse=True
            )  # Sort by old_order descending
            for sentence_id, old_order, _new_order in sorted_changes:
                sentence = Sentence.get(self.session, sentence_id)
                if sentence:
                    sentence.display_order = old_order
                    self.session.add(sentence)
            self.session.flush()  # Ensure display_order changes are applied

        # Now recreate next sentence (will get a new ID, which is fine)
        next_sentence = Sentence(
            project_id=self.next_sentence_data["project_id"],
            display_order=self.next_sentence_data["display_order"],
            text_oe=self.next_sentence_data["text_oe"],
            text_modern=self.next_sentence_data["text_modern"],
        )
        self.session.add(next_sentence)
        self.session.flush()  # Get the new ID

        # Restore tokens to next sentence with original order_index
        # CRITICAL: Do this BEFORE updating current sentence text
        for token_data in self.next_sentence_tokens:
            token = Token.get(self.session, token_data["id"])
            if token:
                token.sentence_id = next_sentence.id  # Use the new sentence ID
                token.order_index = token_data["order_index"]
                self.session.add(token)

        self.session.flush()  # Ensure tokens are moved before updating current sentence

        # Now restore current sentence texts and update (re-tokenize)
        # This will only affect tokens that belong to current sentence
        current_sentence.text_oe = self.before_text_oe
        current_sentence.text_modern = self.before_text_modern
        current_sentence.update(self.session, self.before_text_oe)
        self.session.add(current_sentence)

        # Restore notes to next sentence
        for note_data in self.next_sentence_notes:
            note = self.session.get(Note, note_data["id"])
            if note:
                note.sentence_id = next_sentence.id  # Use the new sentence ID
                self.session.add(note)

        self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Merge sentence {self.current_sentence_id} with {self.next_sentence_id}"


class CommandManager:
    """Manages undo/redo command stack."""

    def __init__(self, session: Session, max_commands: int = 50) -> None:
        """
        Initialize command manager.

        Args:
            session: SQLAlchemy session

        Keyword Args:
            max_commands: Maximum number of commands to keep in memory

        """
        #: The SQLAlchemy session.
        self.session = session
        #: The maximum number of commands to keep in memory.
        self.max_commands = max_commands
        #: The undo stack.
        self.undo_stack: list[Command] = []
        #: The redo stack.
        self.redo_stack: list[Command] = []
        #: Whether a command is currently being executed.
        self._executing = False

    def execute(self, command: Command) -> bool:
        """
        Execute a command and add to undo stack.

        Args:
            command: Command to execute

        Returns:
            True if successful, False otherwise

        """
        if self._executing:
            return False

        self._executing = True
        try:
            if command.execute():
                self.undo_stack.append(command)
                # Limit stack size
                if len(self.undo_stack) > self.max_commands:
                    self.undo_stack.pop(0)
                # Clear redo stack when new action performed
                self.redo_stack.clear()
                return True
            return False
        finally:
            self._executing = False

    def undo(self) -> bool:
        """
        Undo last command.

        Returns:
            True if successful, False otherwise

        """
        if not self.undo_stack or self._executing:
            return False

        self._executing = True
        try:
            command = self.undo_stack.pop()
            if command.undo():
                self.redo_stack.append(command)
                # Limit redo stack size
                if len(self.redo_stack) > self.max_commands:
                    self.redo_stack.pop(0)
                return True
            # If undo failed, put command back
            self.undo_stack.append(command)
            return False
        finally:
            self._executing = False

    def redo(self) -> bool:
        """
        Redo last undone command.

        Returns:
            True if successful, False otherwise

        """
        if not self.redo_stack or self._executing:
            return False

        self._executing = True
        try:
            command = self.redo_stack.pop()
            if command.execute():
                self.undo_stack.append(command)
                # Limit stack size
                if len(self.undo_stack) > self.max_commands:
                    self.undo_stack.pop(0)
                return True
            # If redo failed, put command back
            self.redo_stack.append(command)
            return False
        finally:
            self._executing = False

    def can_undo(self) -> bool:
        """
        Check if undo is possible.

        Returns:
            True if undo is available

        """
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """
        Check if redo is possible.

        Returns:
            True if redo is available

        """
        return len(self.redo_stack) > 0

    def clear(self) -> None:
        """Clear all command stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()


@dataclass
class AddNoteCommand(Command):
    """Command for adding a note."""

    #: The SQLAlchemy session.
    session: Session
    #: The sentence ID.
    sentence_id: int
    #: The start token ID.
    start_token_id: int
    #: The end token ID.
    end_token_id: int
    #: The note text.
    note_text: str
    #: The note number (computed).
    note_number: int | None = None
    #: The created note ID (set after execution).
    note_id: int | None = None

    def execute(self) -> bool:
        """
        Execute note creation.

        Returns:
            True if successful, False otherwise

        """
        # Get next note number
        if self.note_number is None:
            self.note_number = self._get_next_note_number()

        # Create note
        # Ensure None instead of False or 0 for nullable foreign keys
        start_token_id = (
            self.start_token_id if self.start_token_id is not None else None
        )
        end_token_id = self.end_token_id if self.end_token_id is not None else None
        note = Note(
            sentence_id=self.sentence_id,
            start_token=start_token_id,
            end_token=end_token_id,
            note_text_md=self.note_text,
            note_type="span",
        )
        self.session.add(note)
        self.session.flush()
        self.note_id = note.id

        self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo note creation.

        Returns:
            True if successful, False otherwise

        """
        if self.note_id is None:
            return False

        note = Note.get(self.session, self.note_id)
        if note is None:
            return False

        self.session.delete(note)
        self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Add note {self.note_number} to sentence {self.sentence_id}"

    def _get_next_note_number(self) -> int:
        """
        Get next note number for the sentence.

        Returns:
            Next note number

        """
        sentence = Sentence.get(self.session, self.sentence_id)
        if sentence is None:
            return 1

        notes = sentence.notes
        if not notes:
            return 1

        # Note numbers are computed dynamically based on token position,
        # not stored. This returns the count + 1, but actual numbering
        # is done by sorting notes by token position.
        return len(notes) + 1

    @staticmethod
    def get_note_number(session: Session, sentence_id: int, note_id: int) -> int:
        """
        Get note number for a note (1-based index in sentence's notes).

        Notes are numbered by their position in the sentence (by start token
        order_index), not by creation time.

        Args:
            session: SQLAlchemy session
            sentence_id: Sentence ID
            note_id: Note ID

        Returns:
            Note number (1-based)

        """
        sentence = Sentence.get(session, sentence_id)
        if sentence is None:
            return 1

        # Refresh sentence to ensure relationships are up-to-date
        session.refresh(sentence)

        # Safely access tokens relationship - convert to list to trigger lazy load
        tokens_list = list(sentence.tokens)
        if not tokens_list:
            return 1

        # Build token ID to order_index mapping
        token_id_to_order: dict[int, int] = {}
        for token in tokens_list:
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

        # Safely access notes relationship - convert to list to trigger lazy load
        notes_list = list(sentence.notes)
        notes = sorted(notes_list, key=get_note_position)
        for idx, note in enumerate(notes, start=1):
            if note.id == note_id:
                return idx
        return 1


@dataclass
class UpdateNoteCommand(Command):
    """Command for updating a note."""

    #: The SQLAlchemy session.
    session: Session
    #: The note ID.
    note_id: int
    #: The before note text.
    before_text: str
    #: The after note text.
    after_text: str
    #: The before start token ID.
    before_start_token: int | None
    #: The before end token ID.
    before_end_token: int | None
    #: The after start token ID.
    after_start_token: int | None
    #: The after end token ID.
    after_end_token: int | None

    def execute(self) -> bool:
        """
        Execute note update.

        Returns:
            True if successful, False otherwise

        """
        note = Note.get(self.session, self.note_id)
        if note is None:
            return False

        note.note_text_md = self.after_text
        # Ensure None instead of False or 0 for nullable foreign keys
        note.start_token = (
            self.after_start_token if self.after_start_token is not None else None
        )
        note.end_token = (
            self.after_end_token if self.after_end_token is not None else None
        )
        self.session.add(note)
        self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo note update.

        Returns:
            True if successful, False otherwise

        """
        note = Note.get(self.session, self.note_id)
        if note is None:
            return False

        note.note_text_md = self.before_text
        # Ensure None instead of False or 0 for nullable foreign keys
        note.start_token = (
            self.before_start_token if self.before_start_token is not None else None
        )
        note.end_token = (
            self.before_end_token if self.before_end_token is not None else None
        )
        self.session.add(note)
        self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Update note {self.note_id}"


@dataclass
class DeleteNoteCommand(Command):
    """Command for deleting a note."""

    #: The SQLAlchemy session.
    session: Session
    #: The note ID.
    note_id: int
    #: The note text (for undo).
    note_text: str = ""
    #: The start token ID (for undo).
    start_token_id: int | None = None
    #: The end token ID (for undo).
    end_token_id: int | None = None
    #: The sentence ID (for undo).
    sentence_id: int | None = None
    #: The note number (for undo).
    note_number: int | None = None

    def execute(self) -> bool:
        """
        Execute note deletion.

        Note: After deletion, remaining notes will be automatically renumbered
        when the UI refreshes, since note numbers are computed dynamically
        based on token position order (earlier tokens = lower numbers).

        Returns:
            True if successful, False otherwise

        """
        note = Note.get(self.session, self.note_id)
        if note is None:
            return False

        # Store values for undo
        self.note_text = note.note_text_md
        self.start_token_id = note.start_token
        self.end_token_id = note.end_token
        self.sentence_id = note.sentence_id
        if self.sentence_id:
            # Store note number for reference (though it's computed dynamically)
            self.note_number = AddNoteCommand.get_note_number(
                self.session, self.sentence_id, self.note_id
            )

        self.session.delete(note)
        self.session.commit()
        # Note: The UI should refresh after this command executes to renumber
        # remaining notes. This happens via the note_saved signal handler.
        return True

    def undo(self) -> bool:
        """
        Undo note deletion.

        Returns:
            True if successful, False otherwise

        """
        if (
            self.sentence_id is None
            or self.start_token_id is None
            or self.end_token_id is None
        ):
            return False

        # Recreate note
        note = Note(
            sentence_id=self.sentence_id,
            start_token=self.start_token_id,
            end_token=self.end_token_id,
            note_text_md=self.note_text,
            note_type="span",
        )
        self.session.add(note)
        self.session.commit()
        self.note_id = note.id
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Delete note {self.note_id}"
