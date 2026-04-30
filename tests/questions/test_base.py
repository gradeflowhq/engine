import pytest

from gradeflow_engine.questions.models.base import BaseQuestion


def test_base_question_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseQuestion()  # type: ignore[abstract]
