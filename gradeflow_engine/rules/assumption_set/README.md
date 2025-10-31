# Assumption Set Rule

## Overview

The Assumption Set rule handles scenarios where multiple valid interpretations or approaches exist for a problem, each leading to a different set of correct answers. The rule evaluates a student's answers against all possible answer sets and awards points based on the best-matching set.

## Use Cases

- **Ambiguous Problems**: Question wording allows multiple valid interpretations
- **Multiple Methods**: Different valid approaches yield different answers
- **Unit Choices**: Different unit systems produce different numerical answers
- **Assumption-Based Problems**: Explicit or implicit assumptions affect correct answers
- **Fair Grading**: Give credit for any valid approach, not just one "official" answer key

## Features

- **Multiple Answer Sets**: Define several complete, valid answer sets
- **Flexible Evaluation**: Two modes for selecting which set to use
- **Automatic Optimization**: Finds best-matching answer set for each student
- **Named Sets**: Label each answer set for clarity and debugging
- **Cross-Question Support**: Evaluate multiple related questions together

## Configuration

### Required Fields

- `type`: Must be `"ASSUMPTION_SET"`
- `question_ids`: List of question IDs in this group
- `answer_sets`: List of AnswerSet objects, each containing valid answers

### AnswerSet Structure

Each answer set contains:
- `name`: Descriptive label for this answer set
- `answers`: Dictionary mapping `question_id` → `correct_answer`

### Optional Fields

- `mode` (default: `"favor_best"`): How to select answer set
  - `"favor_best"`: Choose set that maximizes student's score
  - `"first_match"`: Use first set where all answers match
- `points_per_question`: Dictionary of `question_id` → points (default: 1.0 per question)
- `description`: Human-readable description of the rule

## Example

### Basic Assumption Set

```yaml
type: ASSUMPTION_SET
question_ids: [q1_interpretation, q2_calculation, q3_unit]
mode: favor_best
answer_sets:
  - name: "SI Units Interpretation"
    answers:
      q1_interpretation: "Use SI units"
      q2_calculation: "9.8"
      q3_unit: "m/s²"
  
  - name: "Imperial Units Interpretation"
    answers:
      q1_interpretation: "Use imperial units"
      q2_calculation: "32.2"
      q3_unit: "ft/s²"

points_per_question:
  q1_interpretation: 3.0
  q2_calculation: 5.0
  q3_unit: 2.0
description: "Accept either SI or imperial unit system"
```

### Multiple Valid Approaches

```yaml
type: ASSUMPTION_SET
question_ids: [q1_method, q2_step1, q3_step2, q4_result]
mode: favor_best
answer_sets:
  - name: "Dynamic Programming Approach"
    answers:
      q1_method: "dynamic programming"
      q2_step1: "build memoization table"
      q3_step2: "fill table bottom-up"
      q4_result: "42"
  
  - name: "Greedy Algorithm Approach"
    answers:
      q1_method: "greedy algorithm"
      q2_step1: "sort by value/weight ratio"
      q3_step2: "select items in order"
      q4_result: "38"
  
  - name: "Brute Force Approach"
    answers:
      q1_method: "brute force"
      q2_step1: "enumerate all combinations"
      q3_step2: "find maximum"
      q4_result: "42"

points_per_question:
  q1_method: 5.0
  q2_step1: 10.0
  q3_step2: 10.0
  q4_result: 15.0
```

### Ambiguous Problem Interpretation

```yaml
type: ASSUMPTION_SET
question_ids: [q1_assumption, q2_answer_a, q3_answer_b]
mode: favor_best
answer_sets:
  - name: "Interpretation A: Problem assumes frictionless surface"
    answers:
      q1_assumption: "frictionless"
      q2_answer_a: "10.0"
      q3_answer_b: "5.0"
  
  - name: "Interpretation B: Problem includes friction coefficient 0.2"
    answers:
      q1_assumption: "friction = 0.2"
      q2_answer_a: "8.4"
      q3_answer_b: "3.6"

points_per_question:
  q1_assumption: 2.0
  q2_answer_a: 5.0
  q3_answer_b: 5.0
description: "Accept either interpretation of friction"
```

## Behavior

### Mode: "favor_best"

Evaluate student against all answer sets and choose the one that maximizes their score.

**Algorithm:**
```python
best_score = 0
best_set = None

for answer_set in answer_sets:
    score = 0
    for question_id in question_ids:
        if student_answers[question_id] == answer_set.answers[question_id]:
            score += points_per_question[question_id]
    
    if score > best_score:
        best_score = score
        best_set = answer_set

points_awarded = best_score
```

**Characteristics:**
- Most generous to students
- Awards maximum possible points
- Good when fairness is paramount
- Student gets benefit of the doubt

### Mode: "first_match"

Use the first answer set where ALL student answers match.

**Algorithm:**
```python
for answer_set in answer_sets:
    all_match = True
    for question_id in question_ids:
        if student_answers[question_id] != answer_set.answers[question_id]:
            all_match = False
            break
    
    if all_match:
        # Perfect match with this set
        points_awarded = sum(points_per_question.values())
        return
    
# No perfect match found
points_awarded = 0.0
```

**Characteristics:**
- All-or-nothing within each set
- Order of sets matters
- Stricter than favor_best
- Good when consistency across all questions is required

## Examples

### Example 1: Unit System Choice (favor_best)

**Configuration:**
```yaml
question_ids: [q1_unit, q2_gravity, q3_result]
mode: favor_best
answer_sets:
  - name: "Metric"
    answers:
      q1_unit: "meters"
      q2_gravity: "9.81"
      q3_result: "98.1"
  - name: "Imperial"
    answers:
      q1_unit: "feet"
      q2_gravity: "32.2"
      q3_result: "322"
points_per_question:
  q1_unit: 2.0
  q2_gravity: 4.0
  q3_result: 4.0
```

**Grading:**
| Student Answers | Metric Score | Imperial Score | Best | Points |
|-----------------|--------------|----------------|------|--------|
| meters, 9.81, 98.1 | 2+4+4=10 | 2+0+0=0 | Metric | 10.0 |
| feet, 32.2, 322 | 0+0+0=0 | 2+4+4=10 | Imperial | 10.0 |
| meters, 9.81, 322 | 2+4+0=6 | 0+0+4=4 | Metric | 6.0 |
| meters, 32.2, 98.1 | 2+0+4=6 | 0+4+0=4 | Metric | 6.0 |

### Example 2: Problem Approach (first_match)

**Configuration:**
```yaml
question_ids: [q1_method, q2_answer]
mode: first_match
answer_sets:
  - name: "Method A"
    answers:
      q1_method: "A"
      q2_answer: "100"
  - name: "Method B"
    answers:
      q1_method: "B"
      q2_answer: "150"
points_per_question:
  q1_method: 5.0
  q2_answer: 10.0
```

**Grading:**
| Student Answers | Set A Match? | Set B Match? | Points |
|-----------------|--------------|--------------|--------|
| A, 100 | ✓ All match | - | 15.0 (perfect) |
| B, 150 | ✗ | ✓ All match | 15.0 (perfect) |
| A, 150 | ✗ | ✗ | 0.0 (no perfect match) |
| B, 100 | ✗ | ✗ | 0.0 (no perfect match) |

### Example 3: Three Valid Interpretations

**Configuration:**
```yaml
question_ids: [q1, q2, q3]
mode: favor_best
answer_sets:
  - name: "Interpretation 1"
    answers: {q1: "A", q2: "X", q3: "1"}
  - name: "Interpretation 2"
    answers: {q1: "B", q2: "Y", q3: "2"}
  - name: "Interpretation 3"
    answers: {q1: "C", q2: "Z", q3: "3"}
points_per_question: {q1: 3.0, q2: 3.0, q3: 4.0}
```

**Student Answer: A, Y, 1**

Scoring:
- Set 1: q1=✓(3), q2=✗(0), q3=✓(4) = **7.0**
- Set 2: q1=✗(0), q2=✓(3), q3=✗(0) = **3.0**
- Set 3: q1=✗(0), q2=✗(0), q3=✗(0) = **0.0**

**Best: Set 1 with 7.0 points**

## When to Use

✅ **Good For:**
- Problems with multiple valid interpretations
- Different solution methods producing different answers
- Unit system choices affecting all answers
- Ambiguous or poorly worded original questions
- Retroactive rubric adjustments
- Fair grading when problem was unclear

❌ **Not Ideal For:**
- Independent questions (use basic rules)
- Questions with single correct answer (use basic rules)
- Partial credit within one approach (use Composite)
- If-then dependencies (use Conditional)

## Tips

1. **Use "favor_best" by Default**: More fair to students, gives benefit of doubt

2. **Use "first_match" When Consistency Required**: When mixing answer sets doesn't make sense

3. **Name Sets Descriptively**: Helps with debugging and understanding results

4. **Cover All Valid Approaches**: Don't favor one interpretation over others

5. **Set Appropriate Points**: Use `points_per_question` to weight questions differently

6. **Document Assumptions**: Use `description` and set names to explain logic

7. **Test Thoroughly**: Verify all combinations work as expected

## Advanced Usage

### Partial Answer Sets

```yaml
# Not all questions need to be in every set
# Missing questions are treated as "any answer acceptable"
answer_sets:
  - name: "Approach 1"
    answers:
      q1_method: "Method A"
      q2_result: "100"
      # q3_explanation: any answer OK
  - name: "Approach 2"
    answers:
      q1_method: "Method B"
      q2_result: "150"
      q3_explanation: "Because of X"
```

### Weighted Questions

```yaml
# Some questions more important than others
points_per_question:
  q1_interpretation: 2.0   # Less critical
  q2_main_calculation: 10.0  # Most important
  q3_unit: 1.0  # Minor
```

### Combined with Other Rules

```yaml
# Use AssumptionSet for some questions
- type: ASSUMPTION_SET
  question_ids: [q1, q2, q3]
  answer_sets: [...]

# Use regular rules for independent questions
- type: KEYWORD
  question_id: q4_explanation
  required_keywords: [concept_a, concept_b]
  points_per_required: 5.0
```

## Mode Comparison

| Aspect | favor_best | first_match |
|--------|------------|-------------|
| Grading | Partial credit possible | All-or-nothing per set |
| Fairness | Maximum generosity | Stricter |
| Mixed answers | Awards best combination | Requires perfect set match |
| Use case | Ambiguous problems | Clear distinct approaches |
| Student benefit | High | Lower |

## Validation Rules

The rule validates:
1. ✅ At least one answer set is required
2. ✅ All answer sets have `name` and `answers`
3. ✅ Each answer set covers the same questions (or subset)
4. ✅ All `question_ids` are listed
5. ✅ Points per question are ≥ 0

## Calculation Details

### Default Points

If `points_per_question` not specified:
- Each question worth 1.0 point by default
- Total possible = number of questions

### Max Points Calculation

```python
max_points = sum(points_per_question.values())
```

### Partial Credit (favor_best only)

Each question graded independently:
- Match correct answer in best set → full points for that question  
- Don't match → 0 points for that question
- Sum all question points for final score

## Related Rules

- **Conditional**: For if-then logic between specific questions
- **Composite**: For combining criteria on single question
- **Programmable**: For very complex multi-question logic
- All basic rules: For independent question grading
