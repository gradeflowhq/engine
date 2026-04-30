# GradeFlow Engine

GradeFlow Engine is a modular grading engine designed to ingest submissions, infer or load question sets, validate and apply rubrics, compute grades, and export results. It emphasizes extensibility through registries, safety via Pydantic validation, and composable rule-based grading.

## Key Features

- Pluggable adapters and serializers for submissions, question sets, and rubrics via registries
- Automatic question type inference from raw submissions
- Comprehensive rule-based grading system with 15+ rule types
- User code execution in a subprocess with configurable timeouts for programmable/programming rules — use the official Docker image for safe sandboxed execution
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
- `cli/`: Typer-based CLI with rich terminal output
- `registry.py`: Generic registry for pluggable components
- `exceptions.py`: Custom exception hierarchy for all engine errors
- `adapters/`: External data source adapters (Examplify, CSV)
- `serializations/`: Serializers for YAML, CSV, and JSON formats
- `io/`: `DataSource` and `DataSink` abstractions
- `question_sets/`: Models, inference, and question type detection
- `rubrics/`: Rubric models and validation
- `submissions/`: Submission models and processing
- `rules/`: Rule models, aggregations, subprocess-based Python executors, and validators
- `questions/`: Question models, parsing utilities, and answer types
- `mixins.py`: Shared mixins
- `py.typed`: PEP 561 marker for type-checking support

## Running with Docker

The official Docker image provides a sandboxed environment for safe execution of user code in programmable and programming rules:

```bash
docker pull ghcr.io/gradeflowhq/gradeflow-engine:latest
```

Run the CLI via Docker:

```bash
docker run --rm \
  -v /path/to/your/files:/data \
  ghcr.io/gradeflowhq/gradeflow-engine:latest \
  grade \
  --submissions /data/submissions.csv \
  --question-set /data/questions.yaml \
  --rubric /data/rubric.yaml \
  --out /data/graded_results.csv
```

Mount your local directory to `/data` inside the container and reference all file paths relative to `/data`.

## Quick Start (CLI)

List available components:

```bash
gradeflow-engine list
```

Infer a `QuestionSet` from submissions (CSV) and save it:

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

Grade with a loaded or inferred `QuestionSet` and a `Rubric`, and save results:

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
- If you omit `--question-set` and `--question-set-adapter-src`, the engine infers a question set from the submissions.
- If you omit `--rubric` and `--rubric-adapter-src`, parsing and reporting occur but grading is skipped.
- Adapters handle external formats (Examplify); serializers handle YAML/CSV/JSON I/O.
- `--point-column question_id=csv_column` can be repeated; those CSV columns are excluded from answers and imported as pre-graded `result_map` entries.

## Quick Start (Python API)

Use the core API for scripted pipelines.

```python
from gradeflow_engine.core import (
    load_raw_submissions_via_adapter,
    load_rubric_from_blob,
    dump_submissions_to_blob,
)
from gradeflow_engine.io.sources import StringSource
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.serializations.base import DataBlob

# Load submissions (CSV) with adapter
csv_data = """
student_id,Q1,Q2,Q3
S1,red,10,hello world foo
S2,blue,9,goodbye world bar
S3,red,8,another example sentence here
S4,blue,7,yet more text for testing
S5,red,11,some words
S6,green,6,extra long answer with many words in it
S7,red,5,short
S8,blue,12,medium length answer here
""".strip()

raw_submissions = load_raw_submissions_via_adapter(
    StringSource(csv_data),
    adapter_name="csv",
    adapter_kwargs={
        "student_id_column": "student_id",
        "answer_columns": ["Q1", "Q2", "Q3"],
    },
)

from gradeflow_engine.questions.models import ChoiceQuestion, NumericQuestion, TextQuestion

question_set = QuestionSet(question_map={
    "Q1": ChoiceQuestion(
        options={"red", "blue", "green"},
        max_points=1.0,
    ),
    "Q2": NumericQuestion(max_points=2.0),
    "Q3": TextQuestion(max_points=1.0),
})

# Load rubric from YAML
rubric_yaml = """
rules:
  - type: MULTIPLE_CHOICE
    question_id: "Q1"
    answer:
      - red
    mode: ALL
  - type: NUMERIC_RANGE
    question_id: "Q2"
    min_value: 9
    max_value: 10
  - type: LENGTH
    question_id: "Q3"
    min_length: 3
    max_length: 50
    mode: characters
"""
rubric = load_rubric_from_blob(
    DataBlob(data=rubric_yaml.encode("utf-8"), media_type="application/yaml", extension="yaml"),
    serializer_name="yaml",
)

# Grade submissions — parse with question set, then grade with rubric
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

### Submissions (CSV input)

- A header row is required. The default `student_id_column` is `student_id`.
- `answer_columns` can be specified explicitly; if omitted, all non-ID and non-point columns are treated as answers.
- `point_columns`: optional `dict[str, str]` mapping `question_id` → CSV column name. When provided, those columns are excluded from answers and their values are loaded as pre-existing `QuestionResult` entries in the submission's `result_map`. Useful for importing manually graded or pass-through scored columns.

Example:

```csv
student_id,Q1,Q2,Q3
S1,red,10,foo
S2,red,9,foobar
S3,blue,,bar
```

Example with a pre-existing points column:

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

The `QuestionSet` is a Pydantic model serialized to/from YAML:

```yaml
question_map:
  Q1:
    type: CHOICE
    description: "Choose a color"
    max_points: 2.0
    config:
      delimiter: ","
      trim_whitespace: true
      normalize_case: false
    options:
      - red
      - blue
      - green
    allow_multiple: false

  Q2:
    type: NUMERIC
    description: "Enter a number"
    max_points: 1.0

  Q3:
    type: TEXT
    description: "Enter a short text"
    max_points: 1.0
```

Each question has an optional `max_points` field (default `1.0`). When loading from Examplify, `max_points` is populated from the exam export's point values. Note that `max_points` is a property of questions, not rules — during grading, the engine uses each question's `max_points` to compute points for the corresponding rule result.

You can generate a `QuestionSet` via inference and save it with the YAML serializer.

### Rubric (YAML)

A rubric is a list of rules targeting questions. The engine supports 15+ rule types. Each rule specifies a `question_id` to target and a `type` discriminator. The `max_points` for scoring is determined by the corresponding question in the `QuestionSet`, not by the rule itself.

**Text-based rules:**

Text Match — exact equality, accepts a list of valid answers:

```yaml
rules:
  - type: TEXT_MATCH
    question_id: Q1
    answers:
      - red
      - Red
      - RED
```

Keywords — answer must contain specified keywords:

```yaml
rules:
  - type: KEYWORDS
    question_id: Q3
    keywords:
      - foo
      - bar
    mode: ANY  # ALL, ANY, or PARTIAL
```

Regex — pattern matching with optional flags:

```yaml
rules:
  - type: REGEX
    question_id: Q3
    pattern: "^foo.*bar$"
    config:
      ignore_case: false
      multi_line: false
      dotall: false
```

Length — min/max length in characters or words:

```yaml
rules:
  - type: LENGTH
    question_id: Q3
    min_length: 3
    max_length: 10
    mode: characters  # characters or words
```

Similarity — fuzzy text matching:

```yaml
rules:
  - type: SIMILARITY
    question_id: Q3
    references:
      - example text
    threshold: 0.8
    algorithm: levenshtein  # levenshtein, jaro_winkler, or transformer
```

**Numeric rules:**

Number Equal — exact numeric equality with optional tolerance:

```yaml
rules:
  - type: NUMBER_EQUAL
    question_id: Q2
    answers:
      - 42
    config:
      approximate: true
      tolerance: 1.0e-6
```

Numeric Range — min/max bounds:

```yaml
rules:
  - type: NUMERIC_RANGE
    question_id: Q2
    min_value: 0
    max_value: 10
```

**Choice rules:**

Multiple Choice — with ALL/ANY/PARTIAL scoring modes:

```yaml
rules:
  - type: MULTIPLE_CHOICE
    question_id: Q1
    answer:
      - red
      - blue
    mode: PARTIAL  # ALL, ANY, or PARTIAL
```

**Advanced rules:**

Composite — combine multiple rules over a single answer:

```yaml
rules:
  - type: COMPOSITE
    question_id: Q3
    aggregation: ALL  # ALL, ANY, or PARTIAL
    rules:
      - type: REGEX
        pattern: "foo"
      - type: LENGTH
        min_length: 3
        max_length: 10
```

Multi-Valued — per-value rules over a list answer:

```yaml
rules:
  - type: MULTI_VALUED
    question_id: Q4
    aggregation: PARTIAL  # ALL, ANY, or PARTIAL
    rules:
      - type: NUMERIC_RANGE
        min_value: 0
        max_value: 10
      - type: TEXT_MATCH
        answers:
          - yes
      - type: REGEX
        pattern: "^ok$"
```

Programmable — custom Python scoring code:

```yaml
rules:
  - type: PROGRAMMABLE
    question_id: Q2
    mode: OUTPUT  # PASS_FAIL or OUTPUT
    code: |
      # 'answer' is provided by the engine (str, float, list, or set)
      # Set 'output' (float 0.0–1.0) for OUTPUT mode
      # Set 'passed' (bool) for PASS_FAIL mode
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

Programming — execute student code against test cases:

```yaml
rules:
  - type: PROGRAMMING
    question_id: Q5
    mode: ALL  # ALL, ANY, or PARTIAL
    testcases:
      - expression: "add(1, 2)"
        expected: "3"
      - expression: "add(0, 0)"
        expected: "0"
      - expression: "add(-1, 1)"
        expected: "0"
    config:
      prepend_code: ""
      append_code: ""
      indent: 0
      time_limit: 5
```

Assumption Set — evaluate multiple scoring assumptions and select MAX or MIN:

```yaml
rules:
  - type: ASSUMPTION_SET
    question_id: Q1
    mode: MAX  # MAX or MIN
    assumptions:
      - name: "Interpretation A"
        weight: 1.0
        rule:
          type: TEXT_MATCH
          answers:
            - red
      - name: "Interpretation B"
        weight: 1.0
        rule:
          type: KEYWORDS
          keywords:
            - crimson
            - scarlet
          mode: ANY
```

Assumption Set (multi-question) — multiple scoring assumptions across multiple questions:

```yaml
rules:
  - type: ASSUMPTION_SET_MULTI
    mode: MAX
    assumptions:
      - name: "Scenario A"
        weight: 1.0
        rules:
          - type: TEXT_MATCH
            question_id: Q1
            answers:
              - red
          - type: NUMERIC_RANGE
            question_id: Q2
            min_value: 9
            max_value: 10
      - name: "Scenario B"
        weight: 0.5
        rules:
          - type: TEXT_MATCH
            question_id: Q1
            answers:
              - blue
          - type: NUMERIC_RANGE
            question_id: Q2
            min_value: 5
            max_value: 8
```

Conditional — if-then-else rules across multiple questions:

```yaml
rules:
  - type: CONDITIONAL
    if_aggregation: AND  # AND or OR
    if_rules:
      - type: LENGTH
        question_id: Q3
        min_length: 3
        mode: characters
    then_rules:
      - type: TEXT_MATCH
        question_id: Q1
        answers:
          - red
    else_rules:
      - type: KEYWORDS
        question_id: Q1
        keywords:
          - blue
        mode: ANY
```

Bonus — always awards full points:

```yaml
rules:
  - type: BONUS
    question_id: Q4
```

Manual — placeholder for manual grading (returns 0 points, `graded=False`):

```yaml
rules:
  - type: MANUAL
    question_id: Q6
```

### Submissions (CSV output)

The CSV serializer (`CsvSubmissionsConfig`) produces columns controlled by boolean flags:

| Config field | Default | Description |
|---|---|---|
| `student_id_column` | `student_id` | Name of the student ID column |
| `include_answers` | `true` | One column per question ID with serialized answers |
| `include_per_question_results` | `true` | `<qid>__points`, `<qid>__max_points`, `<qid>__passed`, `<qid>__percent` columns |
| `include_feedback` | `true` | `<qid>__feedback` columns |
| `include_remarks` | `true` | A single `remarks` column with a full grading breakdown |
| `include_total` | `true` | `total_points`, `total_max_points`, `total_percent` columns |
| `include_rounded_total` | `true` | `rounded_total_points`, `rounded_total_max_points`, `rounded_total_percent` columns |
| `rounding_base` | `0.5` | Rounding base for rounded total columns (set to `0` to disable) |

Answer serialization:
- Choice answers (`set[str]`): alphabetically sorted and joined by `"; "`
- Multi-valued answers (`list`): joined by `" | "`, with individual values stringified
- Single-valued numeric/text: `str()`

## Inference Logic

When inferring question types from raw submissions, the engine applies rules in the following order:

1. **MULTI_VALUED**: All non-empty submissions split using the multi-value delimiter to the same cardinality > 1.
2. **NUMERIC**: A strict majority (> 50%) of non-empty answers parse as numbers.
3. **CHOICE**: The number of distinct observed values (tokenized by the choice delimiter) is between 1 and `choice_option_limit` (inclusive). If not all submissions are single-token, `allow_multiple` is set to `True`.
4. **TEXT**: Fallback for all other cases.

Configuration options (with defaults):

| Option | Default | Description |
|---|---|---|
| `choice_delimiter` | `,` | Delimiter used to tokenize choice answers |
| `choice_option_limit` | `7` | Maximum distinct values to infer CHOICE type |
| `choice_normalize_case` | `True` | Normalize case when tokenizing choices |
| `multi_value_delimiter` | `~` | Delimiter used to detect MULTI_VALUED answers |
| `empty_marker` | `N/A` | String treated as an empty/absent answer |

## Rule Catalogue

### Text-based Rules

| Rule | Supported Question Types | Key Fields |
|---|---|---|
| `TEXT_MATCH` | TEXT, NUMERIC | `answers: list[str]` |
| `KEYWORDS` | TEXT | `keywords: list[str]`, `mode: ALL\|ANY\|PARTIAL` |
| `REGEX` | TEXT | `pattern: str`, `config: RegexConfig` |
| `LENGTH` | TEXT | `min_length`, `max_length`, `mode: characters\|words` |
| `SIMILARITY` | TEXT | `references: list[str]`, `threshold: float`, `algorithm: levenshtein\|jaro_winkler\|transformer` |

### Numeric Rules

| Rule | Supported Question Types | Key Fields |
|---|---|---|
| `NUMBER_EQUAL` | NUMERIC | `answers: list[int\|float]`, `config: NumberEqualConfig` |
| `NUMERIC_RANGE` | NUMERIC | `min_value: float\|None`, `max_value: float\|None` |

### Choice Rules

| Rule | Supported Question Types | Key Fields |
|---|---|---|
| `MULTIPLE_CHOICE` | CHOICE | `answer: set[str]`, `mode: ALL\|ANY\|PARTIAL` |

### Advanced Rules

| Rule | Supported Question Types | Key Fields |
|---|---|---|
| `COMPOSITE` | TEXT, NUMERIC | `rules: list[SingleTargetRule]`, `aggregation: ALL\|ANY\|PARTIAL` |
| `MULTI_VALUED` | MULTI_VALUED | `rules: list[SingleTargetRule]`, `aggregation: ALL\|ANY\|PARTIAL` |
| `PROGRAMMABLE` | TEXT, NUMERIC, CHOICE, MULTI_VALUED | `code: str`, `mode: PASS_FAIL\|OUTPUT` |
| `PROGRAMMING` | TEXT | `testcases`, `config: ProgrammingConfig`, `mode: ALL\|ANY\|PARTIAL` |
| `CONDITIONAL` | TEXT, CHOICE, NUMERIC, MULTI_VALUED | `if_rules`, `if_aggregation: AND\|OR`, `then_rules`, `else_rules` |
| `ASSUMPTION_SET` | TEXT, CHOICE, NUMERIC, MULTI_VALUED | `assumptions: list[Assumption]`, `mode: MAX\|MIN` |
| `ASSUMPTION_SET_MULTI` | TEXT, CHOICE, NUMERIC, MULTI_VALUED | `assumptions: list[MultiQuestionAssumption]`, `mode: MAX\|MIN` |

### Other Rules

| Rule | Supported Question Types | Key Fields |
|---|---|---|
| `BONUS` | TEXT, NUMERIC, CHOICE, MULTI_VALUED | — |
| `MANUAL` | TEXT, NUMERIC, CHOICE, MULTI_VALUED | — |

All rules participate in rubric validation:
- Validate that target questions exist in the question set
- Validate type compatibility (question type must match the rule's supported types)
- Validate that no question is targeted by more than one rule
- Validate rule-specific constraints (e.g., valid choice options, regex patterns)

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
- `csv` (raw submissions)
- `examplify` (question sets, rubrics)

Built-in serializers:
- `yaml` (question sets, rubrics)
- `csv` (graded submissions)
- `json` (graded submissions)

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

print(list_available_raw_submissions_adapters())   # ["csv"]
print(list_available_question_set_adapters())      # ["examplify"]
print(list_available_rubric_adapters())            # ["examplify"]
print(list_available_question_set_serializers())   # ["yaml"]
print(list_available_submissions_serializers())    # ["csv", "json", "yaml"]

CsvAdapter = get_raw_submissions_adapter_class("csv")
```

### Add a New Submissions Adapter

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
        # Parse blob.data and return a list of RawSubmission
        return []


# Register at module import time
raw_submissions_adapter_registry.register("my_adapter", MyAdapter)
```

### Add a New Serializer

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
        text = blob.data.decode("utf-8")
        return QuestionSet(question_map={})

    def dumps(self, obj: QuestionSet) -> DataBlob:
        data = "...".encode("utf-8")
        return DataBlob(data=data, media_type=self.media_type, extension="txt")


# Register at module import time
question_set_serializer_registry.register("my_format", MySerializer)
```

### Add a New Rule

Subclass `BaseRule` and `BaseSingleQuestionRule` (or `BaseMultiQuestionRule` for multi-question rules). The codebase convention is to define a base rule class first, then a question-rule variant:

```python
from typing import Literal
from pydantic import Field, computed_field
from gradeflow_engine.rules.models.base import BaseRule, BaseSingleQuestionRule
from gradeflow_engine.rules.result import Result
from gradeflow_engine.questions.types import Answer, QuestionType


class MyCustomRule(BaseRule):
    type: Literal["MY_CUSTOM"] = Field(
        default="MY_CUSTOM", frozen=True, json_schema_extra={"readOnly": True}
    )
    display_name: Literal["My Custom"] = Field(
        default="My Custom", frozen=True, json_schema_extra={"readOnly": True}
    )
    question_types: frozenset[QuestionType] = Field(
        default=frozenset({"TEXT"}), frozen=True, json_schema_extra={"readOnly": True}
    )
    my_param: str

    @computed_field
    @property
    def description(self) -> str:
        return f"Custom rule with param: {self.my_param}"

    def _process_answer(self, answer: Answer) -> Result:
        passed = str(answer) == self.my_param
        return Result(
            output=passed,
            passed=passed,
            feedback="Correct." if passed else f"Expected {self.my_param!r}.",
            rule=self.__class__.__name__,
        )


class MyCustomQuestionRule(MyCustomRule, BaseSingleQuestionRule):
    def compute_points(self, result: Result, max_points: float) -> float:
        return max_points if result.passed else 0.0
```

Then add `MyCustomQuestionRule` to the `SingleTargetQuestionRule` discriminated union in `rules/models/__init__.py` to enable YAML deserialization.

## License

MIT License

## Acknowledgements

- [Pydantic](https://docs.pydantic.dev/) for robust model validation and serialization
- [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/) for an elegant CLI with beautiful terminal output
- [RapidFuzz](https://github.com/maxbachmann/RapidFuzz) for fast fuzzy string matching and similarity metrics
- [FastEmbed](https://github.com/qdrant/fastembed) for fast text embedding
- [natsort](https://github.com/SethMMorton/natsort) for natural sorting of question IDs in outputs
- [PyYAML](https://pyyaml.org/) for YAML serialization
