# GradeFlow Engine

GradeFlow Engine is a modular grading engine designed to ingest submissions, infer or load question sets, validate and apply rubrics, compute grades, and export results. It emphasizes extensibility through registries, safety via pydantic validation, and composable rule-based grading.

## Key Features

- Pluggable adapters and serializers for submissions, question sets, and rubrics via registries
- Automatic question type inference from raw submissions
- Comprehensive rule-based grading system with 15+ rule types
- Safe execution of user code (inside container) with timeouts for programmable/programming rules
- CLI for common workflows with rich terminal output
- Python API for scripted pipelines
- Deterministic serialization of answers and graded results
- Support for external data sources (Examplify)

## Installation

```bash
pip install -e .
# or use your environment manager of choice
```

## Project Structure

- `core.py`: High-level API and pipeline orchestration
- `cli.py`: Typer-based CLI with rich terminal output
- `registry.py`: Generic registry for pluggable components
- `adapters/`: External data source adapters (Examplify, CSV)
- `serializations/`: Serializers for YAML, CSV, JSON formats
- `io/`: DataSource and DataSink abstractions
- `question_sets/`: models, inference, and question type detection
- `rubrics/`: rubric models and validation
- `submissions/`: submission models and processing
- `rules/`: rule models, aggregations, executors (subprocess-based Python), validators
- `questions/`: question models, parsing utilities, and answer types

## Quick Start (CLI)

List available components:

```bash
gradeflow-engine list
```

Infer a QuestionSet from submissions (CSV) and save it:

```bash
gradeflow-engine infer \
  path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --raw-submissions-adapter-config student_id_column=student_id \
  --raw-submissions-adapter-config 'answer_columns=[Q1,Q2,Q3]' \
  --choice-delimiter ',' \
  --choice-option-limit 7 \
  --multi-value-delimiter '~' \
  --save path/to/inferred_question_set.yaml \
  --question-set-serializer yaml
```

Grade with a loaded or inferred QuestionSet and a Rubric, and save results:

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --raw-submissions-adapter-config student_id_column=student_id \
  --raw-submissions-adapter-config 'answer_columns=[Q1,Q2,Q3]' \
  --question-set path/to/question_set.yaml \
  --question-set-serializer yaml \
  --rubric path/to/rubric.yaml \
  --rubric-serializer yaml \
  --out-serializer csv \
  --out-serializer-config include_answers=true \
  --out-serializer-config include_per_question_results=true \
  --out-serializer-config include_total=true \
  --out path/to/graded_results.csv
```

Use external adapters (Examplify):

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --raw-submissions-adapter-config student_id_column=student_id \
  --question-set-adapter-src path/to/exam_export.csv \
  --question-set-adapter examplify \
  --rubric-adapter-src path/to/exam_export.csv \
  --rubric-adapter examplify \
  --out-serializer csv \
  --out path/to/results.csv
```

Pass pre-existing point columns through (e.g. manually graded questions scored outside the engine):

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --point-column Q4=Q4_pts \
  --point-column Q5=Q5_pts \
  --question-set path/to/question_set.yaml \
  --question-set-serializer yaml \
  --rubric path/to/rubric.yaml \
  --rubric-serializer yaml \
  --out-serializer csv \
  --out path/to/graded_results.csv
```

Notes:
- If you omit `--question-set` and `--question-set-adapter-src`, the engine will infer one from submissions
- If you omit `--rubric` and `--rubric-adapter-src`, parsing and reporting will occur, but grading is skipped
- Adapters handle external formats (Examplify); serializers handle YAML/CSV/JSON I/O
- `--point-column question_id=csv_column` can be repeated; those CSV columns are excluded from answers and imported as pre-graded `result_map` entries

## Quick Start (Python API)

Use the core API for scripted pipelines.

```python
from gradeflow_engine.core import (
    load_raw_submissions_via_adapter,
    load_rubric_from_blob,
    dump_submissions_to_blob,
    run_pipeline,
)
from gradeflow_engine.io.sources import StringSource
from gradeflow_engine.question_sets.inference import infer_question_map
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.serializations.base import DataBlob

# Load submissions (CSV) with adapter
csv_data = """
student_id,Q1,Q2,Q3
S1,red,10,foo
S2,red,9,foobar
S3,blue,,bar
""".strip()

raw_submissions = load_raw_submissions_via_adapter(
    StringSource(csv_data),
    adapter_name="csv",
    adapter_kwargs={
        "student_id_column": "student_id",
        "answer_columns": ["Q1", "Q2", "Q3"],
    },
)

# Infer question set
question_map = infer_question_map(
    raw_submissions,
    choice_delimiter=",",
    choice_option_limit=7,
    multi_value_delimiter="~",
)
question_set = QuestionSet(question_map=question_map)

# Load rubric from YAML
rubric_yaml = """
rules:
  - type: TEXT_MATCH
    question_id: "Q1"
    max_points: 1
    answers: ["red"]
  - type: NUMERIC_RANGE
    question_id: "Q2"
    max_points: 2
    min_value: 9
    max_value: 10
  - type: LENGTH
    question_id: "Q3"
    max_points: 1
    min_length: 3
    max_length: 6
"""
rubric = load_rubric_from_blob(
    DataBlob(data=rubric_yaml.encode("utf-8"), media_type="application/yaml", extension="yaml"),
    serializer_name="yaml"
)

# Grade submissions - parse with question set then grade with rubric
submissions = question_set.parse(raw_submissions)
graded_submissions = rubric.grade(submissions, question_set.question_map)

# Serialize results to CSV
csv_blob = dump_submissions_to_blob(
    graded_submissions,
    serializer_name="csv",
    serializer_kwargs={
        "include_answers": True,
        "include_per_question_results": True,
        "include_total": True,
    },
)

print("CSV output:\n", csv_blob.data.decode("utf-8"))
print("Validation errors:", rubric.validate_rubric(question_set))
```

## Data Formats

### Submissions (CSV)

- A header row is required. Default `student_id_column` is `student_id`.
- `answer_columns` can be provided; if omitted, all non-ID/non-point columns are treated as answers.
- `point_columns`: optional `dict[str, str]` mapping `question_id` → CSV column name. When provided, those columns are excluded from answers and their values are loaded as pre-existing `QuestionResult` entries in the submission's `result_map`. Useful for importing manually graded or pass-through scored columns.

Example:

```csv
student_id,Q1,Q2,Q3
S1,red,10,foo
S2,red,9,foobar
S3,blue,,bar
```

Example with pre-existing points column:

```csv
student_id,Q1,Q2,Q3,Q4_pts
S1,red,10,foo,8.0
S2,red,9,foobar,6.5
S3,blue,,bar,
```

Used via CLI:

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --point-column Q4=Q4_pts \
  ...
```

Or via Python:

```python
load_raw_submissions_via_adapter(
    source,
    adapter_name="csv",
    adapter_kwargs={"point_columns": {"Q4": "Q4_pts"}},
)
```

### QuestionSet (YAML)

The QuestionSet is a pydantic model:

```yaml
question_map:
  Q1:
    type: "CHOICE"
    description: "Choose a color"
    max_points: 2.0
    config:
      delimiter: ","
      trim_whitespace: true
      normalize_case: false
    options: ["red", "blue", "green"]
    allow_multiple: false

  Q2:
    type: "NUMERIC"
    description: "Enter a number"
    max_points: 1.0

  Q3:
    type: "TEXT"
    description: "Enter a short text"
    max_points: 1.0
```

Each question has an optional `max_points` field (default `1.0`). When loading from Examplify, `max_points` is populated from the exam export's point values.

You can generate this via inference and save with the YAML saver.

### Rubric (YAML)

Rubric is a list of rules targeting questions. The engine supports 15+ rule types:

**Text-based rules:**
- `TEXT_MATCH`: Exact text match (accepts list of valid answers)
- `KEYWORDS`: Contains keywords (ALL/ANY/PARTIAL mode)
- `REGEX`: Pattern matching with regex flags
- `LENGTH`: Min/max text length (words or characters)
- `SIMILARITY`: Fuzzy text matching (Levenshtein, Jaro-Winkler)

**Numeric rules:**
- `NUMBER_EQUAL`: Exact numeric equality with tolerance
- `NUMERIC_RANGE`: Numeric min/max bounds

**Choice rules:**
- `MULTIPLE_CHOICE`: Choice answers with ALL/ANY/PARTIAL modes

**Advanced rules:**
- `COMPOSITE`: Combine multiple rules on a single answer (ALL/ANY/PARTIAL)
- `MULTI_VALUED`: Per-value rules over a list answer (ALL/ANY/PARTIAL)
- `PROGRAMMABLE`: User-provided Python code (subprocess)
- `PROGRAMMING`: Code execution with test cases
- `CONDITIONAL`: If-then-else rules across multiple questions
- `ASSUMPTION_SET`: Evaluate multiple scoring assumptions (MAX/MIN)
- `BONUS`: Bonus points rule
- `MANUAL`: Placeholder for manual grading

Examples:

Text Match:

```yaml
rules:
  - type: TEXT_MATCH
    question_id: "Q1"
    max_points: 1
    answers: ["red", "Red", "RED"]  # accepts list of valid answers
```

Numeric Range:

```yaml
rules:
  - type: NUMERIC_RANGE
    question_id: "Q2"
    max_points: 2
    min_value: 0
    max_value: 10
```

Keywords:

```yaml
rules:
  - type: KEYWORDS
    question_id: "Q3"
    max_points: 1
    keywords: ["foo", "bar"]
    mode: "ANY"  # ALL, ANY, or PARTIAL
```

Similarity (fuzzy matching):

```yaml
rules:
  - type: SIMILARITY
    question_id: "Q3"
    max_points: 1
    reference: "example text"
    threshold: 0.8
    algorithm: "levenshtein"  # or jaro_winkler
```

Multiple Choice with partial credit:

```yaml
rules:
  - type: MULTIPLE_CHOICE
    question_id: "Q1"
    max_points: 2
    answer: ["red", "blue"]
    mode: "PARTIAL"  # ALL, ANY, PARTIAL
```

Bonus points (always awards full points):

```yaml
rules:
  - type: BONUS
    question_id: "Q4"
    max_points: 2
```

Composite (combine sub-rules on a single answer):

```yaml
rules:
  - type: COMPOSITE
    question_id: "Q3"
    max_points: 2
    aggregation: "ALL"
    rules:
      - type: REGEX
        pattern: "foo"
      - type: LENGTH
        min_length: 3
        max_length: 10
```

Multi-Valued (each value has its own rule, aggregated):

```yaml
rules:
  - type: MULTI_VALUED
    question_id: "Q4"
    max_points: 3
    aggregation: "PARTIAL"
    rules:
      - type: NUMERIC_RANGE
        min_value: 0
        max_value: 10
      - type: TEXT_MATCH
        answers: ["yes"]
      - type: REGEX
        pattern: "^ok$"
```

Programmable:

```yaml
rules:
  - type: PROGRAMMABLE
    question_id: "Q2"
    max_points: 3
    mode: "OUTPUT"  # or PASS_FAIL
    code: |
      # 'answer' variable is provided by the engine
      # Must set 'output' (float 0.0-1.0), 'passed' (bool)
      # Optionally set 'feedback' (str)
      if isinstance(answer, (int, float)) and 0 <= float(answer) <= 10:
          output = 1.0
          passed = True
          feedback = f"Correct: {answer}"
      else:
          output = 0.0
          passed = False
          feedback = "Out of range"
```

Programming test cases:

```yaml
rules:
  - type: PROGRAMMING
    question_id: "Q5"
    max_points: 5
    mode: "ALL"  # ALL or PARTIAL
    testcases:
      - expression: "add(1, 2)"
        expected: "3"
      - expression: "add(0, 0)"
        expected: "0"
      - expression: "add(-1, 1)"
        expected: "0"
    config:
      timeout_seconds: 5
```

Assumption Set (multiple scoring scenarios):

```yaml
rules:
  - type: ASSUMPTION_SET
    question_id: "Q1"
    max_points: 3
    mode: "MAX"  # or MIN
    assumptions:
      - name: "Interpretation A"
        weight: 1.0
        rule:
          type: TEXT_MATCH
          answers: ["red"]
      - name: "Interpretation B"
        weight: 1.0
        rule:
          type: KEYWORDS
          keywords: ["crimson", "scarlet"]
          mode: "ANY"
```

Conditional:

```yaml
rules:
  - type: CONDITIONAL
    if_aggregation: "AND"  # AND or OR
    if_rules:
      - type: LENGTH
        question_id: "Q3"
        max_points: 0
        min_length: 3
        mode: "characters"
    then_rules:
      - type: TEXT_MATCH
        question_id: "Q1"
        max_points: 1
        answers: ["red"]
    else_rules:
      - type: KEYWORDS
        question_id: "Q1"
        max_points: 1
        keywords: ["blue"]
        mode: "ANY"
```

Manual grading placeholder:

```yaml
rules:
  - type: MANUAL
    question_id: "Q6"
    max_points: 10
```

### Submissions (CSV output)

CSV serializer produces:

- student_id column (configurable)
- Optional: one column per question ID with serialized answers
- Optional: per-question results with columns `<qid>__points`, `<qid>__max_points`, `<qid>__passed`, `<qid>__percent`
- Optional: per-question feedback columns `<qid>__feedback`
- Optional: remarks column with detailed grading breakdown
- Optional totals: `total_points`, `total_max_points`, `total_percent`
- Optional rounded totals: `rounded_total_points`, `rounded_total_max_points`, `rounded_total_percent`

Serialization:
- Choice answers (set[str]): alphabetically sorted and joined by "; "
- Multi-valued (list): joined by " | ", with individual values stringified
- Single-valued numeric/text: str()

## Inference Logic

When inferring question types from raw submissions:

1. **MultiValued**: If all non-empty submissions split using the multi-value delimiter to the same cardinality > 1, infer MULTI_VALUED.
2. **Numeric**: If a strict majority of answers parse as numbers, infer NUMERIC.
3. **Choice**: If the distinct observed values (tokenized by the choice delimiter) are limited (<= choice_option_limit). If not all are single-token, set allow_multiple=True.
4. **Text**: Fallback for all other cases.

Configuration options:
- `choice_delimiter` (default: ",")
- `choice_option_limit` (default: 7)
- `choice_normalize_case` (default: True)
- `multi_value_delimiter` (default: "~")
- `empty_marker` (default: "N/A")

## Rule Catalogue

The engine provides 15+ rule types organized by category:

### Text-based Rules
- **TEXT_MATCH**: Exact text equality with list of acceptable answers
- **KEYWORDS**: Text contains keywords (ALL/ANY/PARTIAL mode)
- **REGEX**: Pattern matching with regex flags (ignore_case, multi_line, dotall)
- **LENGTH**: Min/max text length validation (words or characters mode)
- **SIMILARITY**: Fuzzy text matching using RapidFuzz (levenshtein, jaro_winkler algorithms)

### Numeric Rules
- **NUMBER_EQUAL**: Exact numeric equality with optional tolerance (approximate mode)
- **NUMERIC_RANGE**: Numeric min/max bounds

### Choice Rules
- **MULTIPLE_CHOICE**: Choice answers with ALL/ANY/PARTIAL scoring modes

### Advanced Rules
- **COMPOSITE**: Combine multiple single-target rules over one answer (ALL/ANY/PARTIAL aggregation)
- **MULTI_VALUED**: Per-value rules over a list answer (ALL/ANY/PARTIAL aggregation)
- **PROGRAMMABLE**: User-provided Python code with `answer` variable; PASS_FAIL or OUTPUT modes
- **PROGRAMMING**: Code + test cases; executes student code with prepend/append/indent config
- **CONDITIONAL**: If-then-else rules over multiple questions, with AND/OR aggregation on conditions
- **ASSUMPTION_SET**: Evaluate multiple scoring assumptions with weights and choose MAX/MIN score
- **BONUS**: Always awards full points (no conditions)
- **MANUAL**: Placeholder for manual grading (returns 0 points, graded=False)

All rules participate in rubric validation:
- Validate target question existence
- Validate type compatibility (question type must match rule's supported types)
- Validate unique target questions (no duplicate grading rules per question)
- Validate rule-specific constraints (e.g., valid regex patterns, choice options exist)

## Extensibility

### Registries

The engine uses separate registries for adapters and serializers:

**Adapters** (external data sources):
- `RawSubmissionsAdapter`: Load submissions from external formats
- `QuestionSetAdapter`: Load question sets from external formats  
- `RubricAdapter`: Load rubrics from external formats

**Serializers** (YAML/CSV/JSON I/O):
- `QuestionSetSerializer`: Serialize/deserialize question sets
- `RubricSerializer`: Serialize/deserialize rubrics
- `SubmissionsSerializer`: Serialize graded results

Built-in adapters:
- CSV (submissions)
- Examplify (submissions, question sets, rubrics)

Built-in serializers:
- YAML (question sets, rubrics)
- CSV (graded submissions)
- JSON (graded submissions)

Discover available components:

```python
from gradeflow_engine.core import (
    list_available_raw_submissions_adapters,
    list_available_question_set_adapters,
    list_available_rubric_adapters,
    list_available_question_set_serializers,
    list_available_rubric_serializers,
    list_available_submissions_serializers,
    get_raw_submissions_adapter_class,
)

print(list_available_raw_submissions_adapters())  # ["csv", "examplify"]
print(list_available_question_set_serializers())  # ["yaml"]
print(list_available_submissions_serializers())    # ["csv", "json"]

CsvAdapter = get_raw_submissions_adapter_class("csv")
```

### Add a new Submissions Adapter

```python
from typing import Literal
from pydantic import BaseModel, Field
from gradeflow_engine.adapters.registries import (
    raw_submissions_adapter_registry,
    RawSubmissionsAdapter,
)
from gradeflow_engine.submissions.models import RawSubmission
from gradeflow_engine.io.sources import DataSource

class MyAdapterConfig(BaseModel):
    name: Literal["my_adapter"] = "my_adapter"
    my_option: int = Field(default=0, description="Custom option")

class MyAdapter(RawSubmissionsAdapter):
    name: Literal["my_adapter"] = "my_adapter"
    config: MyAdapterConfig = MyAdapterConfig()

    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)

    def load(self, source: DataSource) -> list[RawSubmission]:
        blob = source.read()
        # Parse blob.data and return RawSubmission list
        return []

# Register at module import time
raw_submissions_adapter_registry.register("my_adapter", MyAdapter)
```

### Add a new Serializer

```python
from typing import Literal
from pydantic import BaseModel
from gradeflow_engine.serializations.registries import question_set_serializer_registry
from gradeflow_engine.serializations.base import Serializer, DataBlob
from gradeflow_engine.question_sets.model import QuestionSet

class MySerializerConfig(BaseModel):
    format: Literal["my_format"] = "my_format"

class MySerializer(Serializer[QuestionSet]):
    format = "my_format"
    media_type = "text/plain"
    config: MySerializerConfig = MySerializerConfig()
    
    def __init__(self, **kwargs: object) -> None:
        self.config = self.config.model_validate(kwargs)
    
    def loads(self, blob: DataBlob) -> QuestionSet:
        # Deserialize from blob.data (bytes)
        text = blob.data.decode("utf-8")
        return QuestionSet(question_map={})
    
    def dumps(self, obj: QuestionSet) -> DataBlob:
        # Serialize to bytes
        data = "...".encode("utf-8")
        return DataBlob(data=data, media_type=self.media_type, extension="txt")

# Register at module import time
question_set_serializer_registry.register("my_format", MySerializer)
```

### Add a new Rule

Implement a subclass of `BaseRule` and likely `BaseSingleQuestionRule` or `BaseMultiQuestionRule`:

```python
from typing import Literal
from gradeflow_engine.rules.models.base import BaseSingleQuestionRule
from gradeflow_engine.rules.result import RuleResult
from gradeflow_engine.questions.types import Answer

class MyCustomRule(BaseSingleQuestionRule):
    type: Literal["MY_CUSTOM"] = "MY_CUSTOM"
    my_param: str
    
    def _process_answer(self, answer: Answer) -> RuleResult:
        # Implement grading logic
        passed = True  # Your logic here
        points = self.max_points if passed else 0
        feedback = "Custom feedback"
        return RuleResult(
            passed=passed,
            points=points,
            max_points=self.max_points,
            feedback=feedback,
        )
```

Update the discriminated union in `rules/models/__init__.py` to enable YAML deserialization.

## License

MIT License

## Acknowledgements

- Pydantic for robust model validation and serialization
- Typer and Rich for elegant CLI with beautiful terminal output
- RapidFuzz for fast fuzzy string matching and similarity metrics
- natsort for natural sorting of question IDs in outputs
- PyYAML for YAML serialization