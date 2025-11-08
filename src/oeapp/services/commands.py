"""Command pattern for undo/redo functionality."""

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.oeapp.services.db import Database


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

    #: The database connection.
    db: Database
    #: The token ID.
    token_id: int
    #: The before state of the annotation.
    before: dict[str, str | int | bool | None]
    #: The after state of the annotation.
    after: dict[str, str | int | bool | None]

    def execute(self) -> bool:
        """
        Execute annotation update.

        Returns:
            True if successful, False otherwise

        """
        try:
            cursor = self.db.conn.cursor()
            # Check if annotation exists
            cursor.execute(
                "SELECT token_id FROM annotations WHERE token_id = ?", (self.token_id,)
            )
            exists = cursor.fetchone()

            if exists:
                # Update existing annotation
                cursor.execute(
                    """
                    UPDATE annotations SET
                        pos = ?, gender = ?, number = ?, "case" = ?, declension = ?,
                        pronoun_type = ?, verb_class = ?, verb_tense = ?, verb_person = ?,
                        verb_mood = ?, verb_aspect = ?, verb_form = ?, prep_case = ?,
                        uncertain = ?, alternatives_json = ?, confidence = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE token_id = ?
                """,  # noqa: E501
                    (
                        self.after.get("pos"),
                        self.after.get("gender"),
                        self.after.get("number"),
                        self.after.get("case"),
                        self.after.get("declension"),
                        self.after.get("pronoun_type"),
                        self.after.get("verb_class"),
                        self.after.get("verb_tense"),
                        self.after.get("verb_person"),
                        self.after.get("verb_mood"),
                        self.after.get("verb_aspect"),
                        self.after.get("verb_form"),
                        self.after.get("prep_case"),
                        self.after.get("uncertain", False),
                        self.after.get("alternatives_json"),
                        self.after.get("confidence"),
                        self.token_id,
                    ),
                )
            else:
                # Insert new annotation
                cursor.execute(
                    """
                    INSERT INTO annotations (
                        token_id, pos, gender, number, "case", declension,
                        pronoun_type, verb_class, verb_tense, verb_person,
                        verb_mood, verb_aspect, verb_form, prep_case,
                        uncertain, alternatives_json, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.token_id,
                        self.after.get("pos"),
                        self.after.get("gender"),
                        self.after.get("number"),
                        self.after.get("case"),
                        self.after.get("declension"),
                        self.after.get("pronoun_type"),
                        self.after.get("verb_class"),
                        self.after.get("verb_tense"),
                        self.after.get("verb_person"),
                        self.after.get("verb_mood"),
                        self.after.get("verb_aspect"),
                        self.after.get("verb_form"),
                        self.after.get("prep_case"),
                        self.after.get("uncertain", False),
                        self.after.get("alternatives_json"),
                        self.after.get("confidence"),
                    ),
                )
            self.db.conn.commit()
        except sqlite3.Error as e:
            print(f"Error executing AnnotateTokenCommand: {e}")
            return False
        else:
            return True

    def undo(self) -> bool:
        """
        Undo annotation update.
        """
        try:
            cursor = self.db.conn.cursor()
            # If before state is empty, delete annotation
            if not any(v for v in self.before.values() if v is not None):
                cursor.execute(
                    "DELETE FROM annotations WHERE token_id = ?", (self.token_id,)
                )
            else:
                # Update to before state
                cursor.execute(
                    """
                    UPDATE annotations SET
                        pos = ?, gender = ?, number = ?, "case" = ?, declension = ?,
                        pronoun_type = ?, verb_class = ?, verb_tense = ?, verb_person = ?,
                        verb_mood = ?, verb_aspect = ?, verb_form = ?, prep_case = ?,
                        uncertain = ?, alternatives_json = ?, confidence = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE token_id = ?
                """,  # noqa: E501
                    (
                        self.before.get("pos"),
                        self.before.get("gender"),
                        self.before.get("number"),
                        self.before.get("case"),
                        self.before.get("declension"),
                        self.before.get("pronoun_type"),
                        self.before.get("verb_class"),
                        self.before.get("verb_tense"),
                        self.before.get("verb_person"),
                        self.before.get("verb_mood"),
                        self.before.get("verb_aspect"),
                        self.before.get("verb_form"),
                        self.before.get("prep_case"),
                        self.before.get("uncertain", False),
                        self.before.get("alternatives_json"),
                        self.before.get("confidence"),
                        self.token_id,
                    ),
                )
            self.db.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error undoing AnnotateTokenCommand: {e}")
            return False
        else:
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

    #: The database connection.
    db: Database
    #: The sentence ID.
    sentence_id: int
    #: The field to edit.
    field: str  # "text_oe" or "text_modern"
    #: The before state of the sentence.
    before: str
    #: The after state of the sentence.
    after: str

    def execute(self) -> bool:
        """
        Execute sentence edit.

        Returns:
            True if successful, False otherwise

        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                f"UPDATE sentences SET {self.field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",  # noqa: E501, S608
                (self.after, self.sentence_id),
            )
            self.db.conn.commit()
        except sqlite3.Error as e:
            print(f"Error executing EditSentenceCommand: {e}")
            return False
        else:
            return True

    def undo(self) -> bool:
        """
        Undo sentence edit.

        Returns:
            True if successful, False otherwise

        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                f"UPDATE sentences SET {self.field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",  # noqa: E501, S608
                (self.before, self.sentence_id),
            )
            self.db.conn.commit()
        except sqlite3.Error as e:
            print(f"Error undoing EditSentenceCommand: {e}")
            return False
        else:
            return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Edit sentence {self.sentence_id} {self.field}"


class CommandManager:
    """Manages undo/redo command stack."""

    def __init__(self, db: Database, max_commands: int = 50) -> None:
        """
        Initialize command manager.

        Args:
            db: Database connection

        Keyword Args:
            max_commands: Maximum number of commands to keep in memory

        """
        #: The database connection.
        self.db = db
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
