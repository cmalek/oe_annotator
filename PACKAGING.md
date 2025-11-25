# Packaging Guide

This guide explains how to package the Ænglisc Toolkit application for distribution.

## Prerequisites

- Python 3.14+ installed
- Virtual environment activated
- PyInstaller installed (`pip install pyinstaller`)

## Resources Included

The following resources are automatically included in the packaged application:

- `help/` - Help documentation markdown files
- `src/oeapp/themes/` - Application themes (if any)

## Building for macOS

1. Ensure you're in the project root directory
2. Activate your virtual environment: `source .venv/bin/activate`
3. Run the build script: `./build_macos.sh`
4. The application will be created in `dist/oe_annotator.app`

### Creating a DMG (Optional)

To create a distributable DMG file:

```bash
# Install create-dmg
brew install create-dmg

# Create DMG
create-dmg --volname "Ænglisc Toolkit" \
           --window-pos 200 120 \
           --window-size 800 400 \
           --icon-size 100 \
           --icon "oe_annotator.app" 200 190 \
           --hide-extension "oe_annotator.app" \
           --app-drop-link 600 185 \
           dist/oe_annotator.dmg \
           dist/
```

## Building for Windows

1. Ensure you're in the project root directory
2. Activate your virtual environment: `.venv\Scripts\activate`
3. Run the build script: `build_windows.bat`
4. The executable will be created in `dist\oe_annotator.exe`

## Customizing the Build

### Modifying the Spec File

The `oe_annotator.spec` file controls the build process. You can:

- Add an icon: Set `icon='path/to/icon.ico'` (Windows) or `icon='path/to/icon.icns'` (macOS)
- Enable console output: Set `console=True` for debugging
- Add additional data files: Add entries to the `datas` list
- Add hidden imports: Add module names to `hiddenimports`

### Rebuilding

After modifying the spec file, rebuild with:

```bash
pyinstaller oe_annotator.spec --clean
```

## Troubleshooting

### Application Doesn't Start

- Try building with `console=True` in the spec file to see error messages
- Check that all dependencies are included in `hiddenimports`
- Verify that resource paths use `sys._MEIPASS` for bundled applications

### Missing Resources

- Ensure all resources are listed in the `datas` section of the spec file
- Check that resource loading code uses `get_resource_path()` helper function

### Large Executable Size

- PySide6 applications are typically 100-200MB
- Consider using `--onefile` for a single executable (slower startup)
- Or use `--onedir` (default) for faster startup with multiple files

## Distribution

- macOS: Distribute the `.app` bundle or a `.dmg` file
- Windows: Distribute the `.exe` file or create an installer using tools like Inno Setup or NSIS
