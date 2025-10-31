# Multiple Choice Rule

## Overview

The Multiple Choice rule is specifically designed for grading multiple choice questions (MCQ) and multiple response questions (MRQ). It supports various scoring strategies to handle different assessment scenarios.

## Use Cases

- **Single Answer MCQ**: Traditional multiple choice with one correct answer
- **Multiple Response Questions**: Select all that apply
- **Partial Credit MCQ**: Award points for partially correct selections
- **Negative Scoring**: Penalize incorrect selections to discourage guessing
- **All-or-Nothing**: Require perfect selection for any credit

## Features

- **Multiple Correct Answers**: Support MRQ with multiple valid selections
- **Flexible Scoring Modes**: All-or-nothing, partial credit, or negative marking
- **Case Insensitivity**: Optionally ignore case in answer matching
- **Penalty Configuration**: Customize deductions for wrong selections

## Configuration

### Required Fields

- `type`: Must be `"MULTIPLE_CHOICE"`
- `question_id`: The ID of the question to grade
- `correct_answers`: List of correct answer(s)
- `max_points`: Maximum points available

### Optional Fields

- `scoring_mode` (default: `"all_or_nothing"`): How to score the question
  - `"all_or_nothing"`: Full points only if all correct answers selected, nothing else
  - `"partial"`: Proportional credit based on correct vs. total selections
  - `"negative"`: Deduct points for wrong selections
- `penalty_per_wrong` (default: `0.0`): Points deducted per incorrect selection (for negative scoring)
- `case_sensitive` (default: `false`): Whether answer matching is case-sensitive
- `description`: Human-readable description of the rule

## Example

### Single Answer MCQ

```yaml
type: MULTIPLE_CHOICE
question_id: q11_capital
correct_answers: ["Paris"]
max_points: 5.0
scoring_mode: all_or_nothing
case_sensitive: false
description: "Capital of France"
```

### Multiple Response Question (Partial Credit)

```yaml
type: MULTIPLE_CHOICE
question_id: q12_prime_numbers
correct_answers: ["2", "3", "5", "7"]
max_points: 10.0
scoring_mode: partial
case_sensitive: false
description: "Select all prime numbers less than 10"
```

### With Negative Marking

```yaml
type: MULTIPLE_CHOICE
question_id: q13_biology
correct_answers: ["A", "C"]
max_points: 8.0
scoring_mode: negative
penalty_per_wrong: 2.0
description: "Select all that apply - wrong answers penalized"
```

## Behavior

### Scoring Logic by Mode

#### Mode: "all_or_nothing"

- **Full Credit**: Student selects exactly the correct answers (no more, no less)
- **Zero Credit**: Any deviation from the correct answer set

```
if student_answers == correct_answers:
    points = max_points
else:
    points = 0
```

#### Mode: "partial"

- **Proportional Credit**: Based on overlap with correct answers
- **Formula**: `(correct_selected / total_correct) × max_points`

```
correct_count = count(student ∩ correct)
total_correct = count(correct)
points = (correct_count / total_correct) × max_points
```

**Important**: Wrong selections don't penalize, only dilute the proportion

#### Mode: "negative"

- **Award for Correct**: Full points for each correct selection
- **Penalize Wrong**: Deduct `penalty_per_wrong` for each incorrect selection
- **Minimum**: Never goes below 0

```
points = max_points - (wrong_selections × penalty_per_wrong)
points = max(0, points)
```

## Examples

### Example 1: Single Answer MCQ (All-or-Nothing)

**Configuration:**
```yaml
correct_answers: ["B"]
max_points: 5.0
scoring_mode: all_or_nothing
```

**Grading:**
| Student Selects | Points | Notes |
|-----------------|--------|-------|
| ["B"]           | 5.0    | Correct |
| ["A"]           | 0.0    | Wrong answer |
| ["B", "C"]      | 0.0    | Extra selection |
| []              | 0.0    | No answer |

### Example 2: Multiple Response (Partial Credit)

**Configuration:**
```yaml
correct_answers: ["A", "B", "C"]
max_points: 9.0
scoring_mode: partial
```

**Grading:**
| Student Selects | Correct Selected | Points | Calculation |
|-----------------|------------------|--------|-------------|
| ["A", "B", "C"] | 3/3              | 9.0    | (3/3) × 9 |
| ["A", "B"]      | 2/3              | 6.0    | (2/3) × 9 |
| ["A"]           | 1/3              | 3.0    | (1/3) × 9 |
| ["A", "D"]      | 1/3              | 3.0    | (1/3) × 9 (D ignored) |
| ["D", "E"]      | 0/3              | 0.0    | (0/3) × 9 |
| []              | 0/3              | 0.0    | No selection |

### Example 3: Negative Marking

**Configuration:**
```yaml
correct_answers: ["A", "C"]
max_points: 10.0
scoring_mode: negative
penalty_per_wrong: 2.5
```

**Grading:**
| Student Selects | Correct | Wrong | Points | Calculation |
|-----------------|---------|-------|--------|-------------|
| ["A", "C"]      | 2       | 0     | 10.0   | 10 - 0×2.5 |
| ["A"]           | 1       | 0     | 10.0   | 10 - 0×2.5 (partial OK) |
| ["A", "B", "C"] | 2       | 1     | 7.5    | 10 - 1×2.5 |
| ["B", "D"]      | 0       | 2     | 5.0    | 10 - 2×2.5 |
| ["B", "D", "E"] | 0       | 3     | 2.5    | 10 - 3×2.5 |
| ["A", "B", "C", "D"] | 2  | 2     | 5.0    | 10 - 2×2.5 |

### Example 4: Case Insensitive Matching

**Configuration:**
```yaml
correct_answers: ["Paris", "London"]
max_points: 6.0
scoring_mode: partial
case_sensitive: false
```

**Grading:**
| Student Selects | Points | Notes |
|-----------------|--------|-------|
| ["paris", "london"] | 6.0 | Case ignored |
| ["PARIS", "LONDON"] | 6.0 | Case ignored |
| ["Paris"]       | 3.0    | Partial credit |

## When to Use

✅ **Good For:**
- Traditional multiple choice questions
- "Select all that apply" questions
- Surveys with correct answer sets
- Binary choices (True/False)
- Questions with clear answer options

❌ **Not Ideal For:**
- Free-form text answers (use ExactMatch or Similarity)
- Numeric answers (use NumericRange)
- Pattern matching (use Regex)
- Complex evaluation logic (use Programmable)

## Tips

1. **Choose Scoring Mode Carefully**:
   - `all_or_nothing`: Strict assessment, prevents partial credit
   - `partial`: Encourages students, rewards partial knowledge
   - `negative`: Discourages random guessing
   
2. **Set Appropriate Penalties**: For negative mode, balance penalty to discourage guessing without being overly harsh
   
3. **Use Case Insensitive**: Set `case_sensitive=false` unless case matters (usually doesn't for MCQ)
   
4. **Single Answer MCQ**: Use `correct_answers: ["A"]` (list with one item)
   
5. **Validate Answer Format**: Ensure student answers match your option format (e.g., "A", "B" vs. "Option A")

## Advanced Usage

### Balanced Negative Marking

```yaml
# For 4 options, 1 correct: penalty discourages random guessing
correct_answers: ["A"]
max_points: 4.0
scoring_mode: negative
penalty_per_wrong: 1.33  # Expected value of guessing = 0
```

### Weighted Multiple Response

```yaml
# Use multiple rules with CompositeRule for weighted MRQ
type: COMPOSITE
mode: WEIGHTED
rules:
  - type: MULTIPLE_CHOICE
    correct_answers: ["A"]  # Critical concept
    max_points: 10.0
  - type: MULTIPLE_CHOICE
    correct_answers: ["B", "C"]  # Secondary concepts
    max_points: 5.0
weights: [0.7, 0.3]  # 70% for critical, 30% for secondary
```

### True/False Questions

```yaml
type: MULTIPLE_CHOICE
question_id: q14_true_false
correct_answers: ["True"]
max_points: 2.0
scoring_mode: all_or_nothing
```

## Scoring Mode Comparison

| Scenario | All-or-Nothing | Partial | Negative |
|----------|----------------|---------|----------|
| Perfect answer | Full points | Full points | Full points |
| Some correct, some wrong | 0 points | Partial points | Full - penalties |
| All wrong | 0 points | 0 points | Max(0, full - penalties) |
| No answer | 0 points | 0 points | Full points |
| Encourages guessing? | Neutral | Yes | No |
| Best for | Single answer MCQ | MRQ learning | High-stakes assessment |

## Related Rules

- **ExactMatch**: For single text answers (not multiple choice)
- **Keyword**: For checking specific terms in free response
- **Composite**: Combine multiple MCQ or with other rule types
- **Conditional**: Make MCQ answers depend on other questions
