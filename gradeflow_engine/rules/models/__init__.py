from typing import Annotated

from pydantic import Discriminator

from .assumption_set import (
    Assumption,
    AssumptionSetMultiQuestionRule,
    AssumptionSetQuestionRule,
    MultiQuestionAssumption,
)
from .bonus import BonusQuestionRule, BonusRule
from .code_tests import CodeTestQuestionRule, CodeTestRule
from .composite import CompositeQuestionRule, CompositeRule
from .conditional import ConditionalMultiQuestionRule
from .custom_code import CustomCodeMultiQuestionRule, CustomCodeQuestionRule, CustomCodeRule
from .keywords import KeywordsQuestionRule, KeywordsRule
from .length import LengthQuestionRule, LengthRule
from .multi_valued import MultiValuedQuestionRule, MultiValuedRule
from .multiple_choice import MultipleChoiceQuestionRule, MultipleChoiceRule
from .number_equal import NumberEqualQuestionRule, NumberEqualRule
from .numeric_range import NumericRangeQuestionRule, NumericRangeRule
from .regex import RegexQuestionRule, RegexRule
from .similarity import SimilarityQuestionRule, SimilarityRule
from .text_match import TextMatchQuestionRule, TextMatchRule

SingleTargetRule = Annotated[
    BonusRule
    | CompositeRule
    | CustomCodeRule
    | CodeTestRule
    | SimilarityRule
    | TextMatchRule
    | KeywordsRule
    | RegexRule
    | LengthRule
    | MultiValuedRule
    | MultipleChoiceRule
    | NumberEqualRule
    | NumericRangeRule,
    Discriminator("type"),
]

SingleTargetQuestionRule = Annotated[
    AssumptionSetQuestionRule
    | BonusQuestionRule
    | CompositeQuestionRule
    | CustomCodeQuestionRule
    | CodeTestQuestionRule
    | SimilarityQuestionRule
    | TextMatchQuestionRule
    | KeywordsQuestionRule
    | RegexQuestionRule
    | LengthQuestionRule
    | MultiValuedQuestionRule
    | MultipleChoiceQuestionRule
    | NumberEqualQuestionRule
    | NumericRangeQuestionRule,
    Discriminator("type"),
]

# Trigger Pydantic to rebuild models to register discriminators
CompositeRule.model_rebuild()
CompositeQuestionRule.model_rebuild()
MultiValuedRule.model_rebuild()
MultiValuedQuestionRule.model_rebuild()
AssumptionSetQuestionRule.model_rebuild()
AssumptionSetMultiQuestionRule.model_rebuild()
Assumption.model_rebuild()
MultiQuestionAssumption.model_rebuild()
ConditionalMultiQuestionRule.model_rebuild()


MultiTargetQuestionRule = Annotated[
    AssumptionSetMultiQuestionRule | ConditionalMultiQuestionRule | CustomCodeMultiQuestionRule,
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
