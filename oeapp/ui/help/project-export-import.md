# Project Export/Import

## Overview

The Ænglisc Toolkit allows you to export and import entire projects in JSON format. This is useful for:

- Sharing projects with others
- Creating backups of your work
- Moving projects between computers
- Archiving completed projects

## Two Types of Export

The application offers two different export options:

### DOCX Export (File Menu)

- **Location**: File → Export... (or **Ctrl+E**)
- **Format**: Microsoft Word document (.docx)
- **Purpose**: Creating formatted documents for reading, printing, or sharing
- **Content**: Formatted text with annotations displayed as superscripts/subscripts
- **Use when**: You want a readable document with your annotations

### JSON Export (Project Menu)

- **Location**: Project → Export...
- **Format**: JSON file (.json)
- **Purpose**: Complete project backup, sharing, or migration
- **Content**: All project data including sentences, tokens, annotations, and notes
- **Use when**: You want to backup, share, or move the entire project

## Exporting a Project

### Step-by-Step Instructions

1. Open the project you want to export
2. Go to **Project → Export...**
3. Choose a location to save the file
4. The default filename is based on your project name (e.g., `my_project.json`)
5. Click **Save**

The export includes:

- Project name and metadata
- All sentences in order
- All tokens for each sentence
- All annotations (POS, grammatical features, metadata)
- All notes attached to sentences
- Migration version information

### Export File Format

The exported JSON file contains:

- **export_version**: Version of the export format
- **migration_version**: Database schema version
- **project**: Project information (name, dates, etc.)
- **sentences**: Array of all sentences with their tokens and annotations

## Importing a Project

### Step-by-Step Instructions

1. Go to **Project → Import...**
2. Select the JSON file you want to import
3. Click **Open**
4. The project will be imported into your database

### What Happens During Import

1. **Version Check**: The application checks if the export file is compatible with the current version
2. **Data Transformation**: If needed, field names are updated to match the current database structure
3. **Project Creation**: A new project is created with the imported data
4. **Name Resolution**: If a project with the same name already exists, the imported project is renamed with a number suffix (e.g., "My Project (1)")

### After Import

After importing, you'll see a dialog asking if you want to:

- **Open the imported project**: Switch to viewing the newly imported project
- **Keep current project open**: Continue working on your current project

The imported project is now available in your project list and can be opened anytime.

## Version Compatibility

The import system handles version differences automatically:

- **Same version**: Import works immediately
- **Older version**: Field mappings are applied to update the data structure
- **Incompatible version**: You'll see an error message explaining what version is required

If you see a compatibility error, you may need to:

- Upgrade the application to a newer version
- Export from the original application using a newer version
- Contact support if the versions are too far apart

## Use Cases

### Sharing Projects

1. Export your project to JSON
2. Share the JSON file with another person
3. They import it using Project → Import...
4. Both of you now have identical copies

### Creating Manual Backups

While automatic backups protect your database, you can also create manual project backups:

1. Export important projects to JSON
2. Store the JSON files in a safe location (cloud storage, external drive, etc.)
3. Import them later if needed

### Moving Between Computers

1. Export your projects on the old computer
2. Copy the JSON files to the new computer
3. Import the projects on the new computer
4. All your annotations and notes are preserved

### Archiving Completed Projects

1. Export finished projects to JSON
2. Store the JSON files in an archive folder
3. You can delete the projects from the application to save space
4. Re-import them later if you need to review or modify them

## Important Notes

- **Complete Export**: JSON export includes everything - you can't export just part of a project
- **File Size**: Large projects may create large JSON files (several MB for extensive texts)
- **No Data Loss**: All annotations, notes, and metadata are preserved in the export
- **One Project Per File**: Each JSON file contains exactly one project
- **Readable Format**: JSON files are text-based and can be opened in any text editor (though editing is not recommended)

## Troubleshooting

**Problem**: Import fails with "migration version incompatible" error

- **Solution**: Upgrade the application to the required version, or export from a newer version of the application

**Problem**: Imported project has a different name than expected

- **Solution**: This happens when a project with that name already exists. The system automatically renames it with a number suffix. You can rename it later if needed.

**Problem**: Can't find the export file

- **Solution**: Check the location where you saved it. The default location is usually your Documents folder or the last location you used.

**Problem**: Import seems to work but project is empty

- **Solution**: This shouldn't happen - contact support. The export includes all data, so if the import succeeds, all data should be present.

## Best Practices

1. **Regular Exports**: Export important projects periodically as additional backups
2. **Version Control**: Keep track of which application version created each export
3. **File Naming**: Use descriptive names when exporting (e.g., `beowulf_complete_2024-01-15.json`)
4. **Storage**: Store exported JSON files in multiple locations for safety
5. **Test Imports**: Periodically test importing your exports to ensure they work correctly

