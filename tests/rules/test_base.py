from typing import Any, cast

import pytest

from gradeflow_engine.rules.models.base import (
    BaseMultiQuestionRule,
    BaseRule,
    BaseSingleQuestionRule,
)
from gradeflow_engine.rules.result import Result


def test_rule_base_classes_are_abstract() -> None:
    with pytest.raises(TypeError):
        BaseRule()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        BaseSingleQuestionRule(question_id="Q1")  # type: ignore[abstract]


def test_rule_base_unimplemented_methods_and_default_paths() -> None:
    description_getter = cast(property, BaseRule.__dict__["description"]).fget
    assert description_getter is not None

    with pytest.raises(NotImplementedError):
        description_getter(cast(Any, object()))
    with pytest.raises(NotImplementedError):
        BaseRule._process_answer(cast(Any, object()), "x")
    assert (
        BaseSingleQuestionRule.compute_points(
            cast(BaseSingleQuestionRule, object()),
            Result(output=0, passed=False, feedback="", rule="x"),
            1.0,
        )
        == 0.0
    )
    with pytest.raises(NotImplementedError):
        BaseMultiQuestionRule._process_answer(cast(Any, object()), "x")
    with pytest.raises(NotImplementedError):
        BaseMultiQuestionRule.process_submission(cast(Any, object()), {}, {})
