"""Grading rules package with auto-discovery and registration."""

import importlib
import pkgutil
from pathlib import Path

from .registry import rule_registry

# Auto-discover and import all rule modules
_rules_path = Path(__file__).parent
for module_info in pkgutil.iter_modules([str(_rules_path)]):
    if module_info.name not in ("__init__", "registry"):
        importlib.import_module(f".{module_info.name}", package=__name__)

# Import all rule models for re-export (after auto-discovery to avoid circular imports)
from .assumption_set.model import AnswerSet, AssumptionSetRule  # noqa: E402
from .composite.model import CompositeRule  # noqa: E402
from .conditional.model import ConditionalRule  # noqa: E402
from .exact_match.model import ExactMatchRule  # noqa: E402
from .keyword.model import KeywordRule  # noqa: E402
from .length.model import LengthRule  # noqa: E402
from .multiple_choice.model import MultipleChoiceRule  # noqa: E402
from .numeric_range.model import NumericRangeRule  # noqa: E402
from .programmable.model import ProgrammableRule  # noqa: E402
from .regex.model import RegexRule  # noqa: E402
from .similarity.model import SimilarityRule  # noqa: E402

__all__ = [
    "rule_registry",
    # Rule models
    "ExactMatchRule",
    "NumericRangeRule",
    "MultipleChoiceRule",
    "LengthRule",
    "SimilarityRule",
    "ConditionalRule",
    "AssumptionSetRule",
    "AnswerSet",
    "ProgrammableRule",
    "KeywordRule",
    "RegexRule",
    "CompositeRule",
]
