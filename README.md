# Ænglisc Toolkit

A desktop application to assist in translation from Old English/Anglo Saxon to Modern English.

## Features

- Annotate Old English texts with grammatical, morphological, and syntactic tags
- Keyboard-driven annotation workflow with prompt-based modal interface
- Incremental refinement of annotations
- Export to DOCX format with formatted annotations
- Notes system for clarifying information
- Autosave and undo/redo support
- Filter and search annotations

## Installation

### Development

```bash
# Install dependencies
uv sync

# Run the application
python -m oeapp.main
```

### Building Standalone Applications

#### macOS

```bash
# Install PyInstaller (if not already installed)
pip install pyinstaller

# Build the application
./build_macos.sh

# The app will be created in dist/Ænglisc Toolkit.app
```

#### Windows

```cmd
REM Install PyInstaller (if not already installed)
pip install pyinstaller

REM Build the application
build_windows.bat

REM The executable will be created in dist\Ænglisc Toolkit.exe
```

## Development

This project uses:

- Python 3.14+
- PySide6 for the GUI
- SQLite for data storage
- python-docx for export functionality
- PyInstaller for packaging

## License

[To be determined]