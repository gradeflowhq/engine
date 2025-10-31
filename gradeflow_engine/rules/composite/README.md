# Composite Rule

## Overview

The Composite rule enables combining multiple grading rules for a single question using logical operators (AND, OR) or weighted averaging. This allows complex, multi-faceted grading scenarios where multiple criteria must be evaluated together.

## Use Cases

- **Multiple Criteria**: Answer must meet several requirements simultaneously
- **Alternative Paths**: Accept answer if ANY of several conditions are met
- **Weighted Evaluation**: Combine different aspects with different importance
- **Complex Grading**: Layered evaluation (format + content + length)
- **Flexible Acceptance**: Multiple valid approaches to the same question

## Features

- **Three Modes**: AND, OR, WEIGHTED combination logic
- **Recursive Composition**: Composite rules can contain other composite rules
- **Flexible Weighting**: Customize importance of each sub-rule
- **Min Passing Threshold**: Require minimum number of passing rules (OR mode)
- **Correctness Threshold**: Define what percentage counts as "correct" (WEIGHTED mode)

## Configuration

### Required Fields

- `type`: Must be `"COMPOSITE"`
- `question_id`: The ID of the question to grade
- `mode`: Combination logic (`"AND"`, `"OR"`, or `"WEIGHTED"`)
- `rules`: List of composable rules to combine

### Optional Fields

- `weights`: List of weights for each rule (required for WEIGHTED mode)
- `min_passing`: Minimum number of passing rules (optional for OR mode)
- `correctness_threshold` (default: `0.95`): Score threshold (0.0-1.0) for weighted correctness
- `description`: Human-readable description of the rule

### Composable Rules

Can include any **single-question rule**:
- ✅ ExactMatch, Keyword, Length, MultipleChoice
- ✅ NumericRange, Regex, Similarity, Programmable
- ✅ Other Composite rules (recursive)
- ❌ ConditionalRule (operates on multiple questions)
- ❌ AssumptionSetRule (operates on multiple questions)

## Example

### AND Mode: All Must Pass

```yaml
type: COMPOSITE
question_id: q21_essay
mode: AND
rules:
  - type: LENGTH
    min_words: 200
    max_words: 500
    max_points: 5.0
    strict: true
  
  - type: KEYWORD
    required_keywords: [introduction, body, conclusion]
    points_per_required: 3.0
    max_points: 9.0
  
  - type: SIMILARITY
    reference_answers: ["A well-structured essay about the topic"]
    threshold: 0.7
    max_points: 6.0
description: "Essay must meet length, structure, and content requirements"
```

### OR Mode: Any Can Pass

```yaml
type: COMPOSITE
question_id: q22_alternative_solutions
mode: OR
rules:
  - type: EXACT_MATCH
    correct_answer: "Method A: Use recursion"
    max_points: 10.0
  
  - type: EXACT_MATCH
    correct_answer: "Method B: Use iteration"
    max_points: 10.0
  
  - type: KEYWORD
    required_keywords: [dynamic programming, memoization]
    points_per_required: 5.0
    max_points: 10.0
description: "Accept any valid solution approach"
```

### WEIGHTED Mode: Weighted Average

```yaml
type: COMPOSITE
question_id: q23_comprehensive
mode: WEIGHTED
rules:
  - type: SIMILARITY
    reference_answers: ["The correct explanation"]
    threshold: 0.75
    max_points: 10.0
  
  - type: KEYWORD
    required_keywords: [key_term_1, key_term_2, key_term_3]
    points_per_required: 3.0
    max_points: 9.0
  
  - type: LENGTH
    min_words: 50
    max_words: 150
    max_points: 5.0
weights: [0.5, 0.3, 0.2]  # 50% similarity, 30% keywords, 20% length
correctness_threshold: 0.85
description: "Weighted evaluation of answer quality"
```

## Behavior

### Mode: AND

All rules must pass for full credit.

**Scoring:**
```python
# All rules must award full points (max_points)
all_correct = all(rule.points == rule.max_points for rule in rules)

if all_correct:
    points_awarded = sum(rule.max_points for rule in rules)
    is_correct = True
else:
    points_awarded = 0.0
    is_correct = False
```

**Characteristics:**
- Strict: All criteria must be met
- Binary: Full points or zero
- Use case: Mandatory requirements

### Mode: OR

At least one rule must pass (or `min_passing` rules if specified).

**Scoring:**
```python
# Find the rule with highest points
best_rule = max(rules, key=lambda r: r.points)

points_awarded = best_rule.points
max_possible = best_rule.max_points
is_correct = (points_awarded >= max_possible)
```

With `min_passing`:
```python
passing_count = count(rule.points >= rule.max_points for rule in rules)

if passing_count >= min_passing:
    # Use best scoring rule
    points_awarded = max(rule.points for rule in rules)
else:
    points_awarded = 0.0
```

**Characteristics:**
- Flexible: Multiple paths to success
- Takes best: Uses highest-scoring rule
- Use case: Alternative valid answers

### Mode: WEIGHTED

Combine rules using weighted average.

**Scoring:**
```python
# Normalize each rule's score
normalized_scores = [
    rule.points / rule.max_points if rule.max_points > 0 else 0
    for rule in rules
]

# Calculate weighted average
weighted_score = sum(score * weight for score, weight in zip(normalized_scores, weights))

# Determine if correct based on threshold
is_correct = (weighted_score >= correctness_threshold)

# Calculate points (weighted average of max points)
total_max = sum(rule.max_points for rule in rules)
points_awarded = weighted_score * total_max
```

**Characteristics:**
- Nuanced: Different criteria have different importance
- Proportional: Partial success yields partial credit
- Use case: Multi-dimensional evaluation

## Examples

### Example 1: AND - Strict Requirements

**Configuration:**
```yaml
mode: AND
rules:
  - type: REGEX
    patterns: ["^[A-Z]"]  # Must start with capital
    points_per_match: 2.0
  - type: LENGTH
    min_chars: 10
    max_chars: 50
    max_points: 2.0
    strict: true
  - type: KEYWORD
    required_keywords: [important]
    points_per_required: 2.0
```

**Grading:**
| Answer | Regex | Length | Keyword | Total | Result |
|--------|-------|--------|---------|-------|--------|
| "Important message here" | ✓ 2.0 | ✓ 2.0 | ✓ 2.0 | 6.0 | All pass → 6.0 |
| "important message here" | ✗ 0.0 | ✓ 2.0 | ✓ 2.0 | - | Not all → 0.0 |
| "Important" | ✓ 2.0 | ✗ 0.0 | ✓ 2.0 | - | Not all → 0.0 |

### Example 2: OR - Multiple Valid Answers

**Configuration:**
```yaml
mode: OR
rules:
  - type: EXACT_MATCH
    correct_answer: "Paris"
    max_points: 5.0
  - type: EXACT_MATCH
    correct_answer: "paris"
    max_points: 5.0
  - type: SIMILARITY
    reference_answers: ["Paris"]
    threshold: 0.8
    max_points: 5.0
```

**Grading:**
| Answer | Match 1 | Match 2 | Similarity | Best | Points |
|--------|---------|---------|------------|------|--------|
| "Paris" | 5.0 | 0.0 | 5.0 | 5.0 | 5.0 |
| "paris" | 0.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| "Pariis" | 0.0 | 0.0 | 4.2 | 4.2 | 4.2 |

### Example 3: WEIGHTED - Balanced Grading

**Configuration:**
```yaml
mode: WEIGHTED
rules:
  - type: KEYWORD
    required_keywords: [concept_a, concept_b]
    points_per_required: 5.0  # max 10
  - type: LENGTH
    min_words: 30
    max_words: 100
    max_points: 5.0
  - type: SIMILARITY
    reference_answers: ["Good answer"]
    threshold: 0.7
    max_points: 5.0
weights: [0.5, 0.25, 0.25]  # Keywords 50%, others 25% each
correctness_threshold: 0.8
```

**Scenario: Answer has both keywords (10/10), meets length (5/5), mediocre similarity (3/5)**

Calculations:
- Keyword score: 10/10 = 1.0
- Length score: 5/5 = 1.0  
- Similarity score: 3/5 = 0.6
- Weighted avg: (1.0×0.5) + (1.0×0.25) + (0.6×0.25) = 0.5 + 0.25 + 0.15 = **0.90**
- Is correct: 0.90 ≥ 0.8 → **Yes**
- Points: 0.90 × (10+5+5) = **18.0 points**

### Example 4: OR with Min Passing

**Configuration:**
```yaml
mode: OR
min_passing: 2  # At least 2 rules must pass
rules:
  - type: KEYWORD
    required_keywords: [term1]
    points_per_required: 5.0
  - type: LENGTH
    min_words: 20
    max_points: 5.0
  - type: SIMILARITY
    reference_answers: ["good"]
    threshold: 0.7
    max_points: 5.0
```

**Grading:**
| Answer | Keyword | Length | Similarity | Pass Count | Points |
|--------|---------|--------|------------|------------|--------|
| "Has term1 and is long enough with good similarity" | 5.0 | 5.0 | 5.0 | 3 | 5.0 |
| "Has term1 and is long enough" | 5.0 | 5.0 | 2.0 | 2 | 5.0 |
| "Has term1" | 5.0 | 0.0 | 0.0 | 1 | 0.0 (min not met) |

## When to Use

✅ **Good For:**
- Multi-criteria evaluation
- Format + content checking
- Alternative valid answers
- Layered requirements
- Balanced grading across dimensions
- Complex rubrics

❌ **Not Ideal For:**
- Simple single-criterion questions (use basic rules)
- Cross-question logic (use Conditional or AssumptionSet)
- Very simple OR logic (consider multiple reference answers in base rules)

## Tips

1. **Choose Mode Carefully**:
   - AND: All must pass (strict)
   - OR: Any can pass (flexible)
   - WEIGHTED: Nuanced combination

2. **Weight Thoughtfully**: In WEIGHTED mode, ensure weights sum to 1.0

3. **Set Appropriate Thresholds**: `correctness_threshold` in WEIGHTED determines "passing"

4. **Nest Strategically**: Composite rules can contain composite rules for complex logic

5. **Test Thoroughly**: Complex compositions can have unexpected behavior

6. **Document Logic**: Use `description` to explain the grading rationale

## Advanced Usage

### Nested Composition

```yaml
type: COMPOSITE
mode: AND
rules:
  # First criterion: Length is appropriate
  - type: LENGTH
    min_words: 100
    max_words: 200
    max_points: 5.0
  
  # Second criterion: Content meets ANY of these
  - type: COMPOSITE
    mode: OR
    rules:
      - type: KEYWORD
        required_keywords: [approach_a, method_a]
        points_per_required: 10.0
      - type: KEYWORD
        required_keywords: [approach_b, method_b]
        points_per_required: 10.0
```

### Graduated Weighted Scoring

```yaml
mode: WEIGHTED
rules:
  - type: SIMILARITY  # Core content (60%)
    reference_answers: ["The main concept"]
    threshold: 0.75
    max_points: 10.0
  
  - type: KEYWORD    # Supporting details (25%)
    required_keywords: [detail1, detail2, detail3]
    points_per_required: 2.0
    max_points: 6.0
  
  - type: LENGTH     # Format (15%)
    min_words: 50
    max_words: 150
    max_points: 4.0

weights: [0.6, 0.25, 0.15]
correctness_threshold: 0.7
```

## Validation Rules

The rule validates:
1. ✅ At least one sub-rule is required
2. ✅ All sub-rules must be composable (single-question rules)
3. ✅ WEIGHTED mode requires `weights` list
4. ✅ `weights` must match number of rules
5. ✅ All weights must be ≥ 0
6. ✅ `correctness_threshold` must be 0.0-1.0
7. ✅ `min_passing` (if specified) must be ≤ number of rules

## Related Rules

- **Conditional**: For if-then logic across questions
- **AssumptionSet**: For multiple valid answer sets
- All basic rules: Building blocks for composite rules
