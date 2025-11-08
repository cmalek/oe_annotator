"""Main entry point for Old English Annotator application."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from src.oeapp.ui.main_window import MainWindow


def get_resource_path(relative_path: str) -> Path:
    """
    Get resource path for bundled application or development.

    Args:
        relative_path: Relative path from project root

    Returns:
        Path to resource file

    """
    if getattr(sys, "frozen", False):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent.parent.parent.parent
    return base_path / relative_path


def main():
    """
    Run the Old English Annotator application.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Old English Annotator")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
