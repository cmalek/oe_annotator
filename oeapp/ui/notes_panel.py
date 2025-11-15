"""Notes panel UI component."""

from PySide6.QtWidgets import QWidget


class NotesPanel(QWidget):
    """
    Widget displaying notes panel.

    Args:
        parent: Parent widget

    """

    def __init__(self, parent: QWidget | None = None):  # noqa: ARG002
        super().__init__()
