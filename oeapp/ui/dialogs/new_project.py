from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from oeapp.exc import AlreadyExists
from oeapp.models.project import Project

from .mixins import TextInputMixin

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class NewProjectDialog(TextInputMixin):
    """
    New project dialog.  This gets opened when the user clicks the "New Project..."
    menu item from the File menu.

    This dialog allows the user to enter a project title and select an input method
    to import Old English text.  The user can either paste in text or import a file.
    If the user imports a file, the file path will be displayed in a read-only edit
    field.  The user can then click the "OK" button to create the project.

    Args:
        main_window: Main window instance

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 600
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 500

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize new project dialog.
        """
        super().__init__()
        self.main_window = main_window

    def build(self) -> None:
        """
        Build the new project dialog.

        This means:

        - Setting the window title
        - Setting the window geometry
        - Adding the title edit
        - Adding the input method selector
        - Adding the text area
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("New Project")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        self.layout = QVBoxLayout(self.dialog)
        self._add_title_edit()
        self._add_input_method_selector()
        self._add_text_area()
        self._add_file_browser_widget()
        # Add stretch to push all widgets to the top
        self.layout.addStretch()

        self._add_button_box()

        # Set up text input widgets (visibility and signals)
        self._setup_text_input()

    def _add_title_edit(self) -> None:
        """
        Add the title edit to the dialog.  The title edit will be used to enter
        the project title.
        """
        self.title_edit = QLineEdit(self.dialog)
        self.title_edit.setPlaceholderText("Enter project title...")
        self.layout.addWidget(QLabel("Project Title:"))
        self.layout.addWidget(self.title_edit)

    def _add_button_box(self) -> None:
        """
        Add the button box to the dialog.  The button box will be used to accept
        or cancel the dialog.
        """
        self.button_box = QDialogButtonBox(self.dialog)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.new_project)
        self.button_box.rejected.connect(self.dialog.reject)
        self.layout.addWidget(self.button_box)

    def create_project(self, text: str, title: str) -> None:
        """
        Create a new project from the text, split into sentences, split
        sentences into tokens, and create sentence cards.

        - If the text is empty, do nothing.
        - If the text is not empty, create a new project from the text.

        Args:
            text: Old English text to process
            title: Project title

        """
        # Create project in the shared database
        project = Project.create(self.main_window.session, text, title)
        self.main_window._configure_project(project)
        self.main_window.setWindowTitle(f"Ænglisc Toolkit - {project.name}")
        self.main_window.show_message("Project created")

    def new_project(self) -> None:
        """
        Create a new project.
        """
        title = self.title_edit.text()
        if not title.strip():
            self.main_window.show_error("Please enter a project title.")
            return

        # Get text from input using mixin method
        try:
            text = self.get_text_from_input()
        except ValueError as e:
            self.main_window.show_error(str(e))
            return

        try:
            self.create_project(text, title)
            self.dialog.close()
            self.main_window.show_message(
                f'Project created: "{title!s}"', duration=2000
            )
        except AlreadyExists:
            self.main_window.show_error(
                f'Project with title "{title!s}" already exists. Please '
                "choose a different title or delete the existing project."
            )

    def execute(self) -> None:
        """
        Execute the new project dialog.
        """
        self.build()
        if self.dialog.exec():
            self.new_project()
