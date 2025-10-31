# GradeFlow Engine

A powerful Python library and CLI tool for automated grading digital exam data with support for complex grading rules.

## Features

- **Multiple Grading Rules**: Comprehensive rule system for any grading scenario
  - **ExactMatch**: Simple text matching with case-sensitivity and whitespace options
  - **NumericRange**: Numeric answers with tolerance and partial credit ranges
  - **MultipleChoice**: Single/multiple selection with flexible scoring modes
  - **Length**: Enforce word/character count constraints with partial credit
  - **Similarity**: Fuzzy string matching with multiple algorithms (Levenshtein, Jaro-Winkler, Token-based)
  - **Keyword**: Award points for required/optional keywords with flexible scoring
  - **Regex**: Powerful pattern matching with multiple match modes
  - **Conditional**: Grade based on dependencies between questions
  - **AssumptionSet**: Multiple valid answer sets with best-score selection
  - **Programmable**: Custom Python logic with sandboxed execution
  - **Composite**: Combine rules with AND/OR/WEIGHTED logic
- **Recursive Composition**: Nest composite rules for complex grading scenarios
- **YAML-First**: Human-readable rubric format with JSON support
- **Multiple Export Formats**: YAML, CSV, and Canvas LMS-compatible formats
- **Type-Safe**: Built with Pydantic v2 for robust validation and type checking
- **CLI & API**: Use as a command-line tool or import as a library
- **Secure Sandboxing**: RestrictedPython-based execution for programmable rules with time and memory limits

## Installation

### From Source
```bash
pip install -e .
```

### Development Installation
```bash
pip install -e ".[dev]"
```

## Requirements

- **Python**: 3.14 or higher
- **Platform**: Unix-like systems (Linux, macOS) for sandboxed programmable rules
  - Windows is **not supported** for programmable rules due to signal.SIGALRM limitations
  - All other rule types work on Windows

## Quick Start

### Command Line Usage

```bash
# Grade submissions using a rubric
gradeflow-engine grade rubric.yaml submissions.csv -o results.yaml

# Export detailed CSV results
gradeflow-engine grade rubric.yaml submissions.csv \
    --csv-summary results_summary.csv \
    --csv-detailed results_detailed.csv

# Export to Canvas LMS format
gradeflow-engine grade rubric.yaml submissions.csv \
    --canvas canvas_import.csv \
    --canvas-assignment-id final_exam_2024

# Validate a rubric before use
gradeflow-engine validate-rubric rubric.yaml

# Show version and help
gradeflow-engine --version
gradeflow-engine --help
```

### Python API Usage

```python
from gradeflow_engine import grade, Rubric, Submission, ExactMatchRule, NumericRangeRule

# Create a rubric with multiple rule types
rubric = Rubric(
    rubric_id="exam1",
    assessment_id="final_2024",
    name="Final Exam 2024",
    rules=[
        ExactMatchRule(
            question_id="Q1",
            correct_answer="Paris",
            max_points=10.0,
            case_sensitive=False,
            description="Capital of France"
        ),
        NumericRangeRule(
            question_id="Q2",
            correct_value=9.81,
            tolerance=0.1,
            max_points=10.0,
            unit="m/s²",
            description="Acceleration due to gravity"
        ),
    ]
)

# Create submissions
submissions = [
    Submission(
        student_id="student1",
        answers={"Q1": "paris", "Q2": "9.8"}
    ),
    Submission(
        student_id="student2",
        answers={"Q1": "London", "Q2": "10.0"}
    ),
]

# Grade them
results = grade(rubric, submissions)

# Access results
for student_result in results.results:
    print(f"{student_result.student_id}: {student_result.total_points}/{student_result.max_points} ({student_result.percentage:.1f}%)")
    for detail in student_result.grade_details:
        print(f"  {detail.question_id}: {detail.points_awarded}/{detail.max_points} - {detail.feedback}")
```

### Loading from Files

```python
from gradeflow_engine import grade_from_files, save_results_yaml, save_results_csv, export_canvas_csv

# Grade from files
results = grade_from_files(
    rubric_path="rubric.yaml",
    submissions_csv_path="submissions.csv",
    student_id_col="student_id"
)

# Save results in different formats
save_results_yaml(results, "results.yaml")
save_results_csv(results, "results_summary.csv", include_details=False)
save_results_csv(results, "results_detailed.csv", include_details=True)

# Export for Canvas LMS
export_canvas_csv(
    results=results,
    output_path="canvas_import.csv",
    assignment_id="final_exam_2024"
)
```

## Grading Rule Types

The engine supports 11 rule types that can be combined to create sophisticated grading rubrics. Each rule type is designed for specific grading scenarios.

### 1. ExactMatch

Compares student answer with expected answer using exact string matching.

**Features:**
- Case-sensitive or case-insensitive comparison
- Whitespace trimming options
- Simple and fast

**Example YAML:**
```yaml
type: EXACT_MATCH
question_id: Q1
correct_answer: "Paris"
max_points: 10.0
case_sensitive: false
trim_whitespace: true
description: "Capital of France"
```

**Example Python:**
```python
from gradeflow_engine import ExactMatchRule

rule = ExactMatchRule(
    question_id="Q1",
    correct_answer="Paris",
    max_points=10.0,
    case_sensitive=False,
    trim_whitespace=True
)
```

### 2. NumericRange

Grades numeric answers with tolerance and optional partial credit ranges.

**Features:**
- Tolerance-based grading (±tolerance)
- Partial credit ranges for different deviation levels
- Unit specification (documentation only)
- Handles scientific notation and special values

**Example YAML:**
```yaml
type: NUMERIC_RANGE
question_id: Q2
correct_value: 9.81
tolerance: 0.1
max_points: 10.0
unit: "m/s²"
partial_credit_ranges:
  - min: 9.5
    max: 9.7
    points: 5.0
  - min: 10.0
    max: 10.2
    points: 5.0
description: "Acceleration due to gravity"
```

### 3. MultipleChoice

Grades multiple choice questions with flexible scoring modes.

**Features:**
- Single or multiple correct answers
- All-or-nothing or partial credit modes
- Penalty for incorrect selections
- Case-insensitive matching

**Example YAML:**
```yaml
type: MULTIPLE_CHOICE
question_id: Q3
correct_answers: ["A", "C"]
max_points: 10.0
mode: partial_credit  # or "all_or_nothing"
partial_credit_per_correct: 5.0
penalty_per_incorrect: 2.0
case_sensitive: false
description: "Select all that apply"
```

### 4. Length

Enforces word or character count constraints with partial credit.

**Features:**
- Word or character count modes
- Minimum and maximum bounds
- Partial credit for exceeding bounds
- Configurable word separators

**Example YAML:**
```yaml
type: LENGTH
question_id: Q4
min_length: 50
max_length: 100
count_mode: words  # or "characters"
max_points: 10.0
partial_credit_factor: 0.5
description: "Essay response (50-100 words)"
```

### 5. Similarity

Fuzzy string matching using multiple similarity algorithms.

**Features:**
- Multiple algorithms: Levenshtein, Jaro-Winkler, Token Sort, Token Set, Partial Ratio
- Configurable similarity threshold
- Case-sensitive or case-insensitive
- Detailed similarity scores in feedback

**Example YAML:**
```yaml
type: SIMILARITY
question_id: Q5
correct_answer: "The mitochondria is the powerhouse of the cell"
algorithm: levenshtein  # or jaro_winkler, token_sort, token_set, partial_ratio
similarity_threshold: 0.8
max_points: 10.0
case_sensitive: false
description: "Biology short answer"
```

### 6. Keyword

Awards points based on presence of required and optional keywords.

**Features:**
- Required keywords (must have for full credit)
- Optional keywords (bonus points)
- Partial credit when some required keywords missing
- Case-sensitive or case-insensitive matching
- Point caps for optional keywords

**Example YAML:**
```yaml
type: KEYWORD
question_id: Q6
required_keywords:
  - algorithm
  - complexity
  - runtime
optional_keywords:
  - Big-O
  - optimization
  - efficiency
points_per_required: 2.0
points_per_optional: 1.0
max_optional_points: 2.0
case_sensitive: false
partial_credit: true
description: "Algorithm analysis"
```

### 7. Regex

Pattern matching using regular expressions with multiple match modes.

**Features:**
- Multiple patterns with individual point values
- Match modes: all, any, count
- Regex flags: case_sensitive, multiline, dotall
- Partial credit support
- Pattern caching for performance

**Example YAML:**
```yaml
type: REGEX
question_id: Q7
patterns:
  - '\b[A-Z]{2,}\b'     # Acronyms
  - '\d{4}'              # Year
  - 'http[s]?://\S+'     # URL
points_per_match:
  - 3.0
  - 3.0
  - 4.0
match_mode: count  # or "all", "any"
case_sensitive: false
multiline: false
partial_credit: true
description: "Format validation"
```

### 8. Conditional

Grade a question differently based on the answer to another question.

**Features:**
- Dependency-based grading
- Supports exact match or similarity-based conditions
- Flexible condition evaluation

**Example YAML:**
```yaml
type: CONDITIONAL
if_question: Q1
if_answer: "A"
then_question: Q2
then_correct_answer: "B"
points: 10.0
description: "If Q1 is A, then Q2 should be B"
```

**Example Python:**
```python
from gradeflow_engine import ConditionalRule

rule = ConditionalRule(
    if_question="Q1",
    if_answer="A",
    then_question="Q2",
    then_correct_answer="B",
    points=10.0
)
```

### 9. AssumptionSet

Support multiple valid answer sets and apply the most favorable scoring.

**Features:**
- Multiple valid interpretation sets
- Best-score or first-match modes
- Per-question point specification
- Detailed feedback on which set was applied

**Example YAML:**
```yaml
type: ASSUMPTION_SET
question_ids: ["Q8", "Q9", "Q10"]
answer_sets:
  - name: "Interpretation A"
    answers:
      Q8: "X"
      Q9: "Y"
      Q10: "Z"
  - name: "Interpretation B"
    answers:
      Q8: "P"
      Q9: "Q"
      Q10: "R"
mode: favor_best  # or "first_match"
points_per_question:
  Q8: 5.0
  Q9: 5.0
  Q10: 5.0
description: "Multiple valid answer paths"
```

**Example Python:**
```python
from gradeflow_engine import AssumptionSetRule, AnswerSet

rule = AssumptionSetRule(
    question_ids=["Q8", "Q9", "Q10"],
    answer_sets=[
        AnswerSet(
            name="Interpretation A",
            answers={"Q8": "X", "Q9": "Y", "Q10": "Z"}
        ),
        AnswerSet(
            name="Interpretation B",
            answers={"Q8": "P", "Q9": "Q", "Q10": "R"}
        ),
    ],
    mode="favor_best",
    points_per_question={"Q8": 5.0, "Q9": 5.0, "Q10": 5.0}
)
```

### 10. Programmable

Write custom Python scripts for complex grading logic with sandboxed execution.

**Features:**
- Full Python logic support (within security constraints)
- Access to all student answers
- Configurable timeout and memory limits
- RestrictedPython sandboxing
- Safe built-ins and guards

**Example YAML:**
```yaml
type: PROGRAMMABLE
question_id: Q11
script: |
  # Check for multiple keywords with weighted scoring
  keywords = {
      'algorithm': 2.5,
      'complexity': 2.5,
      'optimization': 2.0,
      'efficiency': 1.5
  }
  
  answer_lower = answer.lower()
  points_awarded = 0.0
  found = []
  
  for keyword, points in keywords.items():
      if keyword in answer_lower:
          points_awarded += points
          found.append(keyword)
  
  if found:
      feedback = f"Found keywords: {', '.join(found)}"
  else:
      feedback = "No keywords found"
max_points: 10.0
timeout_ms: 5000
memory_mb: 50
description: "Custom weighted keyword matching"
```

**Script API:**
- **Available variables:**
  - `student_answers`: Dict[str, str] - All answers from the student
  - `question_id`: str - Current question being graded
  - `answer`: str - Student's answer to the current question
- **Variables to set:**
  - `points_awarded`: float - Points to award (0 to max_points)
  - `feedback`: str - Optional feedback message

**Security Notes:**
- Scripts run in RestrictedPython sandbox
- No file system or network access
- Limited to safe built-in functions
- Time and memory limits enforced
- Requires Unix-like OS (Linux, macOS)

### 11. Composite

Combine multiple rules with AND/OR/WEIGHTED logic for complex grading scenarios.

**Features:**
- Recursive composition (nest composite rules)
- Three combination modes:
  - **AND**: All sub-rules must pass
  - **OR**: At least one sub-rule must pass
  - **WEIGHTED**: Combine weighted scores from sub-rules
- Supports all single-question rule types
- Powerful for multi-criteria grading

**Example YAML (AND mode):**
```yaml
type: COMPOSITE
question_id: Q12
combination_mode: AND
sub_rules:
  - type: LENGTH
    min_length: 50
    max_length: 200
    count_mode: words
    max_points: 5.0
  - type: KEYWORD
    required_keywords:
      - thesis
      - evidence
      - conclusion
    points_per_required: 1.67
    max_points: 5.0
max_points: 10.0
description: "Essay must meet length AND keyword requirements"
```

**Example YAML (WEIGHTED mode):**
```yaml
type: COMPOSITE
question_id: Q13
combination_mode: WEIGHTED
sub_rules:
  - type: SIMILARITY
    correct_answer: "Expected answer here"
    algorithm: levenshtein
    similarity_threshold: 0.7
    max_points: 6.0
    weight: 0.6
  - type: KEYWORD
    required_keywords: [key1, key2, key3]
    points_per_required: 1.33
    max_points: 4.0
    weight: 0.4
max_points: 10.0
description: "60% similarity + 40% keywords"
```

**Example Python:**
```python
from gradeflow_engine import CompositeRule, LengthRule, KeywordRule

rule = CompositeRule(
    question_id="Q12",
    combination_mode="AND",
    sub_rules=[
        LengthRule(
            min_length=50,
            max_length=200,
            count_mode="words",
            max_points=5.0
        ),
        KeywordRule(
            required_keywords=["thesis", "evidence", "conclusion"],
            points_per_required=1.67,
            max_points=5.0
        ),
    ],
    max_points=10.0
)
```

## CSV Format

### Submissions CSV

The submissions CSV should have a column for student ID and columns for each question.

```csv
student_id,Q1,Q2,Q3,Q4
student001,Paris,9.8,A,The mitochondria is the powerhouse
student002,London,10.0,B,Cells contain mitochondria for energy
student003,Paris,9.81,C,Mitochondria produce ATP
```

**Format requirements:**
- First row: Column headers
- Student ID column: Default is `student_id` (customizable with `--student-col`)
- Question columns: Column names must match question IDs in the rubric
- Missing answers: Leave cells empty (will be treated as empty strings)
- Special characters: CSV-escaped as needed

**Example with custom student ID column:**
```csv
SIS_ID,Q1,Q2,Q3
12345,Paris,9.8,A
23456,London,10.0,B
```

Load with: `--student-col SIS_ID`

## Output Formats

### YAML Results

```yaml
assessment_id: final_2024
rubric_id: exam1
engine_version: 0.1.0
rubric_schema_version: 1.0.0
results:
  - student_id: student001
    total_points: 85.0
    max_points: 100.0
    percentage: 85.0
    grade_details:
      - question_id: Q1
        student_answer: Paris
        correct_answer: Paris
        points_awarded: 10.0
        max_points: 10.0
        is_correct: true
        feedback: ''
        rule_applied: rule1
```

### CSV Summary

Contains overall student scores without question-level details.

```csv
student_id,total_points,max_points,percentage
student001,85.00,100.00,85.00
student002,72.00,100.00,72.00
student003,93.50,100.00,93.50
```

### CSV Detailed

Contains question-level grading details for each student.

```csv
student_id,question_id,student_answer,correct_answer,points_awarded,max_points,is_correct,feedback,rule_applied
student001,Q1,Paris,Paris,10.00,10.00,true,,exact_match_rule
student001,Q2,9.8,9.81,10.00,10.00,true,Within tolerance (0.1),numeric_range_rule
student002,Q1,London,Paris,0.00,10.00,false,Expected: Paris,exact_match_rule
```

### Canvas LMS Export

Canvas-compatible CSV format for importing grades directly into Canvas.

```csv
SIS User ID,final_2024
student001,85.00
student002,72.00
student003,93.50
```

**Usage:**
1. Generate the Canvas export file with `--canvas` option
2. Specify assignment ID with `--canvas-assignment-id`
3. Import the CSV into Canvas LMS gradebook

## API Reference

### Core Functions

#### `grade(rubric, submissions, progress_callback=None)`
Grade a list of submissions against a rubric.

**Parameters:**
- `rubric` (Rubric): The grading rubric
- `submissions` (list[Submission]): List of student submissions
- `progress_callback` (Callable[[int, int], None], optional): Progress callback function

**Returns:** `GradeOutput` - Complete grading results

**Example:**
```python
from gradeflow_engine import grade

results = grade(rubric, submissions)
print(f"Graded {len(results.results)} submissions")
```

#### `grade_from_files(rubric_path, submissions_csv_path, student_id_col='student_id')`
Grade submissions loaded from files.

**Parameters:**
- `rubric_path` (str): Path to YAML rubric file
- `submissions_csv_path` (str): Path to CSV submissions file
- `student_id_col` (str): Column name for student IDs (default: "student_id")

**Returns:** `GradeOutput` - Complete grading results

### I/O Functions

#### `load_rubric(file_path)`
Load a rubric from a YAML file.

**Returns:** `Rubric`

#### `save_rubric(rubric, file_path, indent=2)`
Save a rubric to a YAML file.

#### `load_submissions_csv(file_path, student_id_col='student_id', validate_questions=None)`
Load submissions from a CSV file.

**Returns:** `list[Submission]`

#### `save_results_yaml(results, file_path, indent=2)`
Save grading results to a YAML file.

#### `save_results_csv(results, file_path, include_details=False, encoding='utf-8')`
Save results to CSV format.

**Parameters:**
- `include_details` (bool): If True, save detailed question-level results; if False, save summary only

#### `export_canvas_csv(results, output_path, assignment_id, student_id_col='student_id', encoding='utf-8')`
Export results in Canvas LMS-compatible format.

### Models

#### `Rubric`
Complete grading rubric definition.

**Fields:**
- `rubric_id` (str): Unique rubric identifier
- `assessment_id` (str, optional): Assessment identifier
- `name` (str, optional): Rubric name
- `rules` (list[GradingRule]): List of grading rules
- `metadata` (dict, optional): Additional metadata

#### `Submission`
Student's answers to assessment questions.

**Fields:**
- `student_id` (str): Unique student identifier
- `answers` (dict[str, str]): Mapping of question_id to answer
- `metadata` (dict, optional): Additional metadata

#### `GradeOutput`
Complete grading results for all submissions.

**Fields:**
- `assessment_id` (str, optional): Assessment identifier
- `rubric_id` (str, optional): Rubric identifier
- `engine_version` (str): Engine version used
- `rubric_schema_version` (str): Schema version
- `results` (list[StudentResult]): Results for each student
- `metadata` (dict, optional): Additional metadata

#### `StudentResult`
Grading results for a single student.

**Fields:**
- `student_id` (str): Student identifier
- `total_points` (float): Total points earned
- `max_points` (float): Maximum possible points
- `percentage` (float): Percentage score (0-100)
- `grade_details` (list[GradeDetail]): Question-level details
- `metadata` (dict, optional): Additional metadata

#### `GradeDetail`
Grading details for a single question.

**Fields:**
- `question_id` (str): Question identifier
- `student_answer` (str): Student's answer
- `correct_answer` (str, optional): Expected answer
- `points_awarded` (float): Points earned
- `max_points` (float): Maximum points
- `is_correct` (bool): Whether answer was correct
- `feedback` (str): Feedback message
- `rule_applied` (str, optional): Rule that generated this result
- `metadata` (dict, optional): Additional metadata

## CLI Commands

### `grade`
Grade submissions using a rubric.

```bash
gradeflow-engine grade RUBRIC_PATH SUBMISSIONS_PATH [OPTIONS]
```

**Options:**
- `-o, --output PATH`: Output YAML file path (default: results.yaml)
- `--csv-summary PATH`: Export summary CSV
- `--csv-detailed PATH`: Export detailed CSV
- `--canvas PATH`: Export Canvas-compatible CSV
- `--canvas-assignment-id ID`: Assignment ID for Canvas export
- `--student-col NAME`: Student ID column name (default: student_id)
- `-v, --verbose`: Enable verbose logging
- `-q, --quiet`: Suppress progress output

**Examples:**
```bash
# Basic grading
gradeflow-engine grade rubric.yaml submissions.csv

# Multiple output formats
gradeflow-engine grade rubric.yaml submissions.csv \
    -o results.yaml \
    --csv-summary summary.csv \
    --csv-detailed details.csv

# Canvas export
gradeflow-engine grade rubric.yaml submissions.csv \
    --canvas canvas_import.csv \
    --canvas-assignment-id final_exam_2024
```

### `validate-rubric`
Validate a rubric file for correctness.

```bash
gradeflow-engine validate-rubric RUBRIC_PATH [OPTIONS]
```

**Options:**
- `-v, --verbose`: Show detailed validation information

**Example:**
```bash
gradeflow-engine validate-rubric rubric.yaml
```

### Global Options

- `--version`: Show version and exit
- `--help`: Show help message

## Development

### Project Structure

```
engine/
├── gradeflow_engine/          # Main package
│   ├── __init__.py            # Public API exports
│   ├── core.py                # Core grading logic
│   ├── models.py              # Pydantic models
│   ├── io.py                  # File I/O utilities
│   ├── cli.py                 # Command-line interface
│   ├── sandbox.py             # Sandboxed execution for programmable rules
│   └── rules/                 # Rule implementations
│       ├── __init__.py        # Auto-discovery and exports
│       ├── registry.py        # Rule registration system
│       ├── base.py            # Base utilities for processors
│       ├── utils.py           # Shared utilities
│       ├── exact_match/       # ExactMatch rule
│       ├── numeric_range/     # NumericRange rule
│       ├── multiple_choice/   # MultipleChoice rule
│       ├── length/            # Length rule
│       ├── similarity/        # Similarity rule
│       ├── keyword/           # Keyword rule
│       ├── regex/             # Regex rule
│       ├── conditional/       # Conditional rule
│       ├── assumption_set/    # AssumptionSet rule
│       ├── programmable/      # Programmable rule
│       └── composite/         # Composite rule
├── tests/                     # Test suite
├── examples/                  # Example files
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gradeflow_engine --cov-report=html

# Run specific test file
pytest tests/test_core.py

# Run with verbose output
pytest -v

# Run tests in parallel
pytest -n auto
```

### Code Quality

The project uses modern Python tooling for code quality:

```bash
# Format code with Ruff
ruff format .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Type checking with mypy
mypy gradeflow_engine/
```

### Adding New Rule Types

To add a new rule type:

1. Create a new directory in `gradeflow_engine/rules/`:
   ```
   gradeflow_engine/rules/my_rule/
   ├── __init__.py
   ├── model.py
   ├── processor.py
   └── README.md  (optional)
   ```

2. Define the model in `model.py`:
   ```python
   from pydantic import BaseModel, Field
   from typing import Literal

   class MyRule(BaseModel):
       type: Literal["MY_RULE"] = "MY_RULE"
       question_id: str
       max_points: float
       # ... other fields
   ```

3. Implement the processor in `processor.py`:
   ```python
   def process_my_rule(rule: "MyRule", submission: "Submission") -> "GradeDetail | None":
       # Implementation
       pass
   ```

4. Register in `__init__.py`:
   ```python
   from ..registry import rule_registry
   from .model import MyRule
   from .processor import process_my_rule

   rule_registry.register(
       rule_type="MY_RULE",
       model_class=MyRule,
       processor=process_my_rule
   )
   ```

5. Add to exports in `gradeflow_engine/rules/__init__.py`

6. Update the discriminated union in `gradeflow_engine/models.py`

The rule will be automatically discovered and available for use!

## Architecture

The engine is designed as a modular, standalone Python package:

### Design Principles

1. **Standalone Library**: Can be used independently or integrated into larger systems
2. **Type-Safe**: Pydantic v2 for runtime validation and TypeScript-compatible schemas
3. **Extensible**: Plugin-like rule system with auto-discovery
4. **Secure**: Sandboxed execution for user-provided code
5. **CLI & API**: Dual interface for flexibility

### Component Overview

- **Core Engine** (`core.py`): Pure grading logic, no I/O dependencies
- **Models** (`models.py`): Pydantic models for all data structures
- **Rule System** (`rules/`): Modular rule implementations with registry pattern
- **I/O Layer** (`io.py`): File loading/saving for YAML and CSV formats
- **CLI** (`cli.py`): Command-line interface built with Typer
- **Sandbox** (`sandbox.py`): Secure execution environment for programmable rules

### Integration Patterns

#### 1. Direct Library Usage
```python
from gradeflow_engine import grade, Rubric, Submission
# Use in your Python application
```

#### 2. CLI Scripting
```bash
# Use in shell scripts or automation
gradeflow-engine grade rubric.yaml submissions.csv
```

#### 3. Backend Integration
```python
# FastAPI example
from fastapi import FastAPI
from gradeflow_engine import grade

app = FastAPI()

@app.post("/grade")
async def grade_endpoint(rubric: Rubric, submissions: list[Submission]):
    return grade(rubric, submissions)
```

### Rule Processing Pipeline

1. **Load & Validate**: Rubric and submissions loaded and validated with Pydantic
2. **Rule Dispatch**: Each rule routed to appropriate processor via registry
3. **Grading**: Processors apply rule logic and return `GradeDetail` objects
4. **Aggregation**: Results collected and totaled for each student
5. **Output**: Results serialized to requested format(s)

### Security Model

For programmable rules, the engine implements defense-in-depth:

- **Layer 1**: RestrictedPython compilation (syntax restrictions)
- **Layer 2**: Safe globals (limited built-ins and guards)
- **Layer 3**: Time limits (SIGALRM on Unix systems)
- **Layer 4**: Memory limits (resource.setrlimit)
- **Layer 5**: No file/network access

**Production recommendation**: Run in containers with additional OS-level isolation.

## Security Notes

### Programmable Rules

Programmable rules execute user-provided Python code, which requires careful security consideration:

**Default Security Measures:**
- ✅ RestrictedPython compilation (blocks dangerous syntax)
- ✅ Safe built-ins only (no `open`, `eval`, `exec`, `__import__`)
- ✅ Guarded attribute access (no `__dict__`, `__class__`, etc.)
- ✅ Time limits (default: 5000ms, configurable)
- ✅ Memory limits (default: 50MB, configurable)
- ✅ No file system access
- ✅ No network access
- ✅ Iteration guards (prevents infinite loops)

**Platform Requirements:**
- ⚠️ **Unix-like systems only** (Linux, macOS) for full sandboxing
- ❌ **Windows not supported** for programmable rules (no `signal.SIGALRM`)

**Threat Model:**
- ✅ Protects against: Accidental infinite loops, excessive memory usage, file access
- ✅ Suitable for: Trusted users (instructors, TAs) in educational settings
- ⚠️ May not protect against: Determined attackers with knowledge of RestrictedPython bypasses

**Production Recommendations:**

For high-security environments or untrusted scripts:

1. **Container Isolation**:
   ```dockerfile
   # Run engine in isolated Docker container
   FROM python:3.14-slim
   RUN pip install gradeflow-engine
   # ... additional hardening
   ```

2. **Process Isolation**:
   - Use separate processes for grading
   - Kill processes after timeout
   - Limit container resources

3. **Additional OS Limits**:
   ```python
   # Example: stricter resource limits
   from gradeflow_engine import grade
   
   # Configure before grading
   results = grade(rubric, submissions)
   ```

4. **Input Validation**:
   - Limit script size (default: 50KB max)
   - Limit script lines (default: 1000 max)
   - Review scripts before deployment

5. **Monitoring**:
   - Log all programmable rule executions
   - Alert on timeouts or errors
   - Track resource usage

### Other Rule Types

All non-programmable rule types are safe by design:
- No code execution
- Pure data comparison and pattern matching
- No external resource access

## Examples

See the `examples/` directory for:

- **`example_rubric.yaml`**: Basic rubric with common rule types
- **`comprehensive_rubric.yaml`**: Advanced rubric showcasing all 11 rule types
- **`example_submissions.csv`**: Sample student submissions
- **`usage_examples.py`**: Python API usage examples
- **`results.yaml`**: Example output in YAML format
- **`results_summary.csv`**: Example summary CSV export
- **`results_detailed.csv`**: Example detailed CSV export
- **`canvas_export.csv`**: Example Canvas LMS export

### Quick Example

```bash
cd engine/examples
gradeflow-engine grade comprehensive_rubric.yaml example_submissions.csv -o results.yaml
```

## FAQ

### Can I use this with Canvas/Blackboard/Moodle?

Yes! The engine exports grades in formats compatible with major LMS platforms:
- **Canvas**: Use `--canvas` option for direct CSV import
- **Others**: Use CSV exports and import via LMS-specific tools

### How do I handle partial credit?

Most rule types support partial credit:
- **NumericRange**: Use `partial_credit_ranges`
- **MultipleChoice**: Use `mode: partial_credit`
- **Keyword**: Use `partial_credit: true`
- **Length**: Use `partial_credit_factor`
- **Composite (WEIGHTED)**: Combine scores with weights

### Can I grade code submissions?

Yes, use **Programmable** rules to write custom grading logic:
```python
# Example: Check for specific code patterns
script = """
if 'def ' in answer and 'return' in answer:
    points_awarded = max_points
    feedback = "Function definition found"
else:
    points_awarded = 0
    feedback = "Missing function definition"
"""
```

For complex code analysis, consider integrating with external tools.

### What about essay grading?

Use **Composite** rules to combine multiple criteria:
```yaml
type: COMPOSITE
combination_mode: WEIGHTED
sub_rules:
  - type: LENGTH
    min_length: 200
    max_length: 500
    weight: 0.2
  - type: KEYWORD
    required_keywords: [thesis, evidence, analysis]
    weight: 0.3
  - type: SIMILARITY
    correct_answer: "Expected response..."
    weight: 0.5
```

### Can I customize feedback messages?

Yes, several approaches:
1. **Rule descriptions**: Add `description` field to any rule
2. **Programmable rules**: Generate custom feedback in Python
3. **Post-processing**: Modify `GradeOutput` before saving

## Troubleshooting

### Issue: "Windows not supported" error for programmable rules

**Cause**: Programmable rules require Unix signals not available on Windows.

**Solutions:**
- Use Windows Subsystem for Linux (WSL2)
- Use Docker with Linux container
- Avoid programmable rules (use other rule types)

### Issue: Rubric validation errors

**Cause**: Invalid YAML syntax or model validation failures.

**Solutions:**
- Use `validate-rubric` command before grading
- Check error messages for specific field issues
- Ensure all required fields are present
- Verify question IDs match between rubric and submissions

### Issue: Low test coverage warnings

**Cause**: Some rule types not covered in test submissions.

**Solutions:**
- Add test cases for all question IDs in your rubric
- Use `validate-rubric` to identify missing questions
- Review submission CSV for completeness

### Issue: Slow grading performance

**Solutions:**
- Reduce programmable rule timeouts if safe
- Use simpler rule types when possible
- Profile with `-v` flag to identify slow rules
- Consider parallel processing for large datasets

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Here's how to contribute:

### Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include Python version, OS, and engine version
- Provide minimal reproducible examples
- For security issues, see SECURITY.md (if available) or contact maintainers privately

### Contributing Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linters (`ruff check .` and `mypy gradeflow_engine/`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints for all functions
- Add docstrings for public APIs
- Write tests for new features
- Update README for new rule types

### Testing

- Maintain >90% test coverage
- Add tests for new rule types
- Test edge cases and error conditions
- Use pytest fixtures for common test data
