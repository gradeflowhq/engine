# NumericRange Rule

Grades numeric answers with tolerance and optional partial credit ranges.

## Use Cases
- Physics/chemistry calculations with acceptable rounding error
- Math problems where approximate answers are acceptable
- Engineering problems with measurement tolerance
- Financial calculations with precision requirements

## Features
- **Tolerance-based grading**: Accept answers within ±tolerance of correct value
- **Partial credit ranges**: Award different points for different deviation ranges
- **Unit awareness**: Optional unit specification (documented, not enforced by engine)
- **Error handling**: Graceful handling of non-numeric inputs

## Model Definition

```python
class NumericRangeRule(BaseModel):
    type: Literal["NUMERIC_RANGE"]
    question_id: str
    correct_value: float
    tolerance: float = 0.0  # Acceptable deviation for full credit
    points: float  # Maximum points
    unit: Optional[str] = None  # Expected unit (documentation only)
    partial_credit_ranges: Optional[List[Dict[str, float]]] = None
    description: Optional[str] = None
```

### Partial Credit Ranges

Format: List of dictionaries with `min`, `max`, and `points` keys:
```python
partial_credit_ranges=[
    {"min": 9.5, "max": 10.5, "points": 3.0},  # Close range
    {"min": 9.0, "max": 11.0, "points": 1.5},  # Wider range
]
```

## Grading Logic

1. **Parse student answer**: Convert to float, handle invalid inputs
2. **Check tolerance**: If |student - correct| ≤ tolerance → full points
3. **Check partial credit ranges**: Award points for values within defined ranges
4. **Default**: 0 points if outside all acceptable ranges

## Example Usage

### Basic Tolerance
```yaml
- type: NUMERIC_RANGE
  question_id: Q1
  correct_value: 9.81
  tolerance: 0.1  # Accept 9.71 to 9.91
  points: 5
  unit: "m/s²"
  description: "Acceleration due to gravity"
```

### With Partial Credit
```yaml
- type: NUMERIC_RANGE
  question_id: Q2
  correct_value: 100.0
  tolerance: 5.0  # Full credit: 95-105
  points: 10
  partial_credit_ranges:
    - min: 90
      max: 110
      points: 7  # 70% credit for wider range
    - min: 80
      max: 120
      points: 3  # 30% credit for very wide range
  description: "Estimate population parameter"
```

## Grading Examples

**Question:** Calculate g (m/s²)
- Correct answer: 9.81
- Tolerance: 0.1
- Max points: 5

| Student Answer | Result | Points | Feedback |
|---------------|--------|--------|----------|
| `9.81` | ✓ | 5.0 | Within tolerance (0.1) |
| `9.8` | ✓ | 5.0 | Within tolerance (0.1) |
| `9.75` | ✗ | 0.0 | Outside acceptable range (difference: 0.06) |
| `abc` | ✗ | 0.0 | Invalid numeric value |

## Implementation Notes

- Uses Python's `float()` for parsing
- Handles scientific notation (e.g., "1.23e-4")
- Case-insensitive for special values (inf, nan)
- Partial credit ranges are checked in order (first match wins)
- Unit field is for documentation only - no unit conversion or validation

## Common Patterns

### Physics Calculations
```yaml
- type: NUMERIC_RANGE
  correct_value: 299792458
  tolerance: 1000000
  unit: "m/s"
  description: "Speed of light"
```

### Percentage Estimates
```yaml
- type: NUMERIC_RANGE
  correct_value: 68.5
  tolerance: 2.5
  points: 3
  unit: "%"
```

### Financial Rounding
```yaml
- type: NUMERIC_RANGE
  correct_value: 1234.56
  tolerance: 0.01
  unit: "USD"
  description: "Calculate total cost"
```
