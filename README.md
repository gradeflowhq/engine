# GradeFlow Engine

GradeFlow Engine is the Python grading core for GradeFlow. It loads raw submissions,
infers or imports question sets, validates rubrics, applies composable grading rules,
and serializes graded results. The engine is built around Pydantic models, small I/O
abstractions, registries for pluggable adapters and serializers, and rule classes that
can generate context-aware schemas for clients.

## Highlights

- CSV raw-submission ingestion with optional pass-through point columns.
- Question-set inference for text, numeric, choice, and fixed-width multi-valued answers.
- Question-set drift detection and sync helpers for new questions and new choice options.
- YAML serializers for question sets and rubrics.
- CSV, JSON, and YAML serializers for graded submissions.
- Examplify adapters for question sets and rubrics.
- Seventeen rubric rule types, including composite, conditional, assumption-set, custom
  code, multi-question custom code, and code-test rules.
- Pydantic validation with user-facing error formatting.
- Strict and non-strict parsing/grading modes.
- Optional parallel grading with process or thread workers.
- PEP 561 typing marker via `py.typed`.

## Installation

The package requires Python 3.11 or newer.

```bash
cd engine
pip install -e .
```

For development tools:

```bash
pip install -e ".[dev]"
```

For transformer-based text similarity:

```bash
pip install -e ".[ml]"
```

The `ml` extra installs `fastembed` and `numpy`; it is only needed when a
`SIMILARITY` rule uses `algorithm: transformer`.

## Core Concepts

- `RawSubmission`: a student ID plus raw string answers, as loaded from an adapter.
- `QuestionSet`: a map of question IDs to typed question models. It parses raw answers.
- `Submission`: a parsed submission with typed answers and a `result_map`.
- `Rubric`: a list of question rules or multi-question rules.
- `QuestionResult`: points, max points, pass/fail state, feedback, rule name, and grading flag.
- `DataBlob`: serialized bytes plus media type and extension.
- `DataSource` and `DataSink`: small read/write protocols used by the pipeline.

The main end-to-end entry point is `gradeflow_engine.core.run_pipeline`. Lower-level
helpers are also exposed for loading adapters, loading/dumping serializers, and manually
parsing or grading.

## CLI

The package installs the `gradeflow-engine` command.

List registered components:

```bash
gradeflow-engine list
```

Infer a question set from a CSV and save it:

```bash
gradeflow-engine infer \
  path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --raw-submissions-adapter-config student_id_column=student_id \
  --raw-submissions-adapter-config 'answer_columns=[Q1,Q2,Q3]' \
  --choice-delimiter ',' \
  --choice-option-limit 7 \
  --choice-normalize-case \
  --multi-value-delimiter '~' \
  --empty-marker N/A \
  --save path/to/question_set.yaml \
  --question-set-serializer yaml
```

Grade with a serialized question set and rubric:

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

Grade with an inferred question set:

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --rubric path/to/rubric.yaml \
  --rubric-serializer yaml \
  --out path/to/graded_results.csv
```

Use Examplify exports for question set and rubric data:

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --question-set-adapter-src path/to/exam_export.csv \
  --question-set-adapter examplify \
  --rubric-adapter-src path/to/exam_export.csv \
  --rubric-adapter examplify \
  --out-serializer csv \
  --out path/to/results.csv
```

Import point columns that were scored outside the engine:

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --raw-submissions-adapter csv \
  --point-column Q4=Q4_pts \
  --point-column Q5=Q5_pts \
  --question-set path/to/question_set.yaml \
  --rubric path/to/rubric.yaml \
  --rubric-override-results \
  --out path/to/graded_results.csv
```

Run grading in parallel:

```bash
gradeflow-engine grade \
  --submissions path/to/submissions.csv \
  --rubric path/to/rubric.yaml \
  --rubric-grading-parallel-jobs -1 \
  --rubric-grading-parallel-mode processes \
  --out path/to/graded_results.csv
```

CLI notes:

- Repeated `--*-config key=value` options are parsed with `yaml.safe_load`, so lists,
  booleans, numbers, and dictionaries can be passed as YAML literals.
- If `--question-set` and `--question-set-adapter-src` are both omitted, the engine
  infers the question set from submissions.
- If `--rubric` and `--rubric-adapter-src` are both omitted, the CLI parses and reports
  submissions but skips grading and output serialization.
- `--submissions-parser-strict` raises on unknown questions or parse failures. By
  default, those answers are retained as strings prefixed with `__UNPARSABLE__:`.
- `--rubric-grading-strict` raises on grading failures. By default, grading failures
  become zero-point or ungraded results with feedback.
- `--no-rubric-override-results` preserves pre-existing `result_map` entries, such as
  pass-through points imported from `--point-column`.
- `--no-rubric-grade-questions-without-rule` leaves uncovered questions out of
  `result_map` instead of assigning a zero-point `No Rule` result.
- `--rubric-grading-parallel-jobs -1` uses all available CPUs, capped by the number of
  submissions. `0` is invalid.

## Python API

Use `run_pipeline` for normal scripted grading.

```python
from gradeflow_engine.core import run_pipeline
from gradeflow_engine.io.sinks import StringSink
from gradeflow_engine.io.sources import StringSource

submissions_csv = """student_id,Q1,Q2
S1,red,10
S2,blue,8
S3,red,9
"""

rubric_yaml = """
rules:
  - type: MULTIPLE_CHOICE
    question_id: Q1
    answer:
      - red
    mode: ALL
  - type: NUMERIC_RANGE
    question_id: Q2
    min_value: 9
    max_value: 10
"""

sink = StringSink()
result = run_pipeline(
    submissions_source=StringSource(submissions_csv, media_type="text/csv", extension="csv"),
    submissions_adapter_name="csv",
    submissions_adapter_kwargs={"student_id_column": "student_id"},
    rubric_source=StringSource(rubric_yaml, media_type="application/yaml", extension="yaml"),
    rubric_serializer_name="yaml",
    graded_output_serializer_name="csv",
    graded_output_serializer_kwargs={
        "include_answers": True,
        "include_per_question_results": True,
        "include_total": True,
    },
    graded_output_sink=sink,
)

print(result.question_set)
print(result.validation_errors)
print(sink.data)
```

You can also compose the lower-level APIs directly:

```python
from gradeflow_engine.core import (
    dump_submissions_to_blob,
    load_raw_submissions_via_adapter,
    load_rubric_from_blob,
)
from gradeflow_engine.io.sources import StringSource
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.serializations.base import DataBlob

raw_submissions = load_raw_submissions_via_adapter(
    StringSource("student_id,Q1\nS1,red\n"),
    adapter_name="csv",
)
question_set = QuestionSet.infer(raw_submissions)
submissions = question_set.parse(raw_submissions)

rubric = load_rubric_from_blob(
    DataBlob(
        data=b"rules:\n  - type: BONUS\n    question_id: Q1\n",
        media_type="application/yaml",
        extension="yaml",
    ),
    serializer_name="yaml",
)

graded = rubric.grade(submissions, question_set.question_map)
blob = dump_submissions_to_blob(graded, serializer_name="csv")
print(blob.data.decode("utf-8"))
```

## Data Sources And Sinks

Built-in sources:

| Source | Purpose |
|---|---|
| `FileSource(path, media_type=None)` | Reads bytes from a file and infers media type from extension. |
| `StringSource(data, media_type="text/plain", extension="txt")` | Wraps text as UTF-8 bytes. |
| `BytesSource(data, media_type, extension)` | Wraps existing bytes. |

Built-in sinks:

| Sink | Purpose |
|---|---|
| `FileSink(path, force_extension=True)` | Writes a `DataBlob`, optionally replacing the file extension. |
| `StringSink()` | Stores decoded text in `.data`. |
| `BytesSink()` | Stores the written `DataBlob` in `.blob`. |

## Submission CSV Input

The built-in raw-submissions adapter is `csv`.

```csv
student_id,Q1,Q2,Q3
S1,red,10,foo
S2,blue,9,bar
S3,red,,baz
```

Configuration:

| Field | Default | Description |
|---|---|---|
| `student_id_column` | `student_id` | Column containing the student identifier. |
| `answer_columns` | `None` | Explicit answer columns. If omitted, all non-ID and non-point columns are answers. |
| `point_columns` | `None` | Mapping of `question_id -> CSV column` for pre-existing points. |

Pass-through point columns are loaded into each raw submission's `result_map`:

```csv
student_id,Q1,Q2,Q3,Q4_pts
S1,red,10,foo,8.0
S2,blue,9,bar,6.5
S3,red,,baz,
```

```python
raw_submissions = load_raw_submissions_via_adapter(
    source,
    adapter_name="csv",
    adapter_kwargs={"point_columns": {"Q4": "Q4_pts"}},
)
```

When a question set later parses the raw submissions, any pre-existing result whose
question ID appears in the question set has its `max_points` corrected to the question's
`max_points`.

Malformed CSV rows with missing cells raise `MalformedCsvRowError`. Missing student IDs
raise `MissingStudentIdError`.

## Question Sets

A question set is a Pydantic model serialized as YAML.

```yaml
question_map:
  Q1:
    type: CHOICE
    description: Choose a color
    max_points: 2.0
    config:
      delimiter: ","
      trim_whitespace: true
      normalize_case: true
    options:
      - red
      - blue
      - green
    allow_multiple: false
  Q2:
    type: NUMERIC
    max_points: 1.0
  Q3:
    type: TEXT
    max_points: 1.0
  Q4:
    type: MULTI_VALUED
    max_points: 3.0
    config:
      delimiter: "~"
      trim_whitespace: true
      normalize_case: false
      empty_marker: N/A
    value_types:
      - NUMERIC
      - TEXT
```

Supported question models:

| Type | Parsed answer | Notes |
|---|---|---|
| `TEXT` | `str | None` | `N/A` and `""` parse as `None` by default. |
| `NUMERIC` | `int | float | None` | Integers, floats, scientific notation, and simple fractions are supported. NaN and infinities are rejected. |
| `CHOICE` | `set[str]` | Uses `MultiValuedParserConfig`; options are trimmed and optionally case-normalized. |
| `MULTI_VALUED` | `list[str | int | float | None]` | Fixed number of slots, each declared as `TEXT` or `NUMERIC`. |

### Inference

`QuestionSet.infer(raw_submissions, ...)` applies this order per question ID:

1. `MULTI_VALUED`: every non-empty answer splits with the multi-value delimiter to the
   same cardinality greater than one.
2. `NUMERIC`: a strict majority of answers parse as numbers.
3. `CHOICE`: the observed choice values are non-empty and no more than
   `choice_option_limit`.
4. `TEXT`: fallback.

Inference defaults:

| Option | Default |
|---|---|
| `choice_delimiter` | `","` |
| `choice_option_limit` | `7` |
| `choice_normalize_case` | `True` |
| `multi_value_delimiter` | `"~"` |
| `empty_marker` | `"N/A"` |

Choice inference tokenizes with `choice_delimiter`; if any observed answer has more than
one choice token, `allow_multiple` is set to `True`. Multi-valued inference also infers
each slot as `NUMERIC` when numeric tokens are the majority for that slot, otherwise
`TEXT`.

### Drift And Sync

`QuestionSet.get_drift(raw_submissions)` reports:

- question IDs present in submissions but missing from the question set;
- question IDs present in the question set but absent from submissions;
- choice options observed in submissions but missing from existing `ChoiceQuestion` options.

`QuestionSet.sync_from_submissions(raw_submissions, ...)` returns a new question set that:

- infers missing submission question IDs;
- expands existing choice questions with newly observed options;
- keeps existing non-choice question definitions for observed question IDs.
- omits question IDs that are not present in the provided submissions.

## Rubrics

A rubric is a list of rules. Question rules include `question_id`; multi-question rules
own their target question IDs internally.

```yaml
rules:
  - type: MULTIPLE_CHOICE
    question_id: Q1
    answer:
      - red
    mode: ALL
  - type: NUMERIC_RANGE
    question_id: Q2
    min_value: 9
    max_value: 10
  - type: LENGTH
    question_id: Q3
    min_length: 3
    max_length: 50
    mode: characters
```

Rule scoring uses the target question's `max_points`; rules do not carry their own
point values. Rubric validation checks that referenced questions exist, rule types are
compatible with question types, nested rules are compatible, duplicate targets are not
introduced where uniqueness is required, and rule-specific constraints are satisfied.

`load_rubric_from_blob(..., strict=False)` can load a partial rubric from YAML by keeping
valid rules and skipping invalid rule entries. The CLI loads rubrics strictly.

## Grading Behavior

`Rubric.grade(...)` grades each submission and returns updated `Submission` models.

Important defaults:

| Option | Default | Effect |
|---|---|---|
| `strict` | `False` | Missing answers and grading exceptions become result entries instead of raising. |
| `override_results` | `True` | Rule results overwrite pre-existing `result_map` entries. |
| `grade_questions_without_rule` | `True` | Uncovered questions receive a zero-point `No Rule` result. |
| `parallel_jobs` | `1` | Sequential grading. Use `-1` for all available CPUs. |
| `parallel_mode` | `processes` | Passed to joblib as `prefer`, either `processes` or `threads`. |

Non-strict grading behavior:

- Missing answer for a targeted question: zero-point `No Answer` result.
- Exception while processing a rule: zero-point, `graded=False`, `Manual grading required`.
- Question with no rule and no existing result: zero-point `No Rule` result, unless
  `grade_questions_without_rule=False`.

Rubrics also expose coverage and maintenance helpers:

- `get_coverage(question_set)`;
- `get_target_question_ids()`;
- `get_referenced_question_ids()`;
- `get_stale_rule_references(question_set)`;
- `remove_stale_rules(question_set)`.

## Rule Catalogue

| Rule type | Scope | Compatible questions | Main fields |
|---|---|---|---|
| `TEXT_MATCH` | question, value | `TEXT`, `NUMERIC` | `answers` |
| `KEYWORDS` | question, value | `TEXT` | `keywords`, `mode` |
| `REGEX` | question, value | `TEXT` | `pattern`, `config` |
| `LENGTH` | question, value | `TEXT` | `min_length`, `max_length`, `mode` |
| `SIMILARITY` | question, value | `TEXT` | `references`, `threshold`, `algorithm` |
| `NUMBER_EQUAL` | question, value | `NUMERIC` | `answers`, `config.approximate`, `config.tolerance` |
| `NUMERIC_RANGE` | question, value | `NUMERIC` | `min_value`, `max_value` |
| `MULTIPLE_CHOICE` | question, value | `CHOICE` | `answer`, `mode` |
| `BONUS` | question, value | all question types | awards full points |
| `COMPOSITE` | question, value | `TEXT`, `NUMERIC` | nested value `rules`, `aggregation` |
| `MULTI_VALUED` | question, value | `MULTI_VALUED` | one nested value rule per slot, `aggregation` |
| `CUSTOM_CODE` | question, value | all question types | `code`, `parameters`, `mode` |
| `CODE_TESTS` | question, value | `TEXT` | `testcases`, `config`, `mode` |
| `ASSUMPTION_SET` | question | all question types | `assumptions`, `mode` |
| `CONDITIONAL` | global | all question types | `if_rules`, `then_rules`, `else_rules` |
| `ASSUMPTION_SET_MULTI` | global | all question types | multi-question `assumptions`, `mode` |
| `CUSTOM_CODE_MULTI` | global | all question types | `target_question_ids`, `code`, `parameters`, `mode` |

Common aggregation and mode values:

- Completeness modes: `ALL`, `ANY`, `PARTIAL`.
- Boolean modes: `AND`, `OR`.
- Assumption-set modes: `MAX`, `MIN`.
- Custom code modes: `PASS_FAIL`, `OUTPUT`.
- Multiple-choice modes: `ALL`, `CONTAIN`, `NOT_CONTAIN`, `ANY`, `PARTIAL`.

### Rule Examples

Text match:

```yaml
rules:
  - type: TEXT_MATCH
    question_id: Q1
    answers:
      - red
      - crimson
```

Keywords with partial credit:

```yaml
rules:
  - type: KEYWORDS
    question_id: Q3
    keywords:
      - duty
      - breach
      - causation
    mode: PARTIAL
```

Regex with flags:

```yaml
rules:
  - type: REGEX
    question_id: Q3
    pattern: "^foo.*bar$"
    config:
      ignore_case: true
      multi_line: false
      dotall: false
```

Similarity:

```yaml
rules:
  - type: SIMILARITY
    question_id: Q3
    references:
      - A reasonable reference answer
    threshold: 0.8
    algorithm: levenshtein
```

Numeric equality:

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

Numeric range:

```yaml
rules:
  - type: NUMERIC_RANGE
    question_id: Q2
    min_value: 0
    max_value: 10
```

Multiple choice:

```yaml
rules:
  - type: MULTIPLE_CHOICE
    question_id: Q1
    answer:
      - red
      - blue
    mode: PARTIAL
```

Composite:

```yaml
rules:
  - type: COMPOSITE
    question_id: Q3
    aggregation: ALL
    rules:
      - type: REGEX
        pattern: "foo"
      - type: LENGTH
        min_length: 3
        max_length: 100
```

Multi-valued answer:

```yaml
rules:
  - type: MULTI_VALUED
    question_id: Q4
    aggregation: PARTIAL
    rules:
      - type: NUMERIC_RANGE
        min_value: 0
        max_value: 10
      - type: TEXT_MATCH
        answers:
          - yes
```

Custom code:

```yaml
rules:
  - type: CUSTOM_CODE
    question_id: Q2
    mode: OUTPUT
    parameters:
      minimum:
        dtype: Float
        value: 0.0
      maximum:
        dtype: Float
        value: 10.0
    code: |
      passed = isinstance(answer, (int, float)) and minimum <= float(answer) <= maximum
      output = 1.0 if passed else 0.0
      feedback = f"Answer: {answer}"
```

Multi-question custom code:

```yaml
rules:
  - type: CUSTOM_CODE_MULTI
    target_question_ids:
      - Q1
      - Q2
    mode: PASS_FAIL
    code: |
      results = {}
      q1_ok = "red" in answer_map["Q1"]
      q2_ok = isinstance(answer_map["Q2"], (int, float)) and answer_map["Q2"] >= 9
      results["Q1"] = {"passed": q1_ok, "output": float(q1_ok), "feedback": "Color checked"}
      results["Q2"] = {"passed": q2_ok, "output": float(q2_ok), "feedback": "Number checked"}
```

Code tests:

```yaml
rules:
  - type: CODE_TESTS
    question_id: Q5
    mode: ALL
    testcases:
      - expression: "add(1, 2)"
        expected: "3"
      - expression: "add(-1, 1)"
        expected: "0"
    config:
      prepend_code: ""
      append_code: ""
      indent: 0
      time_limit: 5
```

Conditional:

```yaml
rules:
  - type: CONDITIONAL
    if_aggregation: AND
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

Assumption set:

```yaml
rules:
  - type: ASSUMPTION_SET
    question_id: Q1
    mode: MAX
    assumptions:
      - name: Literal answer
        weight: 1.0
        rule:
          type: TEXT_MATCH
          answers:
            - red
      - name: Thematic answer
        weight: 0.8
        rule:
          type: KEYWORDS
          keywords:
            - crimson
            - scarlet
          mode: ANY
```

Assumption set across questions:

```yaml
rules:
  - type: ASSUMPTION_SET_MULTI
    mode: MAX
    assumptions:
      - name: Scenario A
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
      - name: Scenario B
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

Bonus:

```yaml
rules:
  - type: BONUS
    question_id: Q4
```

## Custom Code Execution

`CUSTOM_CODE`, `CUSTOM_CODE_MULTI`, and `CODE_TESTS` use the Python executor in
`rules/executors/python.py`.

Execution model:

- Variables are encoded to JSON, with tagged support for `set`.
- A long-lived supervisor process receives requests.
- Each request runs in a disposable forked child process.
- Standard output and standard error are discarded in the child.
- Wall-clock timeouts raise `ExecutorTimeoutError`.
- Runtime failures raise `ExecutorRuntimeError` or become failed rule results, depending
  on the calling rule and strictness mode.

This process isolation is useful for cleanup and timeouts, but it is not a security
sandbox. Run untrusted student code inside a locked-down container or VM with appropriate
resource limits.

## Output Serialization

Built-in submissions serializers:

| Serializer | Direction | Notes |
|---|---|---|
| `csv` | dump only | Main gradebook output. |
| `json` | dump only | Encodes sets as sorted lists. |
| `yaml` | dump only | Dumps `Submission.model_dump()` values. |

CSV output configuration:

| Field | Default | Output |
|---|---|---|
| `student_id_column` | `student_id` | Student ID column name. |
| `include_answers` | `true` | One column per question ID. |
| `include_per_question_results` | `true` | `<qid>__points`, `<qid>__max_points`, `<qid>__passed`, `<qid>__percent`. |
| `include_feedback` | `true` | `<qid>__feedback`. |
| `include_remarks` | `true` | A combined `remarks` column with per-question feedback and totals. |
| `include_total` | `true` | `total_points`, `total_max_points`, `total_percent`. |
| `include_rounded_total` | `true` | Rounded total columns. |
| `rounding_base` | `0.5` | Nearest rounding base for rounded totals; set `0` to return unrounded values. |

Answer serialization:

- `set[str]`: natural-sorted and joined with `"; "`.
- `list`: joined with `" | "`.
- text and numeric answers: `str(answer)`.

`QuestionResult.points` and `QuestionResult.max_points` are rounded to two decimals by
their Pydantic validators.

## Examplify Adapter

The built-in `examplify` question-set and rubric adapters read CSV exports.

Shared options:

| Field | Default | Description |
|---|---|---|
| `include_thrown_out` | `False` | Include rows where `ThrowOut` is `true`. |
| `parse_answer_string` | `False` | Parse numeric-like fill-in-the-blank answer keys as numeric rules/questions. |
| `skip_empty_alternatives` | `True` | Ignore empty alternatives in `|`-separated FITB answers. |

Rubric-only options:

| Field | Default |
|---|---|
| `choice_mode` | `PARTIAL` |
| `multi_valued_mode` | `PARTIAL` |

Behavior:

- Question IDs are built as `Q{Seq}`.
- Rows with no `Seq` are skipped.
- Thrown-out rows are skipped unless `include_thrown_out=True`.
- Question points come from `Adjusted Points`, then `Original Points`, then `1.0`.
- Rubric rows with `GiveFullCreditToAllETs == true` are skipped.
- Choice answers use comma splitting, trimming, and lower-case normalization.
- FITB answers may contain markers like `{1} first, {2} second`; alternatives inside a
  blank are split with `|`.

## Contextual Rule Schemas

The engine can generate rule models shaped for a specific editing context. This lets
clients ask the engine which rule types are valid and which fields should be shown for
global rules, question rules, value-slot rules, and nested rule paths.

Important APIs:

```python
from gradeflow_engine.rules.context import RuleContext
from gradeflow_engine.rules.schema import (
    compatible_rule_classes,
    context_for_path,
    rule_class,
)

context = RuleContext(scope="question", question_set=question_set, question_id="Q1")
classes = compatible_rule_classes(context)
model = rule_class("MULTIPLE_CHOICE", context).from_context(context)
initial = rule_class("MULTIPLE_CHOICE", context).initial_value_from_context(context)
nested = context_for_path(context, "rules.0")
```

Schema extras live under `x-gradeflow`:

- `input`: generic rendering hint such as `code`, `string-list`, `rule`, or `rule-list`.
- `suggestions`: observed answer suggestions with counts, derived from submissions in the
  `RuleContext`.

## Registries And Extensibility

Built-in adapters:

| Registry | Key | Class |
|---|---|---|
| raw submissions | `csv` | `CsvRawSubmissionsAdapter` |
| question set | `examplify` | `ExamplifyQuestionSetAdapter` |
| rubric | `examplify` | `ExamplifyRubricAdapter` |

Built-in serializers:

| Registry | Key | Class |
|---|---|---|
| question set | `yaml` | `YamlQuestionSetSerializer` |
| rubric | `yaml` | `YamlRubricSerializer` |
| submissions | `csv` | `CsvSubmissionsSerializer` |
| submissions | `json` | `JsonSubmissionsSerializer` |
| submissions | `yaml` | `YamlSubmissionsSerializer` |

Discover and retrieve registered components:

```python
from gradeflow_engine.core import (
    get_raw_submissions_adapter_class,
    list_available_question_set_adapters,
    list_available_question_set_serializers,
    list_available_raw_submissions_adapters,
    list_available_rubric_adapters,
    list_available_rubric_serializers,
    list_available_submissions_serializers,
)

print(list_available_raw_submissions_adapters())
print(list_available_question_set_adapters())
print(list_available_rubric_adapters())
print(list_available_question_set_serializers())
print(list_available_rubric_serializers())
print(list_available_submissions_serializers())

CsvAdapter = get_raw_submissions_adapter_class("csv")
```

### Add A Raw Submissions Adapter

```python
from typing import ClassVar, Literal

from pydantic import BaseModel

from gradeflow_engine.adapters.base import BaseAdapter
from gradeflow_engine.adapters.registries import RawSubmissionsAdapter, raw_submissions_adapter_registry
from gradeflow_engine.exceptions import GradeFlowValidationError
from gradeflow_engine.io.sources import DataSource
from gradeflow_engine.submissions.models import RawSubmission


class MyAdapterConfig(BaseModel):
    format: Literal["my_format"] = "my_format"


class MyAdapter(BaseAdapter[MyAdapterConfig, list[RawSubmission]], RawSubmissionsAdapter):
    name: ClassVar[Literal["my_adapter"]] = "my_adapter"
    config: MyAdapterConfig = MyAdapterConfig()
    _validation_error_cls = GradeFlowValidationError

    def _load(self, source: DataSource) -> list[RawSubmission]:
        blob = source.read()
        text = blob.data.decode("utf-8")
        # Parse text and return RawSubmission objects.
        return []


raw_submissions_adapter_registry.register("my_adapter", MyAdapter)
```

### Add A Serializer

```python
from typing import Literal

from pydantic import BaseModel

from gradeflow_engine.mixins import ConfigurableMixin
from gradeflow_engine.question_sets.model import QuestionSet
from gradeflow_engine.serializations.base import DataBlob, Serializer
from gradeflow_engine.serializations.registries import question_set_serializer_registry


class MySerializerConfig(BaseModel):
    format: Literal["my_format"] = "my_format"


class MySerializer(ConfigurableMixin[MySerializerConfig], Serializer[QuestionSet]):
    format = "my_format"
    media_type = "text/plain"
    config: MySerializerConfig = MySerializerConfig()

    def loads(self, blob: DataBlob, *, strict: bool = True) -> QuestionSet:
        return QuestionSet(question_map={})

    def dumps(self, obj: QuestionSet) -> DataBlob:
        return DataBlob(data=b"", media_type=self.media_type, extension="txt")


question_set_serializer_registry.register("my_format", MySerializer)
```

### Add A Rule

Add a value rule by subclassing `BaseRule`. Add a question rule by mixing in
`BaseSingleQuestionRule`; add a global rule by subclassing `BaseMultiQuestionRule`.

```python
from typing import Literal

from pydantic import computed_field

from gradeflow_engine.questions.types import Answer, QuestionType
from gradeflow_engine.rules.models.base import (
    BaseRule,
    BaseSingleQuestionRule,
    rule_display_name_field,
    rule_question_types_field,
    rule_type_field,
)
from gradeflow_engine.rules.result import Result


class MyRule(BaseRule):
    type: Literal["MY_RULE"] = rule_type_field("MY_RULE")
    display_name: Literal["My Rule"] = rule_display_name_field("My Rule")
    question_types: frozenset[QuestionType] = rule_question_types_field({"TEXT"})
    expected: str

    @computed_field
    @property
    def description(self) -> str:
        return f"Answer must equal `{self.expected}`."

    def _process_answer(self, answer: Answer) -> Result:
        passed = str(answer) == self.expected
        return Result(
            output=passed,
            passed=passed,
            feedback="Correct." if passed else f"Expected {self.expected!r}.",
            rule=self.display_name,
        )


class MyQuestionRule(MyRule, BaseSingleQuestionRule):
    pass
```

To make the rule loadable from YAML, import it and include it in the relevant
discriminated union in `gradeflow_engine/rules/models/__init__.py`, then rebuild any
models that need forward-reference updates.

## Project Map

```text
gradeflow_engine/
  adapters/          External format adapters: CSV submissions, Examplify question sets/rubrics
  cli/               Typer CLI commands and Rich display helpers
  io/                DataSource and DataSink implementations
  question_sets/     QuestionSet model, inference, drift detection, sync
  questions/         Question models, parser config, answer types, parse utilities
  rubrics/           Rubric model, validation, coverage, grading orchestration
  rules/             Rule models, schema context, aggregations, Python executor
  serializations/    YAML/CSV/JSON serializers and serializer registries
  core.py            Public API and pipeline orchestration
  exceptions.py      Engine exception hierarchy and formatted messages
  registry.py        Generic registry implementation
  mixins.py          Shared configurable mixin
  py.typed           PEP 561 marker
```

## Development

```bash
cd engine
pip install -e ".[dev]"
ruff check .
ruff format .
mypy gradeflow_engine
pytest
```

Coverage is configured for the `gradeflow_engine` package with a `fail_under` value of 90.
Tests that need the ML extra are marked `ml`.

## License

MIT License.

## Acknowledgements

- [Pydantic](https://docs.pydantic.dev/) for model validation and serialization.
- [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/) for the CLI.
- [PyYAML](https://pyyaml.org/) for YAML I/O.
- [joblib](https://joblib.readthedocs.io/) for parallel grading.
- [RapidFuzz](https://github.com/maxbachmann/RapidFuzz) for fuzzy matching.
- [FastEmbed](https://github.com/qdrant/fastembed) for optional transformer similarity.
- [natsort](https://github.com/SethMMorton/natsort) for natural question ordering.
