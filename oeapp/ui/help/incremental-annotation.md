# Incremental Annotation

## Philosophy

Old English annotation is an iterative process. You don't need to annotate everything perfectly on the first try. The system supports incremental refinement of your annotations.

## Workflow

### Step 1: Basic POS Tagging

Start by identifying the Part of Speech for each token:

- Press **A** on a token
- Select POS (N, V, A, etc.)
- Press **Enter** to apply

### Step 2: Add Grammatical Features

Later, return to tokens and add morphological details:

- Select the token again
- Press **A**
- The modal remembers your previous POS selection
- Add gender, number, case, etc.
- Press **Enter** to update

### Step 3: Refinement

Continue refining as you work:

- Add verb class, tense, mood
- Specify declension types
- Include preposition cases

## Partial Annotations

All annotation fields are optional. You can:

- Leave fields empty if unknown
- Fill in only what you're certain about
- Add more details later

## Uncertain Annotations

Use the **Uncertain** checkbox when you're not confident about an annotation:

- Marks the annotation with a `?` in exports
- Helps identify areas needing review
- Can be toggled off later when confident

## Alternatives

Use the **Alternatives** field to record multiple possible interpretations:

- Example: `w2 / s3` (Weak Class II or Strong Class III)
- Displayed as `/` separated values in exports
- Useful for ambiguous forms

## Confidence Levels

Set a confidence percentage (0-100):

- Helps track annotation quality
- Useful for statistical analysis
- Can filter by confidence level later

## TODO Markers

Use the **TODO** checkbox to mark annotations needing further work:

- Helps track incomplete annotations
- Can filter to show only TODO items
- Useful for project management

## Best Practices

1. **Start broad**: Begin with POS tags across the entire text
2. **Work systematically**: Process one sentence at a time
3. **Refine incrementally**: Add details as you become more familiar with the text
4. **Use uncertainty**: Mark uncertain annotations rather than guessing
5. **Review regularly**: Periodically review and refine your annotations

## Keyboard Efficiency

The annotation modal remembers your last-used values for each POS type:

- First noun: Fill in all fields
- Subsequent nouns: Previous values are restored automatically
- Adjust only what differs
- Press **Enter** to apply quickly

This makes annotating similar tokens much faster!
