# Regex Rule

## Overview

The Regex rule enables powerful pattern-based grading using regular expressions. It's ideal for validating answer formats, checking for specific patterns, or implementing complex matching logic that goes beyond simple keyword detection.

## Use Cases

- **Format Validation**: Email addresses, phone numbers, URLs
- **Pattern Matching**: Chemical formulas, mathematical expressions
- **Structured Answers**: Code snippets, specific formatting requirements
- **Flexible Matching**: Multiple valid answer patterns
- **Complex Criteria**: Combining multiple pattern requirements

## Features

- **Multiple Patterns**: Define several regex patterns with individual scoring
- **Flexible Matching Modes**: ALL (all must match), ANY (at least one), COUNT (based on matches)
- **Regex Flags**: Case-insensitive, multiline, dotall modes
- **Partial Credit**: Award points for partial pattern matches
- **Per-Pattern Scoring**: Different points for different patterns

## Configuration

### Required Fields

- `type`: Must be `"REGEX"`
- `question_id`: The ID of the question to grade
- `patterns`: List of regex pattern strings
- `points_per_match`: Points per pattern (single value or list)

### Optional Fields

- `match_mode` (default: `"all"`): How patterns are evaluated
  - `"all"`: All patterns must match for full points
  - `"any"`: Any pattern match awards points
  - `"count"`: Points based on number of matches
- `case_sensitive` (default: `true`): Whether regex is case-sensitive
- `multiline` (default: `false`): Enable multiline mode (^ and $ match line boundaries)
- `dotall` (default: `false`): Enable dotall mode (. matches newlines)
- `partial_credit` (default: `true`): Award partial credit for partial matches (in `"all"` mode)
- `description`: Human-readable description of the rule

### Calculated Properties

- `max_points`: Automatically calculated based on patterns and points

## Example

### Basic Pattern Matching

```yaml
type: REGEX
question_id: q5_email
patterns:
  - "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
points_per_match: 10.0
match_mode: all
case_sensitive: false
description: "Valid email address format"
```

### Multiple Patterns with Different Points

```yaml
type: REGEX
question_id: q6_code_review
patterns:
  - "\\bdef\\s+\\w+\\s*\\("        # Function definition
  - "\\breturn\\b"                  # Has return statement
  - '""".*?"""'                     # Has docstring
match_mode: count
points_per_match: [5.0, 3.0, 2.0]
case_sensitive: true
partial_credit: true
description: "Python function requirements"
```

## Behavior

### Scoring Logic

#### Mode: "all"
1. **Check All Patterns**: Each pattern must match somewhere in the answer
2. **Full Credit**: If all match → full points
3. **Partial Credit**: If `partial_credit=true`, award proportional points for matched patterns

#### Mode: "any"
1. **Check Any Pattern**: At least one pattern must match
2. **Award Points**: Use the points value of the first matching pattern

#### Mode: "count"
1. **Count Matches**: Tally how many patterns match
2. **Sum Points**: Add up points for all matching patterns

### Regex Flags

Based on configuration:
- `case_sensitive=false` → Adds `re.IGNORECASE` flag
- `multiline=true` → Adds `re.MULTILINE` flag
- `dotall=true` → Adds `re.DOTALL` flag

## Examples

### Example 1: Email Validation

**Configuration:**
```yaml
patterns: ["^[\\w.+-]+@[\\w.-]+\\.[a-zA-Z]{2,}$"]
points_per_match: 5.0
match_mode: all
case_sensitive: false
```

**Grading:**
| Student Answer | Match? | Points |
|----------------|--------|--------|
| "user@example.com" | ✓ | 5.0 |
| "test.user@domain.co.uk" | ✓ | 5.0 |
| "invalid@" | ✗ | 0.0 |
| "@example.com" | ✗ | 0.0 |

### Example 2: Chemistry Formula

**Configuration:**
```yaml
patterns:
  - "H2O"
  - "O2"
  - "CO2"
points_per_match: 3.0
match_mode: any
case_sensitive: true
```

**Grading:**
| Student Answer | Points | Matched |
|----------------|--------|---------|
| "H2O is water" | 3.0 | H2O |
| "Carbon dioxide is CO2" | 3.0 | CO2 |
| "h2o" | 0.0 | None (case-sensitive) |

### Example 3: Code Requirements (ALL mode)

**Configuration:**
```yaml
patterns:
  - "\\bclass\\s+\\w+"         # Has class definition
  - "\\bdef\\s+__init__"        # Has __init__ method
  - "\\bself\\."                # Uses self
points_per_match: 10.0
match_mode: all
partial_credit: true
```

**Grading:**
| Student Answer | Patterns Matched | Points |
|----------------|------------------|--------|
| Full class with all requirements | 3/3 | 10.0 |
| Class with __init__ but no self | 2/3 | 6.67 |
| Only class keyword | 1/3 | 3.33 |
| No patterns | 0/3 | 0.0 |

### Example 4: Multiple Patterns with Different Points (COUNT mode)

**Configuration:**
```yaml
patterns:
  - "\\b[A-Z]{2,}"              # Has acronyms (2 pts)
  - "\\d{4}"                     # Has year (3 pts)
  - "https?://\\S+"             # Has URL (1 pt)
points_per_match: [2.0, 3.0, 1.0]
match_mode: count
```

**Grading:**
| Student Answer | Matched Patterns | Points |
|----------------|------------------|--------|
| "NASA launched in 1958 at https://nasa.gov" | All 3 | 6.0 |
| "The USA was founded in 1776" | Patterns 1,2 | 5.0 |
| "Visit https://example.com" | Pattern 3 | 1.0 |

## When to Use

✅ **Good For:**
- Format validation (emails, phone numbers, IDs)
- Pattern-based answers (chemical formulas, expressions)
- Multiple valid answer formats
- Checking for specific structural elements
- Code or markup validation

❌ **Not Ideal For:**
- Simple exact matches (use ExactMatch)
- Keyword presence (use Keyword for simpler cases)
- Numeric ranges (use NumericRange)
- Fuzzy/similarity matching (use Similarity)
- Very complex logic (consider Programmable)

## Tips

1. **Escape Special Characters**: Use `\\` for backslashes in YAML
2. **Test Your Regex**: Use tools like regex101.com before deployment
3. **Use Raw Strings**: In Python, use `r"pattern"` to avoid escaping issues
4. **Start Simple**: Begin with basic patterns and add complexity as needed
5. **Consider Case**: Default is case-sensitive; adjust based on content
6. **Use Anchors**: `^` and `$` to match entire answer vs. substring
7. **Group Related Patterns**: Use match_mode appropriately

## Common Patterns

### Email
```regex
^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
```

### Phone Number (US)
```regex
^\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})$
```

### URL
```regex
^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$
```

### Date (YYYY-MM-DD)
```regex
^\d{4}-\d{2}-\d{2}$
```

### Chemical Formula
```regex
^([A-Z][a-z]?\d*)+$
```

## Advanced Usage

### Multiline Text Matching

```yaml
patterns:
  - "^Introduction"
  - "^Conclusion"
points_per_match: 5.0
match_mode: all
multiline: true
```

### Greedy vs Non-Greedy

```yaml
# Match quoted strings
patterns:
  - '".*?"'  # Non-greedy (recommended)
  # vs
  - '".*"'   # Greedy (may match too much)
```

### Lookahead/Lookbehind

```yaml
# Password validation: has uppercase, lowercase, digit
patterns:
  - "(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).{8,}"
points_per_match: 10.0
```

## Validation Rules

The rule validates:
1. ✅ At least one pattern is required
2. ✅ If `points_per_match` is a list, it must match the number of patterns
3. ✅ All point values must be ≥ 0

## Related Rules

- **ExactMatch**: For simple exact string matching
- **Keyword**: For simpler keyword presence checks
- **Similarity**: For fuzzy matching without patterns
- **Programmable**: For complex pattern logic beyond regex capabilities
- **Composite**: Combine multiple regex rules
