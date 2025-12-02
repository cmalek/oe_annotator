"""Mixin for text input dialogs with paste text or file import options."""

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)


class TextInputMixin:
    """
    Mixin providing shared text input functionality for dialogs.

    This mixin provides UI components and logic for dialogs that allow users to
    input Old English text either by pasting it directly or importing it from a file.

    Classes using this mixin should:
    - Have a `dialog` attribute (QDialog instance)
    - Have a `layout` attribute (QVBoxLayout instance)
    - Have a `main_window` attribute (MainWindow instance)
    - Call the mixin's `_add_*` methods in their `build()` method
    - Call `self._setup_text_input()` after adding all widgets to set up initial state
    """

    def __init__(self) -> None:
        """Initialize the mixin."""
        #: Selected file path for file import (None if not selected)
        self.selected_file_path: str | None = None

    def _add_input_method_selector(self) -> None:
        """
        Add the input method selector to the dialog.

        The input method selector will be used to determine which input method to use:
        - Paste in text (default)
        - Import from file

        Choosing "Import from file" will show a file browser widget and a file
        path edit field, and hide the text area for pasting in text.

        Choosing "Paste in text" will show a text area for pasting in text, and
        hide the file browser widget and file path edit field.
        """
        self.input_method_combo = QComboBox(self.dialog)  # type: ignore[attr-defined]
        self.input_method_combo.addItems(["Paste in text", "Import from file"])
        self.layout.addWidget(QLabel("Input Method:"))  # type: ignore[attr-defined]
        self.layout.addWidget(self.input_method_combo)  # type: ignore[attr-defined]

    def _add_text_area(self) -> None:
        """
        Add the text area to the dialog.

        The text area will be used to paste in text.
        """
        self.text_edit = QTextEdit(self.dialog)  # type: ignore[attr-defined]
        self.text_edit.setPlaceholderText("Paste Old English text here...")
        self.text_edit.setMinimumHeight(400)
        self.text_label = QLabel("Old English Text:")
        self.layout.addWidget(self.text_label)  # type: ignore[attr-defined]
        self.layout.addWidget(self.text_edit)  # type: ignore[attr-defined]

    def _add_file_browser_widget(self) -> None:
        """
        Add the file browser widget to the dialog.

        The file browser widget will be used to browse the file system for a
        file to import.
        """
        file_browser_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit(self.dialog)  # type: ignore[attr-defined]
        self.file_path_edit.setPlaceholderText("No file selected...")
        self.file_path_edit.setReadOnly(True)

        browse_button = QPushButton("Browse...")
        file_browser_layout.addWidget(self.file_path_edit)
        file_browser_layout.addWidget(browse_button)

        self.file_browser_widget = QWidget(self.dialog)  # type: ignore[attr-defined]
        self.file_browser_widget.setLayout(file_browser_layout)
        self.file_label = QLabel("Old English Text File:")

        self.layout.addWidget(self.file_label)  # type: ignore[attr-defined]
        self.layout.addWidget(self.file_browser_widget)  # type: ignore[attr-defined]

        browse_button.clicked.connect(self.open_file_dialog)

    def toggle_input_method(self, index: int) -> None:
        """
        Toggle the visibility of the text label, text edit, file label, and file
        browser widget based on the index.

        Args:
            index: Combo box index (0 for paste text, 1 for import file)

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

    def open_file_dialog(self) -> None:
        """
        Open a file dialog to select a file and update the file path edit field.

        The file dialog should be positioned below the file path edit field.
        """
        # Map the bottom left of file_path_edit to global coordinates
        edit_rect = self.file_path_edit.rect()
        global_point = self.file_path_edit.mapToGlobal(edit_rect.bottomLeft())
        # Create and show the QFileDialog at the desired position
        dialog = QFileDialog(self.dialog, "Select Text File")  # type: ignore[attr-defined]
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Text Files (*.txt);;All Files (*)")
        # Position the dialog below the file_path_edit field
        dialog.move(global_point)
        if dialog.exec():
            files = dialog.selectedFiles()
            if files:
                self.selected_file_path = files[0]
                self.file_path_edit.setText(self.selected_file_path)

    def get_text_from_input(self) -> str:
        """
        Get text from the input method (either pasted text or selected file).

        Returns:
            The text content from either the text edit or the selected file

        Raises:
            ValueError: If no text is provided or file selection is invalid

        """
        # Get text based on input method
        if self.input_method_combo.currentIndex() == 0:  # Paste in text
            text = self.text_edit.toPlainText()
        else:  # Import from file
            if not self.selected_file_path:
                msg = "Please select a file to import."
                raise ValueError(msg)
            text = Path(self.file_path_edit.text()).read_text(encoding="utf-8")

        if not text.strip():
            msg = "Please enter or import Old English text."
            raise ValueError(msg)

        return text

    def _setup_text_input(self) -> None:
        """
        Set up initial visibility state and connect signals for text input widgets.

        This should be called after all widgets are added to the dialog.
        """
        # Set initial visibility of the text label, text edit, file label, and
        # file browser widget
        self.text_label.setVisible(True)
        self.text_edit.setVisible(True)
        self.file_label.setVisible(False)
        self.file_browser_widget.setVisible(False)

        # Connect the input method selector to the toggle_input_method function
        self.input_method_combo.currentIndexChanged.connect(self.toggle_input_method)
