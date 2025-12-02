"""Append OE text dialog."""

from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
)

from oeapp.models.project import Project

from .mixins import TextInputMixin

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class AppendTextDialog(TextInputMixin):
    """
    Append OE text dialog.  This gets opened when the user clicks the "Append OE
    text..." menu item from the Project menu.

    This dialog allows the user to select an input method to import Old English text
    and append it to the end of the current project.  The user can either paste in text
    or import a file.  If the user imports a file, the file path will be displayed in a
    read-only edit field.  The user can then click the "OK" button to append the text.

    Args:
        main_window: Main window instance

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 600
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize append text dialog.
        """
        super().__init__()
        self.main_window = main_window

    def build(self) -> None:
        """
        Build the append text dialog.

        This means:
        - Setting the window title
        - Setting the window geometry
        - Adding the input method selector
        - Adding the text area
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Append OE Text")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)
        self._add_input_method_selector()
        self._add_text_area()
        self._add_file_browser_widget()
        # Add stretch to push all widgets to the top
        self.layout.addStretch()

        self._add_button_box()

        # Set up text input widgets (visibility and signals)
        self._setup_text_input()

    def _add_button_box(self) -> None:
        """
        Add the button box to the dialog.  The button box will be used to accept
        or cancel the dialog.
        """
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.append_text)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def append_text(self) -> None:
        """
        Append text to the current project.
        """
        # Check that a project is open
        if not self.main_window.current_project_id:
            self.main_window.show_error(
                "No project is open. Please open a project first."
            )
            self.dialog.reject()
            return

        # Get the current project
        project = Project.get(
            self.main_window.session, self.main_window.current_project_id
        )
        if project is None:
            self.main_window.show_error("Project not found.")
            self.dialog.reject()
            return

        # Get text from input using mixin method
        try:
            text = self.get_text_from_input()
        except ValueError as e:
            self.main_window.show_error(str(e))
            return

        # Append text to project
        project.append_oe_text(self.main_window.session, text)

        # Refresh the UI by reloading the project
        self.main_window._configure_project(project)
        self.main_window.show_message("Text appended to project")
        self.dialog.close()

    def execute(self) -> None:
        """
        Execute the append text dialog.
        """
        self.build()
        self.dialog.exec()
