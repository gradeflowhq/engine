# GradeFlow Engine

GradeFlow Engine is a modular grading engine designed to ingest submissions, infer or load question sets, validate and apply rubrics, compute grades, and export results. It emphasizes extensibility through registries, safety via pydantic validation, and composable rule-based grading.

## Key Features

- Pluggable loaders and savers for submissions, question sets, and rubrics via registries
- Automatic question type inference from raw submissions
- Rule-based grading: exact match, numeric ranges, keywords, regex, choice, composite, multi-valued, programmable, conditional, programming testcases
- Safe execution of user code (RestrictedPython) with timeouts for programmable/programming rules
- CLI for common workflows
- Python API for scripted pipelines
- Deterministic serialization of answers and graded results

## Installation

```bash
pip install -e .
# or use your environment manager of choice
```

## Project Structure

- `core.py`: High-level API and pipeline orchestration
- `cli.py`: Typer-based CLI
- `registry.py`: Generic registry for pluggable components
- `question_sets/`: models, inference, loaders, savers
- `rubrics/`: models, loaders
- `submissions/`: models, loaders, savers
- `rules/`: rule models, aggregations, executors (RestrictedPython), validators
- `questions/`: question models, parsing utilities and types

## Quick Start (CLI)

List available components:

```bash
gradeflow-engine list
```

Infer a QuestionSet from submissions (CSV) and optionally save it:

```bash
gradeflow-engine infer \
  path/to/submissions.csv \
  --submissions-loader CSV \
  --submissions-loader-kv student_id_column=student_id \
  --submissions-loader-kv 'answer_columns=[Q1,Q2,Q3]' \
  --choice-delimiter ',' \
  --choice-option-limit 5 \
  --multi-value-delimiter '|' \
  --save path/to/inferred_question_set.yaml \
  --question-set-saver YAML
```

Grade with a loaded or inferred QuestionSet and a Rubric, and save results:

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --submissions-loader CSV \
  --submissions-loader-kv student_id_column=student_id \
  --submissions-loader-kv 'answer_columns=[Q1,Q2,Q3]' \
  --question-set path/to/question_set.yaml \
  --question-set-loader YAML \
  --rubric path/to/rubric.yaml \
  --rubric-loader YAML \
  --saver CSV \
  --saver-kv include_answers=true \
  --saver-kv include_per_question_results=true \
  --saver-kv include_total=true \
  --out path/to/graded_results.csv
```

Notes:
- If you omit `--question-set`, the engine will infer one from submissions using the provided delimiters and limits.
- If you omit `--rubric`, parsing and reporting will occur, but grading is skipped.

## Quick Start (Python API)

Use the core API for scripted pipelines.

```python
from gradeflow_engine.core import (
    load_submissions,
    infer_question_set,
    load_rubric,
    save_graded_submissions,
    run_pipeline,
)

# Load submissions (CSV string) with options validated by pydantic
csv_data = """
student_id,Q1,Q2,Q3
S1,red,10,"foo"
S2,red,9,"foobar"
S3,blue,,"bar"
""".strip()

raw_submissions = load_submissions(
    csv_data,
    loader_name="CSV",
    student_id_column="student_id",
    answer_columns=["Q1", "Q2", "Q3"],
)

# Infer question set
question_set = infer_question_set(
    raw_submissions,
    choice_delimiter=",",
    choice_option_limit=5,
    multi_value_delimiter="|",
)

# Optionally load rubric from YAML string
rubric_yaml = """
rules:
  - type: EXACT_MATCH
    question_id: "Q1"
    max_points: 1
    answer: "red"
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
rubric = load_rubric(rubric_yaml, loader_name="YAML")

# End-to-end pipeline
result = run_pipeline(
    raw_submissions=raw_submissions,
    question_set=question_set,
    rubric=rubric,
    saver_name="CSV",  # set None to skip saving
    submissions_saver_kwargs={"include_answers": True, "include_total": True},
)

# Use pipeline result
print("Validation errors:", result.validation_errors)
print("Graded submissions:", len(result.graded_submissions))
if result.output:
    print("CSV output:\n", result.output.data)
```

## Data Formats

### Submissions (CSV)

- A header row is required. Default `student_id_column` is `student_id`.
- `answer_columns` can be provided; if omitted, all non-ID columns are treated as answers.

Example:

```
csv
student_id,Q1,Q2,Q3
S1,red,10,foo
S2,red,9,foobar
S3,blue,,bar
```

### QuestionSet (YAML)

The QuestionSet is a pydantic model:

```yaml
question_map:
  Q1:
    type: "CHOICE"
    description: "Choose a color"
    config:
      delimiter: ","
      trim_whitespace: true
      normalize_case: false
    options: ["red", "blue", "green"]
    allow_multiple: false

  Q2:
    type: "NUMERIC"
    description: "Enter a number"

  Q3:
    type: "TEXT"
    description: "Enter a short text"
```

You can generate this via inference and save with the YAML saver.

### Rubric (YAML)

Rubric is a list of rules targeting questions. Common choices include Exact Match, Numeric Range, Keywords, Regex, Multiple Choice, Composite, Multi-Valued, Programmable, Programming, and Conditional rules.

Examples:

Exact Match:

```yaml
rules:
  - type: EXACT_MATCH
    question_id: "Q1"
    max_points: 1
    answer: "red"
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
    mode: "ANY"  # ALL or ANY
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
      - type: EXACT_MATCH
        answer: "yes"
      - type: REGEX
        pattern: "^ok$"
```

Programmable (RestrictedPython):

```yaml
rules:
  - type: PROGRAMMABLE
    question_id: "Q2"
    max_points: 3
    mode: "OUTPUT"  # or PASS_FAIL
    code: |
      # answer is provided by the engine
      output = 1.0 if (isinstance(answer, (int, float)) and 0 <= float(answer) <= 10) else 0.0
      passed = output >= 1.0
      feedback = f"Value {answer}"
```

Programming test cases:

```yaml
rules:
  - type: PROGRAMMING
    question_id: "Q5"
    max_points: 5
    mode: "ALL"
    testcases:
      - expression: "add(1, 2)"
        expected: "3"
      - expression: "add(0, 0)"
        expected: "0"
    config:
      prepend_code: |
        def add(a, b):
            return a + b
```

Conditional:

```yaml
rules:
  - type: CONDITIONAL
    if_aggregation: "AND"
    if_rules:
      - type: LENGTH
        question_id: "Q3"
        max_points: 0
        min_length: 3
    then_rules:
      - type: EXACT_MATCH
        question_id: "Q1"
        max_points: 1
        answer: "red"
    else_rules:
      - type: KEYWORDS
        question_id: "Q1"
        max_points: 1
        keywords: ["blue"]
```

### Graded Submissions (CSV output)

CSV saver produces:

- student_id column (configurable)
- Optional: one column per question ID with serialized answers
- Optional: per-question results with columns `<qid>__points`, `<qid>__max_points`, `<qid>__passed`
- Optional totals: `total_points`, `total_max_points`

Serialization:
- Choice answers (set[str]): alphabetically sorted and joined by "; "
- Multi-valued (list): joined by " | ", with individual values stringified (numbers kept numeric)
- Single-valued numeric/text: str()

## Inference Logic

When inferring question types from raw submissions:

1) MultiValued: if all non-empty submissions split using the multi-value delimiter to the same cardinality > 1, infer MULTI_VALUED.
2) Numeric: if a strict majority of answers parse as numbers.
3) Choice: if the distinct observed values (tokenized by the choice delimiter) are limited (<= choice_option_limit). If not all are single-token, allow_multiple=True.
4) Text: fallback.

You can control:
- choice_delimiter (default ",")
- choice_option_limit (default 5)
- multi_value_delimiter (default "|")

## Rule Catalogue

- EXACT_MATCH: text/numeric equality
- NUMERIC_RANGE: numeric min/max
- KEYWORDS: text contains keywords (ALL/ANY)
- REGEX: text pattern match with flags
- LENGTH: min/max text length
- MULTIPLE_CHOICE: choice answers with ALL/ANY/PARTIAL modes
- COMPOSITE: combine multiple single-target rules over one answer (ALL/ANY/PARTIAL)
- MULTI_VALUED: per-value rules over a list answer (ALL/ANY/PARTIAL)
- PROGRAMMABLE: user-provided code (RestrictedPython) evaluating `answer`; PASS_FAIL or OUTPUT modes
- PROGRAMMING: code + testcases; executes student code with prepend/append and checks outputs
- CONDITIONAL: if-then-else rules over multiple questions, with AND/OR aggregation on the condition
- ASSUMPTION_SET: evaluate multiple assumptions (each with rules) and choose MAX/MIN score assumption

All rules participate in rubric validation:
- Validate target question existence
- Validate type compatibility
- Validate unique target questions (across grading rules)

## Extensibility

### Registries

Components register via `Registry.register_decorator("NAME")`. Existing keys:

- QuestionSetLoader: "YAML"
- QuestionSetSaver: "YAML"
- RubricLoader: "YAML"
- SubmissionsLoader: "CSV"
- SubmissionsSaver: "CSV"

Discover and get:

```python
from gradeflow_engine.core import (
  list_available_question_set_loaders,
  get_question_set_loader_class,
)
print(list_available_question_set_loaders())  # ["YAML"]
YamlLoader = get_question_set_loader_class("YAML")
```

### Add a new Submissions Loader

```python
from typing import Literal
from pydantic import BaseModel
from gradeflow_engine.registry import submissions_loader_registry
from gradeflow_engine.submissions.loaders.base import BaseSubmissionsLoader
from gradeflow_engine.submissions.models import RawSubmission

@submissions_loader_registry.register_decorator("MY_LOADER")
class MyLoader(BaseSubmissionsLoader):
    name: Literal["MY_LOADER"] = "MY_LOADER"
    my_option: int = 0

    def load(self, data: str) -> list[RawSubmission]:
        # parse data and return RawSubmission list
        return []
```

### Add a new Submissions Saver

```python
from typing import Literal, Iterable
from gradeflow_engine.registry import submissions_saver_registry
from gradeflow_engine.submissions.savers.base import BaseSubmissionsSaver, SubmissionsSaverOutput
from gradeflow_engine.submissions.models import GradedSubmission

@submissions_saver_registry.register_decorator("MY_SAVER")
class MySaver(BaseSubmissionsSaver):
    name: Literal["MY_SAVER"] = "MY_SAVER"
    def save(self, submissions: Iterable[GradedSubmission]) -> SubmissionsSaverOutput:
        data = "..."  # serialize
        return SubmissionsSaverOutput(data=data, extension="txt")
```

### Add a new QuestionSet Loader/Saver

Follow the patterns in `question_sets/loaders/yaml.py` and `question_sets/savers/yaml.py`, register under a unique name.

### Add a new Rule

Implement a subclass of `BaseRule` and likely `BaseSingleQuestionRule` or `BaseMultiQuestionRule`, ensure `type` and `question_types` are defined, implement `_process_answer`, `compute_points`, and validation methods. Update discriminated unions in `rules/models/__init__.py` if you want pydantic to deserialize from YAML using `type`.

## License

MIT License

## Acknowledgements

- Pydantic for robust model validation
- Typer and Rich for CLI UX
- RestrictedPython for sandboxed code execution
- RapidFuzz for similarity metrics
- natsort for predictable question ID ordering in outputs