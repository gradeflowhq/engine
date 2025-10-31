# Length Rule

## Overview

The Length rule grades answers based on their length constraints, either in word count or character count. It's perfect for ensuring students meet formatting requirements or answer constraints without evaluating content.

## Use Cases

- **Essay Requirements**: "Write 500-750 words"
- **Short Answer Format**: "Answer in 2-3 sentences"
- **Character Limits**: Tweet-length responses (280 characters)
- **Minimum Effort**: Ensure substantive responses
- **Format Compliance**: Check answer meets length specifications

## Features

- **Dual Metrics**: Count words or characters (or both)
- **Flexible Constraints**: Minimum and/or maximum limits
- **Partial Deductions**: Deduct points per violation
- **Strict Mode**: Zero points if any constraint violated
- **Multiple Constraints**: Combine word and character limits

## Configuration

### Required Fields

- `type`: Must be `"LENGTH"`
- `question_id`: The ID of the question to grade
- `max_points`: Maximum points available

### Optional Fields (At Least One Required)

- `min_words`: Minimum word count
- `max_words`: Maximum word count
- `min_chars`: Minimum character count
- `max_chars`: Maximum character count

### Additional Optional Fields

- `deduct_per_violation` (default: `0.0`): Points deducted for each constraint violation
- `strict` (default: `false`): If true, award 0 points for any violation
- `description`: Human-readable description of the rule

**Note:** At least one length constraint must be specified.

## Example

### Essay Length

```yaml
type: LENGTH
question_id: q7_essay
min_words: 500
max_words: 750
max_points: 20.0
deduct_per_violation: 5.0
strict: false
description: "Essay must be 500-750 words"
```

### Short Answer Format

```yaml
type: LENGTH
question_id: q8_short_answer
min_words: 10
max_words: 50
max_points: 5.0
strict: true
description: "Concise answer required (10-50 words)"
```

### Character Limit Only

```yaml
type: LENGTH
question_id: q9_tweet
max_chars: 280
max_points: 3.0
deduct_per_violation: 1.0
description: "Tweet-length response"
```

## Behavior

### Counting Logic

- **Words**: Split by whitespace, count non-empty tokens
- **Characters**: Count all characters including spaces and punctuation

### Scoring Logic

1. **Count Answer Length**: Calculate words and/or characters
2. **Check Constraints**: Identify which constraints are violated
3. **Apply Penalties**:
   - **Strict Mode**: Any violation → 0 points
   - **Deduction Mode**: Subtract `deduct_per_violation` for each violation
   - Minimum points: 0 (won't go negative)

### Violation Types

Each of these counts as one violation:
- Answer too short (words): `actual_words < min_words`
- Answer too long (words): `actual_words > max_words`
- Answer too short (chars): `actual_chars < min_chars`
- Answer too long (chars): `actual_chars > max_chars`

## Examples

### Example 1: Essay with Deductions

**Configuration:**
```yaml
min_words: 100
max_words: 200
max_points: 10.0
deduct_per_violation: 3.0
strict: false
```

**Grading:**
| Word Count | Violations | Points | Notes |
|------------|------------|--------|-------|
| 150        | 0          | 10.0   | Perfect |
| 100        | 0          | 10.0   | Minimum OK |
| 200        | 0          | 10.0   | Maximum OK |
| 95         | 1 (too short) | 7.0  | 10.0 - 3.0 |
| 210        | 1 (too long)  | 7.0  | 10.0 - 3.0 |
| 50         | 1          | 7.0    | Too short |

### Example 2: Strict Mode

**Configuration:**
```yaml
min_words: 50
max_words: 100
max_points: 5.0
strict: true
```

**Grading:**
| Word Count | Violations | Points | Notes |
|------------|------------|--------|-------|
| 75         | 0          | 5.0    | Within range |
| 50         | 0          | 5.0    | At minimum |
| 100        | 0          | 5.0    | At maximum |
| 49         | 1          | 0.0    | Too short - strict mode |
| 101        | 1          | 0.0    | Too long - strict mode |

### Example 3: Multiple Constraints

**Configuration:**
```yaml
min_words: 10
max_words: 50
min_chars: 50
max_chars: 300
max_points: 8.0
deduct_per_violation: 2.0
strict: false
```

**Scenario: 5 words, 45 characters**
- Violations: 2 (too few words AND too few chars)
- Points: 8.0 - (2 × 2.0) = **4.0 points**

### Example 4: Character Limit Only

**Configuration:**
```yaml
max_chars: 280
max_points: 3.0
deduct_per_violation: 1.5
```

**Grading:**
| Char Count | Violations | Points |
|------------|------------|--------|
| 150        | 0          | 3.0    |
| 280        | 0          | 3.0    |
| 300        | 1          | 1.5    |

## When to Use

✅ **Good For:**
- Enforcing length requirements
- Format compliance checking
- Ensuring minimum effort
- Preventing overly verbose answers
- Quick quality gate (combined with content rules)

❌ **Not Ideal For:**
- Content evaluation (combine with other rules)
- Quality assessment (length ≠ quality)
- Sole grading criterion (usually combined with content rules)

## Tips

1. **Combine with Content Rules**: Use with Keyword, Similarity, etc. via CompositeRule
2. **Set Reasonable Ranges**: Allow some flexibility (e.g., 450-550 for "~500 words")
3. **Consider Strict vs. Deduction**: 
   - Strict: Hard requirements (e.g., character limits)
   - Deduction: Softer guidelines (e.g., essay length)
4. **Use Appropriate Metric**: 
   - Words: Natural text (essays, answers)
   - Characters: Strict limits (tweets, form fields)
5. **Test Edge Cases**: Verify boundary values (min/max exactly)

## Advanced Usage

### Combined Word and Character Limits

```yaml
# Ensure substantive but concise answer
min_words: 20        # At least 20 words
max_chars: 500       # But under 500 characters
max_points: 10.0
strict: false
deduct_per_violation: 2.5
```

### Only Minimum Requirement

```yaml
# Ensure sufficient detail, no maximum
min_words: 100
max_points: 5.0
strict: true  # Must meet minimum
```

### Only Maximum Limit

```yaml
# Keep it brief
max_words: 25
max_points: 3.0
deduct_per_violation: 1.0
```

### Graduated Deductions

```yaml
# Create multiple rules for different ranges
# Rule 1: Preferred range (500-750 words)
# Rule 2: Acceptable range (400-500 or 750-850 words) - fewer points
# Rule 3: Outside range - minimal points
# Combine with CompositeRule in OR mode
```

## Combining with Other Rules

### Length + Content Quality

```yaml
type: COMPOSITE
question_id: q10_essay
mode: AND
rules:
  - type: LENGTH
    min_words: 200
    max_words: 400
    max_points: 5.0
    strict: true
  
  - type: KEYWORD
    required_keywords: [thesis, evidence, conclusion]
    points_per_required: 5.0
    max_points: 15.0
```

Student must meet BOTH length AND content requirements.

## Word Counting Details

Words are counted by:
1. Splitting answer by whitespace
2. Counting non-empty strings

Examples:
- `"Hello world"` → 2 words
- `"Hello   world"` (multiple spaces) → 2 words
- `"Hello, world! How are you?"` → 5 words
- `""` (empty) → 0 words

## Related Rules

- **Keyword**: Check content after length verification
- **Similarity**: Evaluate answer quality with length
- **Composite**: Combine length with content rules
- **Regex**: Pattern-based format checking (different from length)
