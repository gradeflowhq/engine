"""Rule registry for grading rules."""

import inspect
from collections.abc import Callable


class RuleRegistry:
    """Registry for grading rules."""

    _processors: dict[str, Callable] = {}
    _rule_types: dict[str, type] = {}

    @classmethod
    def register(
        cls,
        rule_type: str,
        processor: Callable,
        model: type,
    ) -> None:
        """Register a grading rule processor and model.

        Args:
            rule_type: The type identifier for the rule (e.g., "exact_match")
            processor: The function that processes the rule
            model: The Pydantic model class for the rule

        Raises:
            ValueError: If processor signature is invalid
        """
        # Validate processor signature
        try:
            sig = inspect.signature(processor)
            params = list(sig.parameters.values())

            if len(params) != 2:
                raise ValueError(
                    f"Processor for '{rule_type}' must accept exactly 2 parameters "
                    f"(rule, submission), got {len(params)}"
                )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid processor signature for '{rule_type}': {e}") from e

        cls._processors[rule_type] = processor
        cls._rule_types[rule_type] = model

    @classmethod
    def get_processor(cls, rule_type: str) -> Callable:
        """Get the processor for a rule type.

        Args:
            rule_type: The type identifier for the rule

        Returns:
            The processor function

        Raises:
            ValueError: If the rule type is not registered
        """
        if rule_type not in cls._processors:
            raise ValueError(f"Unknown rule type: {rule_type}")
        return cls._processors[rule_type]

    @classmethod
    def get_model(cls, rule_type: str) -> type:
        """Get the model class for a rule type.

        Args:
            rule_type: The type identifier for the rule

        Returns:
            The Pydantic model class

        Raises:
            ValueError: If the rule type is not registered
        """
        if rule_type not in cls._rule_types:
            raise ValueError(f"Unknown rule type: {rule_type}")
        return cls._rule_types[rule_type]

    @classmethod
    def get_all_processors(cls) -> dict[str, Callable]:
        """Get all registered processors.

        Returns:
            Dictionary mapping rule types to their processors
        """
        return cls._processors.copy()

    @classmethod
    def get_all_rule_types(cls) -> dict[str, type]:
        """Get all registered rule types.

        Returns:
            Dictionary mapping rule types to their model classes
        """
        return cls._rule_types.copy()

    @classmethod
    def is_registered(cls, rule_type: str) -> bool:
        """Check if a rule type is registered.

        Args:
            rule_type: The type identifier for the rule

        Returns:
            True if the rule type is registered, False otherwise
        """
        return rule_type in cls._processors


# Singleton instance
rule_registry = RuleRegistry()
