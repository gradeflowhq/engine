"""
Protocol definitions for gradeflow engine.

Defines interfaces that rules can optionally implement for extended functionality.
"""

from typing import Protocol, runtime_checkable

from .schema import QuestionSchema


@runtime_checkable
class SchemaValidatable(Protocol):
    """
    Protocol for rules that can validate themselves against a question schema.

    Rules can optionally implement this protocol to provide schema-specific
    validation logic. This avoids coupling the schema validation to specific
    rule types.
    """

    def validate_against_schema(
        self, question_id: str, schema: QuestionSchema, rule_description: str
    ) -> list[str]:
        """
        Validate this rule against a question schema.

        Args:
            question_id: The question ID being validated
            schema: The question schema to validate against
            rule_description: Human-readable description of the rule for error messages

        Returns:
            List of validation error messages (empty if valid)
        """
        ...
