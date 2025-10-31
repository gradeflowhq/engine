"""
Integration tests for the grading engine with multiple rules.

Tests the grading engine's ability to:
- Apply multiple rules to the same question
- Grade multiple questions
- Calculate total scores correctly
- Generate proper feedback
- Handle edge cases

Run with: pytest tests/test_integration.py -v
"""

import os

import pytest

from gradeflow_engine import (
    CompositeRule,
    ConditionalRule,
    ExactMatchRule,
    KeywordRule,
    LengthRule,
    NumericRangeRule,
    Rubric,
    Submission,
    grade,
    grade_from_files,
    load_rubric,
    save_results_yaml,
)


class TestEndToEndGrading:
    """Test complete grading workflow from rubric to results."""

    def test_simple_grading_workflow(self):
        """Test basic grading workflow with multiple questions."""
        # Create rubric
        rubric = Rubric(
            name="Simple Quiz",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="Paris", max_points=10.0),
                ExactMatchRule(question_id="q2", correct_answer="London", max_points=10.0),
                NumericRangeRule(
                    question_id="q3", correct_value=42.0, tolerance=2.0, max_points=15.0
                ),
            ],
        )

        # Create submissions
        submissions = [
            Submission(student_id="student1", answers={"q1": "Paris", "q2": "London", "q3": "42"}),
            Submission(student_id="student2", answers={"q1": "Paris", "q2": "Berlin", "q3": "40"}),
            Submission(student_id="student3", answers={"q1": "Rome", "q2": "London", "q3": "50"}),
        ]

        # Grade submissions
        results = grade(rubric, submissions)

        # Verify results structure
        assert len(results.results) == 3

        # Student 1: All correct
        assert results.results[0].student_id == "student1"
        assert results.results[0].total_points == 35.0
        assert results.results[0].percentage == 100.0

        # Student 2: q1 + q3 correct
        assert results.results[1].student_id == "student2"
        assert results.results[1].total_points == 25.0

        # Student 3: q2 correct only
        assert results.results[2].student_id == "student3"
        assert results.results[2].total_points == 10.0

    def test_conditional_grading_workflow(self):
        """Test workflow with conditional rules."""
        rubric = Rubric(
            name="Conditional Quiz",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="A", max_points=5.0),
                ConditionalRule(
                    if_question="q1",
                    if_answer="A",
                    then_question="q2",
                    then_correct_answer="B",
                    max_points=10.0,
                    description="If q1 is A, then q2 should be B",
                ),
            ],
        )

        submissions = [
            Submission(student_id="s1", answers={"q1": "A", "q2": "B"}),  # Both correct
            Submission(
                student_id="s2", answers={"q1": "A", "q2": "C"}
            ),  # Condition met, wrong answer
            Submission(student_id="s3", answers={"q1": "X", "q2": "B"}),  # Condition not met
        ]

        results = grade(rubric, submissions)

        assert results.results[0].total_points == 15.0  # 5 + 10
        assert results.results[1].total_points == 5.0  # 5 + 0 (condition met but wrong)
        assert results.results[2].total_points == 0.0  # 0 (q1 wrong)

    def test_composite_rule_workflow(self):
        """Test workflow with composite rules."""
        rubric = Rubric(
            name="Composite Quiz",
            rules=[
                CompositeRule(
                    question_id="essay",
                    mode="WEIGHTED",
                    weights=[0.5, 0.5],
                    rules=[
                        KeywordRule(
                            question_id="essay",
                            required_keywords=["python", "programming"],
                            points_per_required=5.0,
                        ),
                        LengthRule(
                            question_id="essay",
                            min_words=20,
                            max_words=100,
                            max_points=10.0,
                        ),
                    ],
                ),
            ],
        )

        submissions = [
            Submission(
                student_id="s1",
                answers={"essay": "Python programming is great. " + " ".join(["word"] * 20)},
            ),
            Submission(
                student_id="s2",
                answers={"essay": "Python is great"},
            ),
        ]

        results = grade(rubric, submissions)

        # s1: keywords=10.0, length=10.0 -> weighted = 0.5*10 + 0.5*10 = 10.0 points
        assert results.results[0].total_points == 10.0

        # s2: keywords=5.0, length=0 -> weighted = 0.5*5 + 0.5*0 = 2.5 points
        assert results.results[1].total_points == 2.5


class TestYAMLIntegration:
    """Test loading and grading from YAML files."""

    def test_load_simple_yaml_rubric(self, tmp_path):
        """Test loading a simple YAML rubric."""
        rubric_yaml = """
name: Test Rubric
rules:
  - type: EXACT_MATCH
    question_id: q1
    correct_answer: Paris
    max_points: 10.0
    case_sensitive: false
  - type: NUMERIC_RANGE
    question_id: q2
    correct_value: 100.0
    tolerance: 5.0
    max_points: 15.0
"""
        # Write YAML file
        rubric_file = tmp_path / "rubric.yaml"
        rubric_file.write_text(rubric_yaml)

        # Load rubric
        rubric = load_rubric(str(rubric_file))

        # Verify loaded correctly
        assert rubric.name == "Test Rubric"
        assert len(rubric.rules) == 2
        assert rubric.rules[0].type == "EXACT_MATCH"
        assert rubric.rules[1].type == "NUMERIC_RANGE"

    def test_load_comprehensive_yaml_rubric(self):
        """Test loading the comprehensive example rubric."""
        rubric_path = "examples/comprehensive_rubric.yaml"

        # Skip if file doesn't exist
        if not os.path.exists(rubric_path):
            pytest.skip("comprehensive_rubric.yaml not found")

        # Load rubric
        rubric = load_rubric(rubric_path)

        # Verify it loaded
        assert rubric.name is not None
        assert len(rubric.rules) > 0

        # Verify all rule types are present (should have examples of all 11 types)
        rule_types = {rule.type for rule in rubric.rules}
        assert "EXACT_MATCH" in rule_types
        assert "COMPOSITE" in rule_types

    def test_grade_from_yaml_and_csv(self, tmp_path):
        """Test complete workflow: load YAML + CSV, grade, save results."""
        # Create rubric YAML
        rubric_yaml = """
name: Integration Test Rubric
rules:
  - type: EXACT_MATCH
    question_id: capital_france
    correct_answer: Paris
    max_points: 10.0
  - type: KEYWORD
    question_id: essay
    required_keywords: ["python", "programming"]
    points_per_required: 5.0
"""
        rubric_file = tmp_path / "rubric.yaml"
        rubric_file.write_text(rubric_yaml)

        # Create submissions CSV
        csv_content = """student_id,capital_france,essay
student1,Paris,I love Python programming
student2,London,I love Python
student3,Paris,I love Java
"""
        csv_file = tmp_path / "submissions.csv"
        csv_file.write_text(csv_content)

        # Grade from files
        results = grade_from_files(
            rubric_path=str(rubric_file),
            submissions_csv_path=str(csv_file),
        )

        # Verify results
        assert len(results.results) == 3

        # student1: capital correct + both keywords = 20
        assert results.results[0].total_points == 20.0

        # student2: capital wrong + one keyword = 5
        assert results.results[1].total_points == 5.0

        # student3: capital correct + no keywords = 10
        assert results.results[2].total_points == 10.0

        # Save results
        output_file = tmp_path / "results.yaml"
        save_results_yaml(results, str(output_file))

        # Verify file was created
        assert output_file.exists()
        assert output_file.stat().st_size > 0


class TestMultipleRulesPerQuestion:
    """Test scenarios with multiple rules grading the same question."""

    def test_multiple_rules_same_question_additive(self):
        """Test that multiple rules on same question add points."""
        rubric = Rubric(
            name="Multi-Rule Test",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="Paris", max_points=10.0),
                KeywordRule(
                    question_id="q1", required_keywords=["capital"], required_points_per_keyword=5.0
                ),
                LengthRule(question_id="q1", min_chars=3, max_chars=10, max_points=3.0),
            ],
        )

        submission = Submission(student_id="s1", answers={"q1": "Paris"})
        results = grade(rubric, [submission])

        # Should get points from all three rules
        assert results.results[0].total_points == 13.0  # 10 + 0 + 3

    def test_multiple_rules_different_questions(self):
        """Test grading with many questions and rules."""
        rubric = Rubric(
            name="Large Rubric",
            rules=[
                ExactMatchRule(question_id=f"q{i}", correct_answer=f"answer{i}", max_points=5.0)
                for i in range(10)
            ],
        )

        # Perfect submission
        perfect_answers = {f"q{i}": f"answer{i}" for i in range(10)}
        perfect_submission = Submission(student_id="perfect", answers=perfect_answers)

        # Partial submission (only even questions)
        partial_answers = {f"q{i}": f"answer{i}" for i in range(0, 10, 2)}
        partial_submission = Submission(student_id="partial", answers=partial_answers)

        results = grade(rubric, [perfect_submission, partial_submission])

        assert results.results[0].total_points == 50.0  # All 10 questions
        assert results.results[1].total_points == 25.0  # 5 questions


class TestEdgeCasesIntegration:
    """Test edge cases in real scenarios."""

    def test_empty_submissions_list(self):
        """Test grading with no submissions."""
        rubric = Rubric(
            name="Test",
            rules=[ExactMatchRule(question_id="q1", correct_answer="A", max_points=10.0)],
        )

        results = grade(rubric, [])

        assert len(results.results) == 0
        assert results.metadata is not None

    def test_submission_missing_all_answers(self):
        """Test submission with no answers to graded questions."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="A", max_points=10.0),
                ExactMatchRule(question_id="q2", correct_answer="B", max_points=10.0),
            ],
        )

        submission = Submission(student_id="s1", answers={})
        results = grade(rubric, [submission])

        assert results.results[0].total_points == 0.0
        assert results.results[0].max_points == 20.0
        assert results.results[0].percentage == 0.0

    def test_submission_with_extra_answers(self):
        """Test submission with answers to questions not in rubric."""
        rubric = Rubric(
            name="Test",
            rules=[ExactMatchRule(question_id="q1", correct_answer="A", max_points=10.0)],
        )

        submission = Submission(
            student_id="s1",
            answers={"q1": "A", "q2": "B", "q3": "C"},  # q2, q3 not graded
        )
        results = grade(rubric, [submission])

        # Should only grade q1, ignore others
        assert results.results[0].total_points == 10.0
        assert len(results.results[0].grade_details) == 1

    def test_unicode_content(self):
        """Test grading with Unicode characters."""
        rubric = Rubric(
            name="Test Unicode",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="París", max_points=10.0),
                KeywordRule(
                    question_id="q2", required_keywords=["日本", "中国"], points_per_required=5.0
                ),
            ],
        )

        submission = Submission(
            student_id="s1",
            answers={"q1": "París", "q2": "日本 中国 français"},
        )
        results = grade(rubric, [submission])

        # q1=10.0, q2=10.0 (2 keywords * 5.0)
        assert results.results[0].total_points == 20.0

    def test_large_text_answers(self):
        """Test grading with very long text answers."""
        rubric = Rubric(
            name="Test Large Text",
            rules=[
                LengthRule(question_id="essay", min_words=100, max_words=500, max_points=20.0),
                KeywordRule(
                    question_id="essay", required_keywords=["important"], points_per_required=5.0
                ),
            ],
        )

        # Generate long answer (200 words)
        long_answer = "important " + " ".join([f"word{i}" for i in range(199)])
        submission = Submission(student_id="s1", answers={"essay": long_answer})

        results = grade(rubric, [submission])

        # length=20.0, keyword=5.0
        assert results.results[0].total_points == 25.0


class TestComplexScenarios:
    """Test complex real-world grading scenarios."""

    def test_progressive_difficulty_quiz(self):
        """Test quiz where later questions depend on earlier ones."""
        rubric = Rubric(
            name="Progressive Quiz",
            rules=[
                # Basic question
                ExactMatchRule(question_id="q1_basics", correct_answer="yes", max_points=5.0),
                # If they got basics right, check advanced (just checks for specific keyword)
                ConditionalRule(
                    if_question="q1_basics",
                    if_answer="yes",
                    then_question="q2_code",
                    then_correct_answer="function",
                    max_points=10.0,
                ),
                # Separately grade an essay question with composite rules
                CompositeRule(
                    question_id="q3_essay",
                    mode="WEIGHTED",
                    weights=[0.5, 0.5],
                    rules=[
                        LengthRule(
                            question_id="q3_essay",
                            min_words=20,
                            max_words=100,
                            max_points=10.0,
                        ),
                        KeywordRule(
                            question_id="q3_essay",
                            optional_keywords=["analysis", "detailed", "comprehensive"],
                            points_per_optional=2.0,
                            max_optional_points=6.0,
                        ),
                    ],
                ),
            ],
        )

        # Student who does well
        advanced_student = Submission(
            student_id="advanced",
            answers={
                "q1_basics": "yes",
                "q2_code": "function",
                "q3_essay": "This is a detailed analysis with comprehensive explanation "
                + " ".join(["word"] * 15),
            },
        )

        # Student who doesn't progress
        basic_student = Submission(
            student_id="basic",
            answers={
                "q1_basics": "no",
                "q2_code": "function",
                "q3_essay": "short",
            },
        )

        results = grade(rubric, [advanced_student, basic_student])

        # Advanced student: 5 (basics) + 10 (conditional) + weighted(0.5*10 + 0.5*6)
        # = 5 + 10 + 8.0 = 23.0
        assert results.results[0].total_points == 23.0

        # Basic student: 0 (wrong basics, so conditional doesn't apply) + weighted(0 + 0) = 0.0
        assert results.results[1].total_points == 0.0

    def test_multiple_students_batch_grading(self):
        """Test grading a large batch of students."""
        rubric = Rubric(
            name="Batch Test",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="A", max_points=10.0),
                NumericRangeRule(
                    question_id="q2", correct_value=50.0, tolerance=5.0, max_points=10.0
                ),
            ],
        )

        # Generate 50 submissions with varying correctness
        submissions = []
        for i in range(50):
            answers = {
                "q1": "A" if i % 2 == 0 else "B",
                "q2": str(50 + (i % 10) - 5),  # Values from 45 to 54
            }
            submissions.append(Submission(student_id=f"student{i}", answers=answers))

        results = grade(rubric, submissions)

        # Verify all graded
        assert len(results.results) == 50

        # Check statistical properties
        total_points = [r.total_points for r in results.results]
        avg_points = sum(total_points) / len(total_points)

        # Average should be reasonable (not all 0 or all max)
        assert 0 < avg_points < 20.0

        # Should have variety in scores
        assert len(set(total_points)) > 1


class TestMetadataHandling:
    """Test metadata preservation through workflow."""

    def test_rubric_metadata_preserved(self):
        """Test that rubric metadata is preserved."""
        rubric = Rubric(
            name="Test",
            rules=[ExactMatchRule(question_id="q1", correct_answer="A", max_points=10.0)],
            metadata={"version": "2.0", "author": "Test Author", "tags": ["test", "demo"]},
        )

        submission = Submission(student_id="s1", answers={"q1": "A"})
        _ = grade(rubric, [submission])

        # Metadata available in rubric
        assert rubric.metadata["version"] == "2.0"
        assert rubric.metadata["author"] == "Test Author"

    def test_submission_metadata_preserved(self):
        """Test that submission metadata is preserved."""
        rubric = Rubric(
            name="Test",
            rules=[ExactMatchRule(question_id="q1", correct_answer="A", max_points=10.0)],
        )

        submission = Submission(
            student_id="s1",
            answers={"q1": "A"},
            metadata={"timestamp": "2024-01-01", "attempt": 1},
        )
        _ = grade(rubric, [submission])

        # Metadata accessible from submission
        assert submission.metadata["timestamp"] == "2024-01-01"

    def test_output_metadata(self):
        """Test adding metadata to output."""
        rubric = Rubric(
            name="Test",
            rules=[ExactMatchRule(question_id="q1", correct_answer="A", max_points=10.0)],
        )

        submission = Submission(student_id="s1", answers={"q1": "A"})
        results = grade(rubric, [submission])

        # Can add metadata to output
        results.metadata["grader_version"] = "1.0"
        results.metadata["notes"] = "Test grading run"

        assert results.metadata["grader_version"] == "1.0"


class TestMultipleRules:
    """Test grading with multiple rules applied to same/different questions."""

    def test_multiple_rules_same_question(self):
        """Test multiple rules grading the same question."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="Paris", max_points=5.0),
                LengthRule(question_id="q1", min_chars=3, max_chars=10, max_points=3.0),
            ],
        )
        result = grade(rubric, [Submission(student_id="s1", answers={"q1": "Paris"})])
        assert result.results[0].total_points == 8.0  # Both rules apply

    def test_multiple_rules_different_questions(self):
        """Test rules for different questions."""
        rubric = Rubric(
            name="Test",
            rules=[
                ExactMatchRule(question_id="q1", correct_answer="Paris", max_points=10.0),
                ExactMatchRule(question_id="q2", correct_answer="London", max_points=15.0),
                ExactMatchRule(question_id="q3", correct_answer="Berlin", max_points=20.0),
            ],
        )
        result = grade(
            rubric,
            [Submission(student_id="s1", answers={"q1": "Paris", "q2": "London", "q3": "Berlin"})],
        )
        assert result.results[0].total_points == 45.0
        assert result.results[0].max_points == 45.0
        assert result.results[0].percentage == 100.0
