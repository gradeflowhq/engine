# GradeFlow Engine

A powerful Python library and CLI tool for automated grading digital exam data with support for complex grading rules.

## Features

- **Multiple Grading Rules**: Comprehensive rule system for any grading scenario
  - **ExactMatch**: Simple text matching
  - **NumericRange**: Numeric answers with min/max ranges
  - **MultipleChoice**: Single/multiple selection with flexible scoring modes
  - **Length**: Enforce word/character count constraints
  - **Similarity**: Fuzzy string matching with multiple algorithms (Levenshtein, Jaro-Winkler, Token-based)
  - **Keyword**: Simple keywords matching
  - **Regex**: Powerful pattern matching with multiple match modes
  - **Conditional**: Grade based on dependencies between questions
  - **AssumptionSet**: Multiple valid answer sets
  - **Programmable**: Custom Python grading logic
  - **Composite**: Combine multiple rules
- **Recursive Composition**: Nest composite rules for complex grading scenarios
- **Assessment Schema**: Define and validate question types, options, and constraints
  - Automatic schema inference from submission data
  - Rubric validation against schemas
  - Support for CHOICE, NUMERIC, and TEXT question types
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

- **Python**: 3.11 or higher
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
            answer="Paris",
            max_points=10.0,
        ),
        NumericRangeRule(
            question_id="Q2",
            min_value=9.71,
            max_value=9.91,
            max_points=10.0,
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
student001,Q2,9.8,9.81,10.00,10.00,true,Within range [9.71-9.91],numeric_range_rule
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

## Assessment Schema

The engine supports **assessment schemas** that define the structure and constraints of assessments. Schemas specify question types, valid options, and constraints, enabling:
- Validation of rubrics against expected question types
- Automatic schema inference from submission data
- Type-safe assessment design

### Schema Models

#### Question Types

**ChoiceQuestionSchema** - Multiple choice or multiple response questions:
```python
from gradeflow_engine import ChoiceQuestionSchema

schema = ChoiceQuestionSchema(
    type="CHOICE",
    question_id="Q1",
    options=["A", "B", "C", "D"],
    allow_multiple=False  # True for MRQ, False for MCQ
)
```

**NumericQuestionSchema** - Numeric answer questions:
```python
from gradeflow_engine import NumericQuestionSchema

schema = NumericQuestionSchema(
    type="NUMERIC",
    question_id="Q2",
    numeric_range=(9.5, 10.0)  # Optional expected range
)
```

**TextQuestionSchema** - Free-text answer questions:
```python
from gradeflow_engine import TextQuestionSchema

schema = TextQuestionSchema(
    type="TEXT",
    question_id="Q3",
    max_length=500  # Optional character limit
)
```

#### AssessmentSchema

Complete schema for an assessment:
```python
from gradeflow_engine import (
    AssessmentSchema,
    ChoiceQuestionSchema,
    NumericQuestionSchema,
    TextQuestionSchema
)

schema = AssessmentSchema(
    name="Final Exam 2024",
    questions={
        "Q1": ChoiceQuestionSchema(
            question_id="Q1",
            options=["A", "B", "C", "D"],
            allow_multiple=False
        ),
        "Q2": NumericQuestionSchema(
            question_id="Q2",
            numeric_range=(9.5, 10.5)
        ),
        "Q3": TextQuestionSchema(
            question_id="Q3",
            max_length=1000
        ),
    }
)
```

### Schema Inference

Automatically infer schemas from submission data:

```python
from gradeflow_engine import infer_schema_from_submissions, load_submissions_csv

# Load submissions
submissions = load_submissions_csv("submissions.csv")

# Infer schema from answer patterns
schema = infer_schema_from_submissions(
    submissions,
    name="Inferred Assessment"
)

# Save for later use
from gradeflow_engine import save_schema
save_schema(schema, "schema.yaml")
```

**CLI Usage:**
```bash
# Infer schema from submissions
gradeflow-engine infer-schema submissions.csv -o schema.yaml

# With custom assessment name
gradeflow-engine infer-schema submissions.csv \
    -o schema.yaml \
    --name "Midterm Exam"

# Show detailed inference info
gradeflow-engine infer-schema submissions.csv -o schema.yaml -v
```

### Schema Validation

Validate rubrics against schemas to ensure compatibility:

```python
from gradeflow_engine import (
    validate_rubric_against_schema,
    load_rubric,
    load_schema
)

# Load rubric and schema
rubric = load_rubric("rubric.yaml")
schema = load_schema("schema.yaml")

# Validate
errors = validate_rubric_against_schema(rubric, schema)

if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Rubric is valid!")
```

**CLI Usage:**
```bash
# Validate schema file
gradeflow-engine validate-schema schema.yaml

# Validate rubric against schema
gradeflow-engine validate-schema schema.yaml --rubric rubric.yaml

# Show detailed schema info
gradeflow-engine validate-schema schema.yaml -v
```

### Schema YAML Format

```yaml
name: "Final Exam 2024"
questions:
  Q1:
    type: CHOICE
    question_id: Q1
    options:
      - A
      - B
      - C
      - D
    allow_multiple: false
  Q2:
    type: NUMERIC
    question_id: Q2
    min_value: 9.5
    max_value: 10.5
  Q3:
    type: TEXT
    question_id: Q3
    max_length: 1000
metadata:
  course: "PHYS 101"
  semester: "Fall 2024"
```

### Inference Algorithm

The schema inference system analyzes submission data to automatically detect:

**Choice Questions:**
- Few unique answers (≤10)
- Very short answers (avg ≤2 characters)
- Identifies whether multiple selections are allowed (comma/semicolon separated)

**Numeric Questions:**
- Answers are parseable as numbers (≥80% numeric)
- Infers reasonable min/max range from data

**Text Questions:**
- Default for all other answer patterns
- Longer, varied responses

### Use Cases

1. **Rubric Validation**: Ensure grading rules match expected question types
2. **Assessment Design**: Define question structure before creating rubrics
3. **LMS Integration**: Import assessment structure from external systems
4. **Quality Assurance**: Verify submission data matches expected format

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

#### `load_schema(file_path)`
Load an assessment schema from a YAML file.

**Returns:** `AssessmentSchema`

**Example:**
```python
from gradeflow_engine import load_schema

schema = load_schema("schema.yaml")
print(f"Loaded schema with {len(schema.questions)} questions")
```

#### `save_schema(schema, file_path, indent=2)`
Save an assessment schema to a YAML file.

**Parameters:**
- `schema` (AssessmentSchema): Schema to save
- `file_path` (str): Output file path
- `indent` (int): YAML indentation level

**Example:**
```python
from gradeflow_engine import save_schema

save_schema(schema, "schema.yaml")
```

### Schema Functions

#### `infer_schema_from_submissions(submissions, name='Inferred Assessment')`
Automatically infer assessment schema from submission data.

**Parameters:**
- `submissions` (list[Submission]): List of student submissions
- `name` (str): Name for the inferred schema

**Returns:** `AssessmentSchema` - Inferred schema with question types and constraints

**Example:**
```python
from gradeflow_engine import infer_schema_from_submissions, load_submissions_csv

submissions = load_submissions_csv("submissions.csv")
schema = infer_schema_from_submissions(submissions, name="Final Exam")
```

#### `validate_rubric_against_schema(rubric, schema)`
Validate a rubric against an assessment schema.

**Parameters:**
- `rubric` (Rubric): Rubric to validate
- `schema` (AssessmentSchema): Schema to validate against

**Returns:** `list[str]` - List of validation errors (empty if valid)

**Example:**
```python
from gradeflow_engine import validate_rubric_against_schema, load_rubric, load_schema

rubric = load_rubric("rubric.yaml")
schema = load_schema("schema.yaml")
errors = validate_rubric_against_schema(rubric, schema)

if errors:
    print("Validation failed:")
    for error in errors:
        print(f"  - {error}")
```

#### `infer_mcq_options(answers, min_frequency=0.05)`
Infer multiple choice options from answer list.

**Parameters:**
- `answers` (list[str]): List of student answers
- `min_frequency` (float): Minimum frequency for option inclusion (0.0-1.0)

**Returns:** `list[str]` - Inferred options

#### `infer_numeric_range(answers)`
Infer reasonable numeric range from answer list.

**Parameters:**
- `answers` (list[str]): List of student answers

**Returns:** `tuple[float, float] | None` - (min, max) range or None if not numeric

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

#### `AssessmentSchema`
Complete schema for an assessment defining question types and constraints.

**Fields:**
- `name` (str): Assessment name
- `questions` (dict[str, QuestionSchema]): Map of question_id to question schema
- `metadata` (dict, optional): Additional metadata

#### `QuestionSchema`
Base type for question schemas (discriminated union of all question types).

Can be one of:
- `ChoiceQuestionSchema`: Multiple choice questions
- `NumericQuestionSchema`: Numeric answer questions
- `TextQuestionSchema`: Free-text answer questions

#### `ChoiceQuestionSchema`
Schema for multiple choice or multiple response questions.

**Fields:**
- `type` (Literal["CHOICE"]): Always "CHOICE"
- `question_id` (str): Question identifier
- `options` (list[str]): Valid answer options
- `allow_multiple` (bool): Whether multiple selections allowed (MRQ vs MCQ)
- `metadata` (dict, optional): Additional metadata

#### `NumericQuestionSchema`
Schema for numeric answer questions.

**Fields:**
- `type` (Literal["NUMERIC"]): Always "NUMERIC"
- `question_id` (str): Question identifier
- `metadata` (dict, optional): Additional metadata

#### `TextQuestionSchema`
Schema for free-text answer questions.

**Fields:**
- `type` (Literal["TEXT"]): Always "TEXT"
- `question_id` (str): Question identifier
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

### `infer-schema`
Automatically infer assessment schema from submission data.

```bash
gradeflow-engine infer-schema SUBMISSIONS_PATH [OPTIONS]
```

**Options:**
- `-o, --output PATH`: Output schema YAML file path (default: schema.yaml)
- `-n, --name NAME`: Assessment name (default: "Inferred Assessment")
- `-s, --student-col NAME`: Student ID column name (default: student_id)
- `-v, --verbose`: Show detailed schema information

**Examples:**
```bash
# Basic schema inference
gradeflow-engine infer-schema submissions.csv -o schema.yaml

# With custom name
gradeflow-engine infer-schema submissions.csv \
    -o schema.yaml \
    --name "Midterm Exam"

# Verbose output
gradeflow-engine infer-schema submissions.csv -o schema.yaml -v
```

### `validate-schema`
Validate an assessment schema file and optionally validate a rubric against it.

```bash
gradeflow-engine validate-schema SCHEMA_PATH [OPTIONS]
```

**Options:**
- `-r, --rubric PATH`: Optional rubric file to validate against schema
- `-v, --verbose`: Show detailed validation information

**Examples:**
```bash
# Validate schema file
gradeflow-engine validate-schema schema.yaml

# Validate rubric against schema
gradeflow-engine validate-schema schema.yaml --rubric rubric.yaml

# Verbose output
gradeflow-engine validate-schema schema.yaml -v
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
│   ├── models.py              # Pydantic models for rubrics and results
│   ├── schema.py              # Assessment schema models and validation
│   ├── io.py                  # File I/O utilities
│   ├── cli.py                 # Command-line interface
│   ├── sandbox.py             # Sandboxed execution for programmable rules
│   ├── types.py               # Type definitions
│   ├── protocols.py           # Protocol definitions
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
   FROM python:3.11-slim
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

Use **Composite** rules to combine multiple criteria.

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
