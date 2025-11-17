from typing import Literal

# Question Types
QuestionId = str
QuestionType = Literal["TEXT", "CHOICE", "NUMERIC", "MULTI_VALUED"]

# Answer Types
TextAnswer = str
NumericAnswer = float | int
SingleValuedAnswer = TextAnswer | NumericAnswer

ChoiceAnswer = set[str]
MultiValuedAnswer = list[SingleValuedAnswer]

Answer = SingleValuedAnswer | ChoiceAnswer | MultiValuedAnswer
