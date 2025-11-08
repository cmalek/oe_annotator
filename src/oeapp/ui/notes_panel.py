"""Notes panel UI component."""

from PySide6.QtWidgets import QWidget


class NotesPanel(QWidget):
    """Widget displaying notes panel."""

    def __init__(self, parent: QWidget | None = None):  # noqa: ARG002
        """Initialize notes panel."""
        super().__init__()
