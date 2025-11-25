from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from oeapp.exc import AlreadyExists
from oeapp.models.project import Project

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class NewProjectDialog:
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
        self.main_window = main_window

    def browse_file(self) -> None:
        """
        Open a file dialog to select a file and update the file path edit field.

        This should be connected to the "Browse" button in _add_file_browser_widget.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.dialog,
            "Select Text File",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_path_edit.setText(file_path)

    def toggle_input_method(self, index: int) -> None:
        """
        Toggle the visibility of the text label, text edit, file label, and file
        browser widget based on the index.
        """
        if index == 0:
            self.text_label.setVisible(True)
            self.text_edit.setVisible(True)
            self.file_label.setVisible(False)
            self.file_browser_widget.setVisible(False)
        else:
            self.text_label.setVisible(False)
            self.text_edit.setVisible(False)
            self.file_label.setVisible(True)
            self.file_browser_widget.setVisible(True)

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

        # Set initial visibility of the text label, text edit, file label, and
        # file browser widget
        self.text_label.setVisible(True)
        self.text_edit.setVisible(True)
        self.file_label.setVisible(False)
        self.file_browser_widget.setVisible(False)

        # Connect the input method selector to the toggle_input_method function
        self.input_method_combo.currentIndexChanged.connect(self.toggle_input_method)

    def _add_title_edit(self) -> None:
        """
        Add the title edit to the dialog.  The title edit will be used to enter
        the project title.
        """
        self.title_edit = QLineEdit(self.dialog)
        self.title_edit.setPlaceholderText("Enter project title...")
        self.layout.addWidget(QLabel("Project Title:"))
        self.layout.addWidget(self.title_edit)

    def _add_input_method_selector(self) -> None:
        """
        Add the input method selector to the dialog.  The input method selector
        will be used to determine which input method to use.

        - Paste in text (default)
        - Import from file

        Choosing "Import from file" will show a file browser widget and a file
        path edit field, and hide the text area for pasting in text.

        Choosing "Paste in text" will show a text area for pasting in text, and
        hide the file browser widget and file path edit field.

        """
        self.input_method_combo = QComboBox(self.dialog)
        self.input_method_combo.addItems(["Paste in text", "Import from file"])
        self.layout.addWidget(QLabel("Input Method:"))
        self.layout.addWidget(self.input_method_combo)

    def _add_text_area(self) -> None:
        """
        Add the text area to the dialog.  The text area will be used to paste in text.
        """
        self.text_edit = QTextEdit(self.dialog)
        self.text_edit.setPlaceholderText("Paste Old English text here...")
        self.text_edit.setMinimumHeight(400)
        self.text_label = QLabel("Old English Text:")
        self.layout.addWidget(self.text_label)
        self.layout.addWidget(self.text_edit)

    def open_file_dialog(self) -> None:
        """
        Open a file dialog to select a file and update the file path edit field.

        The file dialog should be positioned below the file path edit field.
        """
        # Map the bottom left of file_path_edit to global coordinates
        edit_rect = self.file_path_edit.rect()
        global_point = self.file_path_edit.mapToGlobal(edit_rect.bottomLeft())
        # Create and show the QFileDialog at the desired position
        dialog = QFileDialog(self.dialog, "Select Text File")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Text Files (*.txt);;All Files (*)")
        # Position the dialog below the file_path_edit field
        dialog.move(global_point)
        if dialog.exec():
            files = dialog.selectedFiles()
            if files:
                self.selected_file_path = files[0]
                self.file_path_edit.setText(self.selected_file_path)

    def _add_file_browser_widget(self) -> None:
        """
        Add the file browser widget to the dialog.  The file browser widget will
        be used to browse the file system for a file to import.
        """
        file_browser_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit(self.dialog)
        self.file_path_edit.setPlaceholderText("No file selected...")
        self.file_path_edit.setReadOnly(True)

        browse_button = QPushButton("Browse...")
        file_browser_layout.addWidget(self.file_path_edit)
        file_browser_layout.addWidget(browse_button)

        self.file_browser_widget = QWidget(self.dialog)
        self.file_browser_widget.setLayout(file_browser_layout)
        self.file_label = QLabel("Old English Text File:")

        self.layout.addWidget(self.file_label)
        self.layout.addWidget(self.file_browser_widget)

        browse_button.clicked.connect(self.open_file_dialog)

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

        # Get text based on input method
        if self.input_method_combo.currentIndex() == 0:  # Paste in text
            text = self.text_edit.toPlainText()
        else:  # Import from file
            if not self.selected_file_path:
                self.main_window.show_error("Please select a file to import.")
                return
            text = Path(self.file_path_edit.text()).read_text(encoding="utf-8")

        if text.strip():
            try:
                self.create_project(text, title)
            except AlreadyExists:
                self.main_window.show_error(
                    f'Project with title "{title!s}" already exists. Please '
                    "choose a different title or delete the existing project."
                )
        else:
            self.main_window.show_error("Please enter or import Old English text.")
        self.dialog.close()
        self.main_window.show_message(f'Project created: "{title!s}"', duration=2000)

    def execute(self) -> None:
        """
        Execute the new project dialog.
        """
        self.build()
        if self.dialog.exec():
            self.new_project()
