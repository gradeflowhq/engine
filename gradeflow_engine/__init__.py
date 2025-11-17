# Import submodules to register loaders/savers.

# Question set
from .question_sets import loaders as question_set_loaders
from .question_sets import savers as question_set_savers

# Rubrics
from .rubrics import loaders as rubric_loaders

# Submissions
from .submissions import loaders as submissions_loaders
from .submissions import savers as submissions_savers

__all__ = [
    "question_set_loaders",
    "question_set_savers",
    "rubric_loaders",
    "submissions_loaders",
    "submissions_savers",
]
