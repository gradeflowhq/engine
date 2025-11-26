from typing import Annotated

from pydantic import Discriminator

from .assumption_set import Assumption, AssumptionSetMultiQuestionRule
from .composite import CompositeQuestionRule, CompositeRule
from .conditional import ConditionalMultiQuestionRule
from .exact_match import ExactMatchQuestionRule, ExactMatchRule
from .keywords import KeywordsQuestionRule, KeywordsRule
from .length import LengthQuestionRule, LengthRule
from .multi_valued import MultiValuedQuestionRule, MultiValuedRule
from .multiple_choice import MultipleChoiceQuestionRule, MultipleChoiceRule
from .numeric_range import NumericRangeQuestionRule, NumericRangeRule
from .programmable import ProgrammableQuestionRule, ProgrammableRule
from .programming import ProgrammingQuestionRule, ProgrammingRule
from .regex import RegexQuestionRule, RegexRule

SingleTargetRule = Annotated[
    CompositeRule
    | ProgrammableRule
    | ProgrammingRule
    | ExactMatchRule
    | KeywordsRule
    | RegexRule
    | LengthRule
    | MultiValuedRule
    | MultipleChoiceRule
    | NumericRangeRule,
    Discriminator("type"),
]

SingleTargetQuestionRule = Annotated[
    CompositeQuestionRule
    | ProgrammableQuestionRule
    | ProgrammingQuestionRule
    | ExactMatchQuestionRule
    | KeywordsQuestionRule
    | RegexQuestionRule
    | LengthQuestionRule
    | MultiValuedQuestionRule
    | MultipleChoiceQuestionRule
    | NumericRangeQuestionRule,
    Discriminator("type"),
]

# Trigger Pydantic to rebuild models to register discriminators
CompositeRule.model_rebuild()
CompositeQuestionRule.model_rebuild()
MultiValuedRule.model_rebuild()
MultiValuedQuestionRule.model_rebuild()
AssumptionSetMultiQuestionRule.model_rebuild()
Assumption.model_rebuild()
ConditionalMultiQuestionRule.model_rebuild()


MultiTargetQuestionRule = Annotated[
    AssumptionSetMultiQuestionRule | ConditionalMultiQuestionRule,
    Discriminator("type"),
]

Rule = Annotated[
    SingleTargetRule | MultiTargetQuestionRule,
    Discriminator("type"),
]

QuestionRule = Annotated[
    SingleTargetQuestionRule | MultiTargetQuestionRule,
    Discriminator("type"),
]
