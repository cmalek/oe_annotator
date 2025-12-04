#!/bin/bash
# Build script for macOS

set -e

echo "Building Ænglisc Toolkit for macOS..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install PyInstaller if not already installed
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec 2>/dev/null || true

# Build the application
echo "Building application..."
pyinstaller aenglisc_toolkit.spec

# Create macOS app bundle
if [ -d "dist/Ænglisc Toolkit.app" ]; then
    echo "Application built successfully!"
    echo "Location: dist/Ænglisc Toolkit.app"
    echo ""
    echo "To create a DMG, install create-dmg:"
    echo "  brew install create-dmg"
    echo "  create-dmg --volname 'Ænglisc Toolkit' dist/Ænglisc Toolkit.dmg dist/"
else
    echo "Build failed - Ænglisc Toolkit.app not found"
    exit 1
fi

