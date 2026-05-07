from typing import Literal

NumericAggregation = Literal["SUM", "AVERAGE", "MIN", "MAX", "COUNT"]
BooleanAggregation = Literal["AND", "OR"]
CompletenessAggregation = Literal["ALL", "ANY", "PARTIAL"]
AggregationType = NumericAggregation | BooleanAggregation | CompletenessAggregation

RuleValidationError = str
