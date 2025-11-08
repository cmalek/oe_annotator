"""Help dialog."""

import sys
from pathlib import Path
from typing import Final

import markdown
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


def get_resource_path(relative_path: str) -> Path:
    """
    Get resource path for bundled application or development.

    Args:
        relative_path: Relative path from project root

    Returns:
        Path to resource file

    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent.parent.parent.parent
    return base_path / relative_path


class HelpDialog(QDialog):
    """Help dialog displaying documentation."""

    #: Help topics mapping
    TOPICS: Final[dict[str, str]] = {
        "Keybindings": "keybindings.md",
        "Annotation Guide": "annotation-guide.md",
        "Incremental Annotation": "incremental-annotation.md",
        "Export Formatting": "export-formatting.md",
        "Morphological Reference": "morphological-reference.md",
        "Troubleshooting": "troubleshooting.md",
    }

    def __init__(self, topic: str | None = None, parent: QWidget | None = None) -> None:
        """
        Initialize help dialog.

        Keyword Args:
            topic: Optional topic to display initially
            parent: Parent widget

        """
        super().__init__(parent)
        self.help_dir = get_resource_path("help")
        self._setup_ui()
        if topic and topic in self.TOPICS:
            self._load_topic(topic)
        else:
            self._load_topic("Keybindings")

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        self.setWindowTitle("Old English Annotator - Help")
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumSize(QSize(800, 600))

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Help Documentation")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        # Splitter for topic list and content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Topic list (left sidebar)
        self.topic_list = QListWidget()
        self.topic_list.addItems(list(self.TOPICS.keys()))
        self.topic_list.setMaximumWidth(200)
        self.topic_list.currentItemChanged.connect(self._on_topic_changed)
        splitter.addWidget(self.topic_list)

        # Content area (right side)
        self.content_view = QTextBrowser()
        self.content_view.setOpenExternalLinks(True)
        splitter.addWidget(self.content_view)

        # Set splitter proportions
        splitter.setSizes([200, 700])

        # Select first topic
        self.topic_list.setCurrentRow(0)

    def _on_topic_changed(
        self,
        current: QListWidgetItem,
        previous: QListWidgetItem,  # noqa: ARG002
    ) -> None:
        """
        Handle topic selection change.

        Args:
            current: The current topic item
            previous: The previous topic item

        """
        if current:
            topic_name = current.text()
            self._load_topic(topic_name)

    def _load_topic(self, topic_name: str) -> None:
        """
        Load and display a help topic.  This means:

        - Loading the topic from the file system
        - Converting the markdown to HTML
        - Displaying the HTML in the content view
        - Adding basic styling to the HTML
        - Handling errors that may occur

        Args:
            topic_name: Name of the topic to load

        """
        if topic_name not in self.TOPICS:
            return

        filename = self.TOPICS[topic_name]
        filepath = self.help_dir / filename

        if not filepath.exists():
            self.content_view.setHtml(
                f"<h1>Error</h1><p>Help file not found: {filename}</p>"
            )
            return

        try:
            # Read markdown file
            with Path(filepath).open(encoding="utf-8") as f:
                markdown_content = f.read()

            # Convert markdown to HTML.  Note that codehilite is part of markdown
            # and is enabled when the pygments package is installed.
            extensions = ["tables", "fenced_code", "codehilite"]
            html = markdown.markdown(
                markdown_content,
                extensions=extensions,
            )

            # Add basic styling
            styled_html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                        line-height: 1.6;
                        padding: 20px;
                        max-width: 800px;
                    }}
                    h1 {{
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        color: #34495e;
                        margin-top: 30px;
                    }}
                    h3 {{
                        color: #7f8c8d;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 20px 0;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #3498db;
                        color: white;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f2f2f2;
                    }}
                    code {{
                        background-color: #f4f4f4;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: "Courier New", monospace;
                    }}
                    pre {{
                        background-color: #f4f4f4;
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                    ul, ol {{
                        margin: 10px 0;
                        padding-left: 30px;
                    }}
                    strong {{
                        color: #2c3e50;
                    }}
                </style>
            </head>
            <body>
                {html}
            </body>
            </html>
            """  # noqa: E501

            self.content_view.setHtml(styled_html)

        except Exception as e:
            self.content_view.setHtml(
                f"<h1>Error</h1><p>Failed to load help content: {e!s}</p>"
            )

    def show_topic(self, topic_name: str):
        """
        Show a specific topic in the help dialog. This means:

        - Finding the topic in the list
        - Selecting the topic
        - Loading the topic

        Args:
            topic_name: Name of the topic to show

        """
        if topic_name in self.TOPICS:
            # Find and select the topic in the list
            items = self.topic_list.findItems(topic_name, Qt.MatchFlag.MatchExactly)
            if items:
                self.topic_list.setCurrentItem(items[0])
                self._load_topic(topic_name)
