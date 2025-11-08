# Export Formatting

## DOCX Export

The application exports annotated Old English texts to Microsoft Word (.docx) format. The export preserves both grammatical annotations and clarifying notes.

## Accessing Export

1. Press **Ctrl+E** or go to File → Export
2. Choose a save location
3. The document is generated automatically

## Document Structure

### Title

- Project name appears as the document title

### For Each Sentence

#### Sentence Number

- Format: `[N]` where N is the sentence number
- Bold text

#### Old English Text

- Italic formatting
- Annotations appear directly on words:

  - **Superscripts**: POS abbreviations, case, number, gender codes
  - **Subscripts**: Detailed morphological information (declension, verb class, etc.)

#### Modern English Translation

- Regular text (not italic)
- Appears below the Old English text

#### Blank Line

- Separates sentences for readability

#### Notes (if any)

- Clarifying notes listed separately
- Not part of the grammatical annotations

## Annotation Format

### Superscripts

- **POS abbreviations**: `pron:rel`, `n:`, `v:`, `adj:`, etc.
- **Case codes**: `nom`, `acc`, `dat`, `gen`, `inst`
- **Number codes**: `sg`, `pl`
- **Gender codes**: `m`, `f`, `n`

### Subscripts

- **Declension details**: `dat1` (dative singular), `acc1` (accusative singular)
- **Verb class**: `w1`, `w2`, `s3`, etc.
- **Compact morphological tags**: Detailed information in abbreviated form

### Example Format

The word "hē" might appear as:

- Base: `hē` (italic)
- Superscript: `pron:m.sg.nom`
- Subscript: `pers`

## Handling Missing Data

- Missing annotations: Displayed as "—" or omitted
- Uncertain annotations: Marked with `?`
- Alternatives: Displayed as `/` separated values (e.g., `w2 / s3`)

## Font Sizes

- Old English text: Normal size, italic
- Superscripts: 8pt
- Subscripts: 8pt
- Translation: Normal size
- Notes: Normal size

## Style Reference

The exported DOCX uses standard Word styles:

- **Title**: For project name
- **Body**: For sentence content
- **Default**: Base paragraph style

You can customize these styles in Word after export if needed.

## Tips

1. **Review before export**: Check your annotations are complete
2. **Use notes**: Add clarifying notes for complex constructions
3. **Mark uncertainty**: Use the uncertain flag for questionable annotations
4. **Consistent formatting**: The export maintains consistent formatting across all sentences
