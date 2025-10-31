"""
Tests for the rule registry.
"""

import pytest

from gradeflow_engine.rules.registry import RuleRegistry, rule_registry


def test_registry_singleton():
    """Test that rule_registry is a singleton instance."""
    assert isinstance(rule_registry, RuleRegistry)


def test_registry_has_all_rule_types():
    """Test that all expected rule types are registered."""
    expected_types = {
        "EXACT_MATCH",
        "NUMERIC_RANGE",
        "MULTIPLE_CHOICE",
        "LENGTH",
        "SIMILARITY",
        "CONDITIONAL",
        "ASSUMPTION_SET",
        "PROGRAMMABLE",
        "KEYWORD",
        "REGEX",
        "COMPOSITE",
    }

    registered_types = set(rule_registry.get_all_processors().keys())
    assert expected_types == registered_types


def test_get_processor_for_valid_type():
    """Test getting a processor for a valid rule type."""
    processor = rule_registry.get_processor("EXACT_MATCH")
    assert callable(processor)


def test_get_processor_for_invalid_type():
    """Test that getting an invalid processor raises ValueError."""
    with pytest.raises(ValueError, match="Unknown rule type"):
        rule_registry.get_processor("INVALID_TYPE")


def test_get_model_for_valid_type():
    """Test getting a model for a valid rule type."""
    model = rule_registry.get_model("EXACT_MATCH")
    assert model is not None
    assert hasattr(model, "model_validate")


def test_get_model_for_invalid_type():
    """Test that getting an invalid model raises ValueError."""
    with pytest.raises(ValueError, match="Unknown rule type"):
        rule_registry.get_model("INVALID_TYPE")


def test_is_registered():
    """Test the is_registered method."""
    assert rule_registry.is_registered("EXACT_MATCH")
    assert not rule_registry.is_registered("INVALID_TYPE")


def test_registration_signature_validation():
    """Test that invalid processor signatures are rejected."""

    # Try to register a processor with wrong number of parameters
    def invalid_processor_no_params():
        pass

    def invalid_processor_one_param(rule):
        pass

    def invalid_processor_three_params(rule, submission, extra):
        pass

    # These should raise ValueError due to signature validation
    with pytest.raises(ValueError, match="must accept exactly 2 parameters"):
        rule_registry.register("TEST_INVALID_0", invalid_processor_no_params, type)

    with pytest.raises(ValueError, match="must accept exactly 2 parameters"):
        rule_registry.register("TEST_INVALID_1", invalid_processor_one_param, type)

    with pytest.raises(ValueError, match="must accept exactly 2 parameters"):
        rule_registry.register("TEST_INVALID_3", invalid_processor_three_params, type)


def test_get_all_processors_returns_copy():
    """Test that get_all_processors returns a copy, not the original dict."""
    processors1 = rule_registry.get_all_processors()
    processors2 = rule_registry.get_all_processors()

    # Should be equal but not the same object
    assert processors1 == processors2
    assert processors1 is not processors2


def test_get_all_rule_types_returns_copy():
    """Test that get_all_rule_types returns a copy, not the original dict."""
    types1 = rule_registry.get_all_rule_types()
    types2 = rule_registry.get_all_rule_types()

    # Should be equal but not the same object
    assert types1 == types2
    assert types1 is not types2
