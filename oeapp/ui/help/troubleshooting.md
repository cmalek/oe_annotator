# Troubleshooting

## Common Issues and Solutions

### Database Issues

**Problem**: "Database locked" error

- **Solution**: Close other instances of the application. The database uses SQLite WAL mode for concurrent access, but multiple instances can conflict.

**Problem**: Data not saving

- **Solution**: Check that autosave is working (changes save automatically after 500ms). Try using File → Save (Ctrl+S) to force an immediate save.

**Problem**: Can't open project file

- **Solution**: Ensure the project file (.db) isn't corrupted. Check file permissions.

### Annotation Issues

**Problem**: Annotation modal not opening

- **Solution**: Ensure a token is selected in the token table. Press **A** when a token row is highlighted.

**Problem**: Annotation fields not appearing

- **Solution**: Select a Part of Speech first. Fields are dynamically generated based on POS selection.

**Problem**: Previous annotation values not restoring

- **Solution**: The system remembers values per POS type. If you change POS, previous values for that POS type should restore. Try selecting the same POS again.

### Export Issues

**Problem**: DOCX export fails

- **Solution**: Ensure `python-docx` is installed. Check file permissions on the save location. Try a different save location.

**Problem**: Annotations not appearing in export

- **Solution**: Ensure annotations are actually applied (not just entered in modal). Check that you clicked Apply or pressed Enter.

**Problem**: Formatting looks wrong in Word

- **Solution**: Open the exported file in Word. Word may need to apply styles. The document uses standard Word styles that should render correctly.

### UI Issues

**Problem**: Keyboard shortcuts not working

- **Solution**: Ensure the correct widget has focus. Some shortcuts only work when specific widgets are focused:

    - J/K: Work globally
    - A: Works when token table is focused
    - Arrow keys: Work when token table is focused

**Problem**: Can't navigate between sentences

- **Solution**: Ensure a sentence card or token table has focus. Try clicking on a token table first.

**Problem**: Translation field not focusing

- **Solution**: Press **T** when a sentence card is active. Ensure the sentence has a translation field.

### Performance Issues

**Problem**: Application is slow

- **Solution**: Large projects may be slow. Consider:

    - Reducing the number of sentences loaded at once (future feature)
    - Checking database file size
    - Ensuring autosave delay isn't too short

**Problem**: Memory usage high

- **Solution**: The application loads all sentences into memory. For very large texts, consider splitting into multiple projects.

## Getting Help

### Check Documentation

1. Press **F1** to open the help dialog
2. Browse topics in the help system
3. Refer to the keyboard shortcuts guide

### Common Workflows

**Starting a new project:**

1. File → New Project
2. Paste Old English text
3. Click Create
4. Sentences are automatically tokenized

**Annotating a token:**

1. Use arrow keys to select a token
2. Press **A**
3. Select POS (use keyboard shortcuts: N, V, A, etc.)
4. Fill in fields
5. Press **Enter** to apply

**Navigating:**

- **J** = Next sentence
- **K** = Previous sentence
- **→** = Next token
- **←** = Previous token

**Undoing changes:**

- **Ctrl+Z** = Undo
- **Ctrl+R** = Redo
- **Ctrl+Shift+R** = Redo

## Reporting Issues

If you encounter bugs or issues:

1. Note the exact steps to reproduce
2. Check if the issue persists after restarting
3. Check the database file for corruption
4. Report with:

   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - System information (OS, Python version)

## Tips for Success

1. **Save regularly**: Although autosave is enabled, use Ctrl+S for important milestones
2. **Use keyboard shortcuts**: Much faster than mouse clicking
3. **Work incrementally**: Don't try to annotate everything perfectly on first pass
4. **Use uncertainty flags**: Mark uncertain annotations rather than guessing
5. **Review exports**: Regularly export and review DOCX files to catch annotation errors
