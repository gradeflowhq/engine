# Exact Match Rule

## Description
Compares student answer with expected answer using exact string matching. Supports case-insensitive comparison and whitespace trimming.

## Model Fields
- `question_id`: Question identifier to grade
- `correct_answer`: The expected correct answer
- `max_points`: Maximum points awarded for correct answer
- `case_sensitive`: Whether comparison is case-sensitive (default: False)
- `trim_whitespace`: Whether to trim leading/trailing whitespace (default: True)
- `description`: Optional description of the rule

## Examples

### YAML Example
```yaml
type: EXACT_MATCH
question_id: Q1
correct_answer: "Paris"
max_points: 10.0
case_sensitive: false
trim_whitespace: true
description: "Capital of France"
```

### Python Example
```python
from gradeflow_engine import ExactMatchRule, Rubric, Submission, grade

rule = ExactMatchRule(
    question_id="Q1",
    correct_answer="Paris",
    max_points=10.0,
    case_sensitive=False,
    trim_whitespace=True
)

rubric = Rubric(rules=[rule])
submission = Submission(student_id="student1", answers={"Q1": "paris"})
results = grade(rubric, [submission])
```

## Behavior
1. Retrieves student's answer for the specified question
2. Applies transformations if configured:
   - `trim_whitespace=True`: Removes leading/trailing spaces
   - `case_sensitive=False`: Converts both answers to lowercase
3. Compares transformed student answer with transformed correct answer
4. Awards full points if match, zero points otherwise

## Use Cases
- Simple factual questions with single correct answer
- Short answer questions (names, terms, definitions)
- Questions where exact wording matters (case-sensitive mode)
- Questions where whitespace should be ignored (default)
