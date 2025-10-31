# Keyword Rule

## Overview

The Keyword rule grades answers based on the presence of specific keywords or phrases. It's ideal for open-ended questions where you want to verify that students mention certain concepts without requiring exact phrasing.

## Use Cases

- **Essay Questions**: Check for key concepts in longer responses
- **Short Answer**: Verify important terms are mentioned
- **Concept Checks**: Award points for each concept discussed
- **Partial Credit**: Give credit for mentioning some but not all required points

## Features

- **Required Keywords**: Must be present for full credit
- **Optional Keywords**: Bonus points for additional concepts
- **Flexible Point Values**: Different points for required vs. optional
- **Partial Credit**: Award points for partial keyword matches
- **Case Sensitivity**: Optionally ignore case differences

## Configuration

### Required Fields

- `type`: Must be `"KEYWORD"`
- `question_id`: The ID of the question to grade

### Optional Fields

- `required_keywords` (default: `[]`): List of keywords that must be present
- `optional_keywords` (default: `[]`): List of keywords for bonus points
- `points_per_required` (default: `1.0`): Points awarded per required keyword found
- `points_per_optional` (default: `0.5`): Points awarded per optional keyword found
- `max_optional_points` (default: `None`): Cap on bonus points from optional keywords
- `case_sensitive` (default: `false`): Whether keyword matching is case-sensitive
- `partial_credit` (default: `true`): Award partial credit for some required keywords
- `description`: Human-readable description of the rule

### Calculated Properties

- `max_points`: Automatically calculated based on keywords and point values

## Example

```yaml
type: KEYWORD
question_id: q2_photosynthesis
required_keywords:
  - chlorophyll
  - sunlight
  - carbon dioxide
  - glucose
optional_keywords:
  - chloroplast
  - oxygen
  - ATP
points_per_required: 2.0
points_per_optional: 0.5
max_optional_points: 1.0
case_sensitive: false
partial_credit: true
description: "Photosynthesis process - check for key terms"
```

**Max Points**: (4 required × 2.0) + 1.0 (capped optional) = **9.0 points**

## Behavior

### Scoring Logic

1. **Search for Keywords**: Check if each keyword appears in the answer (substring match)
2. **Case Handling**: If `case_sensitive` is false, convert both to lowercase
3. **Count Matches**: Tally required and optional keywords found
4. **Calculate Points**:
   - Required: `matches × points_per_required`
   - Optional: `min(matches × points_per_optional, max_optional_points)`
5. **Partial Credit**: If disabled and not all required found → 0 points

### Matching Behavior

Keywords are matched as **substrings**, so:
- "DNA" matches in "DNA replication"
- "cell" matches in "cells" and "cellular"
- "photo" matches in "photosynthesis"

## Examples

### Example 1: Science Question

**Configuration:**
```yaml
required_keywords: [photosynthesis, chlorophyll, sunlight]
optional_keywords: [glucose, oxygen]
points_per_required: 2.0
points_per_optional: 1.0
partial_credit: true
```

**Student Answer:** "Plants use chlorophyll to perform photosynthesis using sunlight and produce glucose."

**Grading:**
- Required found: 3/3 (photosynthesis, chlorophyll, sunlight) → 6.0 points
- Optional found: 1/2 (glucose) → 1.0 points
- **Total: 7.0 points**

### Example 2: Partial Credit

**Configuration:**
```yaml
required_keywords: [mitosis, chromosomes, cell division]
points_per_required: 3.0
partial_credit: true
```

**Student Answer:** "Mitosis involves chromosomes separating."

**Grading:**
- Required found: 2/3 (mitosis, chromosomes) → 6.0 points
- **Total: 6.0 points** (out of max 9.0)

### Example 3: No Partial Credit

Same configuration but `partial_credit: false`

**Grading:**
- Required found: 2/3 → **Total: 0.0 points** (not all required keywords present)

## When to Use

✅ **Good For:**
- Open-ended questions with multiple correct phrasings
- Checking for specific concepts in essays
- Grading based on content coverage
- Partial credit scenarios
- Questions where keyword presence indicates understanding

❌ **Not Ideal For:**
- Exact answers needed (use ExactMatch)
- Order or structure matters (consider Regex or Programmable)
- Numeric answers (use NumericRange)
- Similarity/fuzzy matching needed (use Similarity)

## Tips

1. **Use lowercase keywords** and set `case_sensitive=false` for most cases
2. **Choose specific keywords** to avoid false positives (e.g., "cell division" not just "cell")
3. **Set `max_optional_points`** to prevent bonus points from exceeding expectations
4. **Consider word boundaries**: "photo" will match "photosynthesis" (may or may not be desired)
5. **Enable `partial_credit`** for fairer grading on complex questions
6. **Combine with other rules** using CompositeRule for more nuanced grading

## Advanced Usage

### Capping Optional Points

```yaml
optional_keywords: [detail1, detail2, detail3, detail4, detail5]
points_per_optional: 0.5
max_optional_points: 2.0  # Cap at 2 points even if all 5 mentioned
```

### All-or-Nothing Required Keywords

```yaml
required_keywords: [term1, term2, term3]
points_per_required: 10.0
partial_credit: false  # Must have all required for any points
```

## Related Rules

- **ExactMatch**: For single precise answers
- **Regex**: For pattern-based matching with more control
- **Similarity**: For fuzzy matching of entire answer
- **Composite**: Combine keyword rules with AND/OR logic
