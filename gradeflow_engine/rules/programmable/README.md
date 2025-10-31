# Programmable Rule

## Overview

The Programmable rule allows you to implement custom grading logic using Python scripts. This is the most flexible rule type, enabling complex evaluation scenarios that go beyond what the standard rules can handle.

## Use Cases

- **Custom Algorithms**: Implement specialized grading logic
- **Complex Validation**: Multi-step validation processes
- **Domain-Specific Grading**: Subject-specific evaluation (math proofs, code snippets)
- **Cross-Question Logic**: Use answers from multiple questions
- **Advanced Calculations**: Custom scoring formulas
- **External Validation**: Parse and validate structured data

## Features

- **Full Python Power**: Execute arbitrary Python code (with restrictions)
- **Access to All Answers**: Read any student answer in the submission
- **Flexible Scoring**: Implement any scoring algorithm
- **Custom Feedback**: Generate detailed feedback messages
- **Sandboxed Execution**: Safe execution environment with timeouts and memory limits

## Configuration

### Required Fields

- `type`: Must be `"PROGRAMMABLE"`
- `question_id`: The ID of the question to grade
- `script`: Python script to execute for grading
- `max_points`: Maximum points available

### Optional Fields

- `timeout_ms` (default: `5000`): Script execution timeout in milliseconds (100-30000)
- `memory_mb` (default: `50`): Memory limit in megabytes (10-500)
- `description`: Human-readable description of the rule

## Script Environment

### Available Variables

Your script has access to:

```python
student_answers: Dict[str, str]  # All student answers {question_id: answer}
question_id: str                  # The current question being graded
answer: str                       # The student's answer to this question
```

### Required Output Variables

Your script must set:

```python
points_awarded: float  # Points to award (0 to max_points)
feedback: str          # Optional feedback message (can be empty string)
```

### Example Script Structure

```python
# Read the student's answer
response = answer.strip().lower()

# Implement grading logic
if some_condition(response):
    points_awarded = max_points
    feedback = "Excellent work!"
else:
    points_awarded = 0.0
    feedback = "Please review the concept."
```

## Example

### Basic Script

```yaml
type: PROGRAMMABLE
question_id: q18_even_odd
script: |
  # Check if answer is a number and correctly identifies even/odd
  try:
      num = int(answer)
      if num % 2 == 0 and "even" in answer.lower():
          points_awarded = max_points
          feedback = "Correct! The number is even."
      elif num % 2 != 0 and "odd" in answer.lower():
          points_awarded = max_points
          feedback = "Correct! The number is odd."
      else:
          points_awarded = 0.0
          feedback = "Incorrect classification."
  except:
      points_awarded = 0.0
      feedback = "Invalid answer format."
max_points: 5.0
timeout_ms: 3000
description: "Check if number is even or odd"
```

### Cross-Question Validation

```yaml
type: PROGRAMMABLE
question_id: q19_calculation
script: |
  # Validate that answer matches inputs from other questions
  try:
      num1 = float(student_answers.get('q1_input', '0'))
      num2 = float(student_answers.get('q2_input', '0'))
      expected = num1 + num2
      actual = float(answer)
      
      diff = abs(expected - actual)
      if diff < 0.01:
          points_awarded = max_points
          feedback = f"Correct! {num1} + {num2} = {actual}"
      elif diff < 1.0:
          points_awarded = max_points * 0.7
          feedback = f"Close. Expected {expected}, got {actual}"
      else:
          points_awarded = 0.0
          feedback = f"Incorrect. Check your calculation."
  except:
      points_awarded = 0.0
      feedback = "Invalid numeric format."
max_points: 10.0
```

### JSON Validation

```yaml
type: PROGRAMMABLE
question_id: q20_json
script: |
  import json
  
  try:
      data = json.loads(answer)
      
      # Check required fields
      required = ['name', 'age', 'email']
      if all(field in data for field in required):
          # Validate email format
          email = data['email']
          if '@' in email and '.' in email:
              points_awarded = max_points
              feedback = "Valid JSON with all required fields."
          else:
              points_awarded = max_points * 0.7
              feedback = "Valid JSON but email format incorrect."
      else:
          points_awarded = max_points * 0.5
          feedback = "JSON valid but missing required fields."
  except json.JSONDecodeError:
      points_awarded = 0.0
      feedback = "Invalid JSON format."
max_points: 15.0
timeout_ms: 5000
```

## Behavior

### Execution Process

1. **Sandbox Setup**: Create restricted Python environment
2. **Variable Injection**: Inject `student_answers`, `question_id`, `answer`, `max_points`
3. **Script Execution**: Run the script with timeout and memory limits
4. **Extract Results**: Retrieve `points_awarded` and `feedback`
5. **Validation**: Ensure points are within 0 to `max_points`
6. **Return**: Return grading result

### Safety Features

- **Timeout Protection**: Scripts cannot run longer than `timeout_ms`
- **Memory Limits**: Controlled memory usage
- **Restricted Imports**: Limited access to Python standard library
- **No File I/O**: Cannot read/write files
- **No Network**: Cannot make network requests
- **No System Calls**: Cannot execute system commands

### Error Handling

If script fails:
- Exception caught and logged
- Default: `points_awarded = 0.0`
- Feedback includes error message (if in debug mode)

## Examples

### Example 1: Pattern Matching

```python
# Grade answer based on custom pattern
import re

pattern = r'^[A-Z]{3}-\d{4}$'
if re.match(pattern, answer):
    points_awarded = max_points
    feedback = "Correct ID format."
else:
    points_awarded = 0.0
    feedback = "ID must be format: ABC-1234"
```

### Example 2: Mathematical Expression

```python
# Evaluate mathematical expression
import re

# Extract numbers
numbers = re.findall(r'\d+', answer)
if len(numbers) >= 2:
    nums = [int(n) for n in numbers]
    if '+' in answer:
        result = sum(nums)
        feedback = f"Sum calculated: {result}"
        points_awarded = max_points
    else:
        points_awarded = 0.0
        feedback = "Addition not detected."
else:
    points_awarded = 0.0
    feedback = "Please provide at least two numbers."
```

### Example 3: Conditional Logic from Multiple Questions

```python
# Award points based on consistency across questions
q1 = student_answers.get('q1_theory', '').lower()
q2 = student_answers.get('q2_application', '').lower()

# If student chose theory A, application must be compatible
if 'theory_a' in q1:
    if 'application_x' in q2:
        points_awarded = max_points
        feedback = "Consistent choice!"
    else:
        points_awarded = 0.0
        feedback = "Application doesn't match chosen theory."
elif 'theory_b' in q1:
    if 'application_y' in q2:
        points_awarded = max_points
        feedback = "Consistent choice!"
    else:
        points_awarded = 0.0
        feedback = "Application doesn't match chosen theory."
else:
    points_awarded = 0.0
    feedback = "Theory not recognized."
```

### Example 4: Partial Credit Scaling

```python
# Graduated scoring based on answer quality
answer_lower = answer.lower()
score = 0

# Check for key concepts (2 points each)
concepts = ['concept_a', 'concept_b', 'concept_c']
for concept in concepts:
    if concept in answer_lower:
        score += 2

# Check length (2 points)
if len(answer.split()) >= 20:
    score += 2

# Check conclusion (2 points)
if any(word in answer_lower for word in ['conclusion', 'summary', 'therefore']):
    score += 2

points_awarded = min(score, max_points)
feedback = f"Score breakdown: {score}/{max_points} based on content analysis."
```

## When to Use

✅ **Good For:**
- Complex validation logic
- Cross-question dependencies
- Custom scoring algorithms
- Domain-specific evaluation
- Structured data validation (JSON, XML, CSV)
- Mathematical proofs or derivations
- Code snippet validation

❌ **Not Ideal For:**
- Simple exact matches (use ExactMatch)
- Standard keyword checking (use Keyword)
- Basic numeric ranges (use NumericRange)
- Regular patterns (use Regex)
- Standard similarity (use Similarity)

## Tips

1. **Keep Scripts Simple**: Complex logic is harder to debug and maintain
2. **Handle Exceptions**: Always use try-except blocks
3. **Validate Input**: Check for None, empty strings, invalid formats
4. **Set Reasonable Timeouts**: Complex scripts may need more time
5. **Test Thoroughly**: Test with various student responses
6. **Provide Clear Feedback**: Help students understand their grade
7. **Document Your Logic**: Add comments explaining grading criteria
8. **Use Other Rules First**: Only use Programmable when necessary

## Security Considerations

The script runs in a **sandboxed environment** with:

✅ **Allowed:**
- Basic Python syntax and operations
- String manipulation
- Math operations
- Regular expressions
- JSON parsing
- Limited standard library imports

❌ **Restricted:**
- File system access
- Network operations
- System commands
- Dangerous imports (os, subprocess, etc.)
- Infinite loops (timeout protection)
- Excessive memory usage

## Performance Tips

1. **Avoid Heavy Computation**: Keep scripts lightweight
2. **Set Appropriate Timeouts**: Balance between allowing computation and preventing hangs
3. **Minimize Memory Usage**: Large data structures count against memory limit
4. **Cache When Possible**: If checking multiple answers, compute once

## Debugging

To debug scripts:

1. **Test Standalone**: Run script outside the rule with sample data
2. **Add Print Statements**: Use feedback variable to debug
3. **Check Error Messages**: Review execution errors
4. **Start Simple**: Begin with basic logic, add complexity gradually
5. **Validate Variables**: Ensure `points_awarded` and `feedback` are set

## Advanced Usage

### Using Helper Functions

```python
def validate_email(email):
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    import re
    pattern = r'^\d{3}-\d{3}-\d{4}$'
    return re.match(pattern, phone) is not None

# Main grading logic
email_valid = validate_email(answer)
phone = student_answers.get('q_phone', '')
phone_valid = validate_phone(phone)

if email_valid and phone_valid:
    points_awarded = max_points
    feedback = "All contact info valid."
elif email_valid:
    points_awarded = max_points * 0.6
    feedback = "Email valid, phone invalid."
else:
    points_awarded = 0.0
    feedback = "Invalid email format."
```

### State Machine Example

```python
# Grade based on state transitions
states = answer.split('->')
valid_transitions = {
    'START': ['A', 'B'],
    'A': ['C', 'END'],
    'B': ['C'],
    'C': ['END']
}

is_valid = True
for i in range(len(states) - 1):
    current = states[i].strip()
    next_state = states[i + 1].strip()
    
    if next_state not in valid_transitions.get(current, []):
        is_valid = False
        break

if is_valid:
    points_awarded = max_points
    feedback = "Valid state transition!"
else:
    points_awarded = 0.0
    feedback = "Invalid state transition detected."
```

## Related Rules

- **Composite**: Combine programmable logic with standard rules
- **Conditional**: For simpler if-then logic
- **Regex**: For pattern matching without full programming
- All other rules: Use them first, only resort to Programmable when needed
