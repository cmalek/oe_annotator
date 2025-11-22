#!/usr/bin/env python3
"""Alembic wrapper that creates migrations and updates version/mapping files."""

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

# Get the project root directory (parent of bin/)
PROJECT_ROOT = Path(__file__).parent.parent
ETC_DIR = PROJECT_ROOT / "oeapp" / "etc"
MIGRATIONS_DIR = PROJECT_ROOT / "oeapp" / "models" / "alembic" / "versions"
MIGRATION_VERSIONS_FILE = ETC_DIR / "migration_versions.json"
FIELD_MAPPINGS_FILE = ETC_DIR / "field_mappings.json"


def run_alembic_revision(message: str) -> str | None:
    """
    Run alembic revision command and return the created migration file path.

    Args:
        message: Migration message

    Returns:
        Path to created migration file, or None if failed

    """
    alembic_ini = PROJECT_ROOT / "oeapp" / "etc" / "alembic.ini"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "revision",
            "-m",
            message,
            "--config",
            str(alembic_ini),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error running alembic revision: {result.stderr}", file=sys.stderr)
        return None

    # Extract migration file from output
    # Alembic outputs something like: "Generating /path/to/migration_file.py ... done"
    match = re.search(r"Generating\s+(.+?)\s+\.\.\.\s+done", result.stdout)
    if match:
        return match.group(1).strip()

    # Try to find the most recently created migration file
    migration_files = sorted(
        MIGRATIONS_DIR.glob("*.py"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if migration_files:
        return str(migration_files[0])

    return None


def extract_migration_revision(migration_file: str) -> str | None:
    """
    Extract revision ID from migration file.

    Args:
        migration_file: Path to migration file

    Returns:
        Revision ID, or None if not found

    """
    # Read file content
    try:
        with Path(migration_file).open("r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, PermissionError) as e:
        print(
            f"Error reading migration file {migration_file}: {e}", file=sys.stderr
        )
        return None

    # Look for revision = "..." pattern
    match = re.search(r'revision\s*:\s*str\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)

    # Try parsing as Python AST
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(
            f"Error parsing migration file {migration_file} as Python: {e}",
            file=sys.stderr,
        )
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "revision":
                    if isinstance(node.value, ast.Constant):
                        return node.value.value
                    elif isinstance(node.value, ast.Str):  # Python < 3.8
                        return node.value.s

    return None


def detect_field_renames(migration_file: str) -> dict[str, dict[str, str]]:
    """
    Detect field renames from migration file.

    Args:
        migration_file: Path to migration file

    Returns:
        Dictionary mapping model names to field renames

    """
    renames: dict[str, dict[str, str]] = {}

    # Read file content
    try:
        with Path(migration_file).open("r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, PermissionError) as e:
        print(
            f"Error reading migration file {migration_file}: {e}", file=sys.stderr
        )
        return renames

    # Look for batch_op.alter_column() calls with new_column_name parameter
    # Pattern: batch_op.alter_column("old_name", new_column_name="new_name", ...)
    pattern = r'batch_op\.alter_column\(["\']([^"\']+)["\'][^)]*new_column_name\s*=\s*["\']([^"\']+)["\']'
    matches = re.finditer(pattern, content)

    for match in matches:
        old_name = match.group(1)
        new_name = match.group(2)

        # Try to determine table/model name from context
        # Look backwards for table name in batch_alter_table
        before_match = content[: match.start()]
        table_match = re.search(
            r'batch_alter_table\(["\']([^"\']+)["\']', before_match
        )
        if table_match:
            table_name = table_match.group(1)
            # Map table name to model name (simple mapping)
            model_name = _table_to_model_name(table_name)
            if model_name not in renames:
                renames[model_name] = {}
            renames[model_name][old_name] = new_name

    return renames


def _table_to_model_name(table_name: str) -> str:
    """
    Convert table name to model name.

    Args:
        table_name: Database table name

    Returns:
        Model name

    """
    # Simple mapping: plural table names to singular model names
    # This is a basic implementation - may need refinement
    if table_name.endswith("s"):
        return table_name[:-1].capitalize()
    return table_name.capitalize()


def update_migration_versions(revision: str, min_version: str) -> None:
    """
    Update migration_versions.json with new migration.

    Ensures only one migration SHA per version (the latest one).

    Args:
        revision: Migration revision ID
        min_version: Minimum app version required

    """
    if not MIGRATION_VERSIONS_FILE.exists():
        versions = {}
    else:
        try:
            with MIGRATION_VERSIONS_FILE.open("r", encoding="utf-8") as f:
                versions = json.load(f)
        except (json.JSONDecodeError, OSError):
            versions = {}

    # Remove any existing migration SHA that maps to this version
    # (to ensure only the latest migration SHA per version)
    keys_to_remove = [
        old_revision
        for old_revision, old_version in versions.items()
        if old_version == min_version
    ]
    for key in keys_to_remove:
        del versions[key]

    # Add the new migration SHA for this version
    versions[revision] = min_version

    MIGRATION_VERSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MIGRATION_VERSIONS_FILE.open("w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)
        f.write("\n")

    if keys_to_remove:
        print(
            f"Updated {MIGRATION_VERSIONS_FILE}: Replaced {keys_to_remove} with {revision} for version {min_version}"
        )
    else:
        print(f"Updated {MIGRATION_VERSIONS_FILE} with {revision}: {min_version}")


def update_field_mappings(revision: str, renames: dict[str, dict[str, str]]) -> None:
    """
    Update field_mappings.json with detected renames.

    Args:
        revision: Migration revision ID
        renames: Dictionary mapping model names to field renames

    """
    if not FIELD_MAPPINGS_FILE.exists():
        mappings = {}
    else:
        try:
            with FIELD_MAPPINGS_FILE.open("r", encoding="utf-8") as f:
                mappings = json.load(f)
        except (json.JSONDecodeError, OSError):
            mappings = {}

    if renames:
        mappings[revision] = renames
        FIELD_MAPPINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with FIELD_MAPPINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2)
            f.write("\n")
        print(f"Updated {FIELD_MAPPINGS_FILE} with field renames for {revision}")
    else:
        print(f"No field renames detected for {revision}")


def main() -> None:
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: create_migration.py <message>", file=sys.stderr)
        print("Example: create_migration.py 'Add new field'", file=sys.stderr)
        sys.exit(1)

    message = sys.argv[1]

    # Run alembic revision
    print(f"Creating migration: {message}")
    migration_file = run_alembic_revision(message)

    if not migration_file:
        print("Failed to create migration", file=sys.stderr)
        sys.exit(1)

    print(f"Created migration file: {migration_file}")

    # Extract revision ID
    revision = extract_migration_revision(migration_file)
    if not revision:
        print("Failed to extract revision ID from migration file", file=sys.stderr)
        sys.exit(1)

    print(f"Migration revision: {revision}")

    # Prompt for minimum app version
    min_version = input("Enter minimum app version required for this migration (e.g., 0.1.0): ").strip()
    if not min_version:
        print("No version provided, skipping version update", file=sys.stderr)
    else:
        update_migration_versions(revision, min_version)

    # Detect field renames
    print("Detecting field renames...")
    renames = detect_field_renames(migration_file)

    if renames:
        print(f"Detected field renames: {renames}")
        confirm = input("Confirm these field renames? (y/n): ").strip().lower()
        if confirm == "y":
            update_field_mappings(revision, renames)
        else:
            print("Field renames not saved. You can manually update field_mappings.json")
    else:
        print("No field renames detected")
        # Still update mappings with empty dict to record this migration
        update_field_mappings(revision, {})

    print("Migration creation complete!")


if __name__ == "__main__":
    main()

