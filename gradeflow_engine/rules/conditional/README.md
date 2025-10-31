# Conditional Rule

## Overview

The Conditional rule implements if-then grading logic across multiple questions. It evaluates one question's answer and uses it to determine the correct answer for another question. This is perfect for questions where the correct answer depends on a previous choice or response.

## Use Cases

- **Follow-Up Questions**: "If you chose A in Q1, what should Q2 be?"
- **Dependent Answers**: Answer to Q2 depends on method chosen in Q1
- **Scenario-Based Tests**: Different paths through a problem
- **Consistency Checking**: Ensure answers align across questions
- **Branching Logic**: Different correct answers based on earlier choices

## Features

- **Cross-Question Logic**: Reference answers from other questions
- **Simple If-Then Structure**: Easy to understand and configure
- **Flexible Matching**: Works with any answer format
- **Clear Dependencies**: Makes answer relationships explicit

## Configuration

### Required Fields

- `type`: Must be `"CONDITIONAL"`
- `if_question`: Question ID to check for the condition
- `if_answer`: Expected answer value that triggers the condition
- `then_question`: Question ID to grade (based on the condition)
- `then_correct_answer`: The correct answer for `then_question` when condition is met
- `max_points`: Points awarded if the conditional logic is satisfied

### Optional Fields

- `description`: Human-readable description of the rule

## Example

### Basic Conditional

```yaml
type: CONDITIONAL
if_question: q1_method
if_answer: "recursion"
then_question: q2_implementation
then_correct_answer: "Use base case and recursive call"
max_points: 10.0
description: "If recursion chosen, implementation must use base case"
```

### Multiple Conditionals for Same Question

```yaml
# Rule 1: If chose Method A
- type: CONDITIONAL
  if_question: q1_approach
  if_answer: "Method A"
  then_question: q2_next_step
  then_correct_answer: "Apply formula X"
  max_points: 5.0

# Rule 2: If chose Method B  
- type: CONDITIONAL
  if_question: q1_approach
  if_answer: "Method B"
  then_question: q2_next_step
  then_correct_answer: "Apply formula Y"
  max_points: 5.0
```

### Chained Dependencies

```yaml
# First level
- type: CONDITIONAL
  if_question: q1_topic
  if_answer: "Physics"
  then_question: q2_subtopic
  then_correct_answer: "Mechanics"
  max_points: 3.0

# Second level
- type: CONDITIONAL
  if_question: q2_subtopic
  if_answer: "Mechanics"
  then_question: q3_concept
  then_correct_answer: "Newton's Laws"
  max_points: 5.0
```

## Behavior

### Evaluation Logic

1. **Check Condition**: Compare student's answer to `if_question` with `if_answer`
2. **Evaluate Then**: If condition matches, check if `then_question` answer matches `then_correct_answer`
3. **Award Points**:
   - If condition NOT met: Rule does not apply (no points, but not penalized)
   - If condition met AND then_answer correct: Award `max_points`
   - If condition met AND then_answer incorrect: Award `0.0` points

### Matching Behavior

- **Exact Match**: Uses simple string comparison
- **Case Sensitive**: Comparison is case-sensitive by default
- **Whitespace**: Includes whitespace in comparison
- **Recommendation**: Normalize answers before comparison or use flexible matching

### Points Calculation

```python
if student_answers[if_question] == if_answer:
    # Condition is met, evaluate then_question
    if student_answers[then_question] == then_correct_answer:
        points_awarded = max_points
        is_correct = True
    else:
        points_awarded = 0.0
        is_correct = False
else:
    # Condition not met, rule doesn't apply
    points_awarded = None  # Rule skipped
    is_correct = None
```

## Examples

### Example 1: Method Selection

**Rubric:**
```yaml
# Question 1: Choose solving method
# Question 2: Show implementation

- type: CONDITIONAL
  if_question: q1_method
  if_answer: "iteration"
  then_question: q2_code
  then_correct_answer: "for loop"
  max_points: 8.0

- type: CONDITIONAL
  if_question: q1_method
  if_answer: "recursion"
  then_question: q2_code
  then_correct_answer: "recursive function"
  max_points: 8.0
```

**Grading:**
| Q1 Answer | Q2 Answer | Rule Applied | Points |
|-----------|-----------|--------------|--------|
| "iteration" | "for loop" | Rule 1 | 8.0 |
| "iteration" | "recursive function" | Rule 1 | 0.0 |
| "recursion" | "recursive function" | Rule 2 | 8.0 |
| "recursion" | "for loop" | Rule 2 | 0.0 |
| "neither" | "for loop" | Neither | 0.0 (no rule applies) |

### Example 2: Scenario-Based

**Rubric:**
```yaml
# If patient has symptom X, correct diagnosis is Y
- type: CONDITIONAL
  if_question: q1_symptoms
  if_answer: "fever and cough"
  then_question: q2_diagnosis
  then_correct_answer: "respiratory infection"
  max_points: 15.0
  description: "Fever and cough → respiratory infection"

- type: CONDITIONAL
  if_question: q1_symptoms
  if_answer: "fever and rash"
  then_question: q2_diagnosis
  then_correct_answer: "viral infection"
  max_points: 15.0
  description: "Fever and rash → viral infection"
```

### Example 3: Multi-Step Problem

**Rubric:**
```yaml
# Step 1: Choose formula
# Step 2: Calculate intermediate value (depends on formula)
# Step 3: Final answer (depends on intermediate)

- type: CONDITIONAL
  if_question: q1_formula
  if_answer: "Formula A"
  then_question: q2_intermediate
  then_correct_answer: "25"
  max_points: 5.0

- type: CONDITIONAL
  if_question: q1_formula
  if_answer: "Formula B"
  then_question: q2_intermediate
  then_correct_answer: "30"
  max_points: 5.0

- type: CONDITIONAL
  if_question: q2_intermediate
  if_answer: "25"
  then_question: q3_final
  then_correct_answer: "100"
  max_points: 10.0

- type: CONDITIONAL
  if_question: q2_intermediate
  if_answer: "30"
  then_question: q3_final
  then_correct_answer: "120"
  max_points: 10.0
```

### Example 4: Consistency Check

**Rubric:**
```yaml
# Ensure unit consistency
- type: CONDITIONAL
  if_question: q1_unit_choice
  if_answer: "meters"
  then_question: q2_calculation
  then_correct_answer: "100 meters"
  max_points: 5.0

- type: CONDITIONAL
  if_question: q1_unit_choice
  if_answer: "feet"
  then_question: q2_calculation
  then_correct_answer: "328 feet"
  max_points: 5.0
```

## When to Use

✅ **Good For:**
- Questions with dependent answers
- Branching scenarios
- Method-dependent solutions
- Consistency validation
- Follow-up questions
- Multi-step problems with choices

❌ **Not Ideal For:**
- Independent questions (use basic rules)
- Complex multi-question logic (consider AssumptionSet)
- Single question evaluation (use basic rules)
- Weighted combinations (use Composite)

## Tips

1. **Normalize Answers**: Consider trimming whitespace, normalizing case
   - Use Programmable rule for flexible matching if needed

2. **Cover All Cases**: Create conditional rules for all possible if-answers
   - Otherwise, some answer paths won't be graded

3. **Document Dependencies**: Use `description` to explain the logic

4. **Test Paths**: Verify all branches of conditional logic work correctly

5. **Combine with Other Rules**: Use alongside basic rules for complete grading
   - Conditional for dependency logic
   - Basic rules for independent questions

6. **Consider Alternatives**:
   - Multiple conditionals → might need AssumptionSet
   - Complex logic → might need Programmable

## Advanced Usage

### Multiple Conditions for Same Question Pair

```yaml
# Accept multiple valid if-answers leading to same then-answer
- type: CONDITIONAL
  if_question: q1_method
  if_answer: "approach_a"
  then_question: q2_result
  then_correct_answer: "result_x"
  max_points: 10.0

- type: CONDITIONAL
  if_question: q1_method
  if_answer: "approach_b"
  then_question: q2_result
  then_correct_answer: "result_x"  # Same result from different approach
  max_points: 10.0
```

### Combined with Regular Grading

```yaml
# Q1: Graded independently
- type: MULTIPLE_CHOICE
  question_id: q1_theory
  correct_answers: ["Theory A", "Theory B"]
  max_points: 5.0
  scoring_mode: all_or_nothing

# Q2: Depends on Q1 choice
- type: CONDITIONAL
  if_question: q1_theory
  if_answer: "Theory A"
  then_question: q2_application
  then_correct_answer: "Application X"
  max_points: 10.0

- type: CONDITIONAL
  if_question: q1_theory
  if_answer: "Theory B"
  then_question: q2_application
  then_correct_answer: "Application Y"
  max_points: 10.0
```

### Flexible Matching with Programmable

```yaml
# For more complex matching, combine with Programmable
- type: PROGRAMMABLE
  question_id: q2_dependent
  script: |
    q1_answer = student_answers.get('q1_method', '').lower().strip()
    q2_answer = answer.lower().strip()
    
    # Define conditional logic with flexible matching
    if 'recursion' in q1_answer:
        expected = 'recursive'
        if expected in q2_answer:
            points_awarded = max_points
            feedback = "Correct for recursion approach"
        else:
            points_awarded = 0.0
            feedback = "Inconsistent with recursion choice"
    elif 'iteration' in q1_answer:
        expected = 'loop'
        if expected in q2_answer:
            points_awarded = max_points
            feedback = "Correct for iteration approach"
        else:
            points_awarded = 0.0
            feedback = "Inconsistent with iteration choice"
    else:
        points_awarded = 0.0
        feedback = "Could not determine approach from Q1"
  max_points: 10.0
```

## Limitations

1. **Exact Matching Only**: Uses simple string comparison
   - Workaround: Normalize answers or use Programmable

2. **Binary Logic**: Only handles simple if-then
   - Workaround: Multiple rules or use Programmable for complex logic

3. **Single Condition**: Can't combine multiple if-conditions
   - Workaround: Use Programmable for AND/OR conditions

4. **No Else Clause**: Can't specify "if A then B, else C"
   - Workaround: Create separate conditional rules

## Validation Rules

The rule validates:
1. ✅ All required question IDs are provided
2. ✅ `if_question` and `then_question` are different
3. ✅ `max_points` ≥ 0

## Related Rules

- **AssumptionSet**: For multiple valid answer sets across questions
- **Composite**: For combining rules on single question
- **Programmable**: For complex conditional logic
- All basic rules: Use for independent question grading
