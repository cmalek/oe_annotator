import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class MigrationFailureDialog:
    """
    Dialog shown when migration fails during startup.
    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 700
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(
        self,
        main_window: MainWindow,
        error: Exception,
        backup_app_version: str | None,
    ) -> None:
        """
        Initialize migration failure dialog.

        Args:
            main_window: Main window instance
            error: The exception that occurred during migration
            backup_app_version: Application version from the restored backup

        """
        self.main_window = main_window
        self.error = error
        self.backup_app_version = backup_app_version

    def build(self) -> None:
        """
        Build the migration failure dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Migration Failed")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)

        # Error message
        error_label = QLabel(
            "Database migration failed during startup.\n\n"
            "Your database has been automatically restored to the backup created "
            "before the migration attempt.\n\n"
        )
        if self.backup_app_version:
            error_label.setText(
                error_label.text()
                + f"To continue working, please downgrade to application version "
                f"{self.backup_app_version}.\n\n"
                f"The restored backup was created with application version "
                f"{self.backup_app_version}."
            )
        error_label.setWordWrap(True)
        self.layout.addWidget(error_label)

        # Stack trace
        trace_label = QLabel("Stack Trace:")
        self.layout.addWidget(trace_label)

        trace_text = QTextEdit(self.dialog)
        trace_text.setReadOnly(True)
        trace_str = "".join(
            traceback.format_exception(
                type(self.error), self.error, self.error.__traceback__
            )
        )
        trace_text.setPlainText(trace_str)
        trace_text.setMinimumHeight(200)
        self.layout.addWidget(trace_text)

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("Save Stack Trace")
        save_button.clicked.connect(self.save_stack_trace)
        button_layout.addWidget(save_button)

        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_button)

        button_layout.addStretch()

        exit_button = QPushButton("Exit Application")
        exit_button.clicked.connect(self.dialog.accept)
        button_layout.addWidget(exit_button)

        self.layout.addLayout(button_layout)

    def save_stack_trace(self) -> None:
        """Save stack trace to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.dialog,
            "Save Stack Trace",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            # Format stack trace (should not fail)
            trace_str = "".join(
                traceback.format_exception(
                    type(self.error), self.error, self.error.__traceback__
                )
            )
            # Write to file - can fail with file system errors
            try:
                Path(file_path).write_text(trace_str, encoding="utf-8")
            except (OSError, PermissionError) as e:
                self.main_window.show_error(f"Failed to save stack trace: {e}")
                return

            self.main_window.show_information(
                f"Stack trace saved to:\n{file_path}", title="Saved"
            )

    def copy_to_clipboard(self) -> None:
        """Copy stack trace to clipboard."""
        clipboard = QApplication.clipboard()
        trace_str = "".join(
            traceback.format_exception(
                type(self.error), self.error, self.error.__traceback__
            )
        )
        clipboard.setText(trace_str)
        self.main_window.show_message("Stack trace copied to clipboard")

    def execute(self) -> None:
        """
        Execute the migration failure dialog.
        """
        self.build()
        self.dialog.exec()
