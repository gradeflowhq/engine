"""
Example script demonstrating how to use the gradeflow-engine library.

This script shows various ways to use the engine programmatically.
"""

from gradeflow_engine import (
    ConditionalRule,
    ExactMatchRule,
    ProgrammableRule,
    Rubric,
    Submission,
    grade,
    grade_from_files,
    save_results_yaml,
)
from gradeflow_engine.io import export_canvas_csv, save_results_csv


def example_1_basic_usage():
    """Example 1: Basic usage with programmatically created rubric."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    # Create a simple rubric with conditional rule
    rubric = Rubric(
        name="Demo Exam",
        rules=[
            ConditionalRule(
                type="CONDITIONAL",
                if_rules={
                    "Q1": ExactMatchRule(
                        question_id="Q1",
                        correct_answer="A",
                        max_points=0,
                        case_sensitive=False,
                    )
                },
                then_rules={
                    "Q2": ExactMatchRule(
                        question_id="Q2",
                        correct_answer="B",
                        max_points=10.0,
                        case_sensitive=False,
                    )
                },
                if_aggregation="AND",
            )
        ],
    )

    # Create submissions
    submissions = [
        Submission(student_id="student1", answers={"Q1": "A", "Q2": "B"}),
        Submission(student_id="student2", answers={"Q1": "A", "Q2": "C"}),
        Submission(student_id="student3", answers={"Q1": "C", "Q2": "B"}),
    ]

    # Grade
    results = grade(rubric, submissions)

    # Print results
    for result in results.results:
        print(
            f"{result.student_id}: {result.total_points}/{result.max_points} "
            f"({result.percentage:.1f}%)"
        )

    print()


def example_2_load_from_files():
    """Example 2: Load rubric and submissions from files."""
    print("=" * 60)
    print("Example 2: Load from Files (YAML)")
    print("=" * 60)

    # Grade from files - supports both YAML and JSON
    results = grade_from_files(
        rubric_path="examples/example_rubric.yaml",
        submissions_csv_path="examples/example_submissions.csv",
    )

    # Print summary
    print(f"Students graded: {len(results.results)}")
    print()

    # Print detailed results
    for result in results.results:
        print(f"\n{result.student_id}:")
        print(f"  Total: {result.total_points}/{result.max_points} ({result.percentage:.1f}%)")

        for detail in result.grade_details:
            status = "✓" if detail.is_correct else "✗"
            print(
                f"  {status} {detail.question_id}: {detail.points_awarded}/{detail.max_points} pts"
            )
            if detail.feedback:
                print(f"    Feedback: {detail.feedback}")

    print()

    return results


def example_3_export_results(results):
    """Example 3: Export results to various formats."""
    print("=" * 60)
    print("Example 3: Export Results")
    print("=" * 60)

    # Export to YAML
    save_results_yaml(results, "examples/results.yaml")
    print("✓ Saved results.yaml")

    # Export to CSV (summary)
    save_results_csv(results, "examples/results_summary.csv", include_details=False)
    print("✓ Saved results_summary.csv")

    # Export to CSV (detailed)
    save_results_csv(results, "examples/results_detailed.csv", include_details=True)
    print("✓ Saved results_detailed.csv")

    # Export for Canvas LMS
    export_canvas_csv(results, "examples/canvas_export.csv")
    print("✓ Saved canvas_export.csv")

    print()


def example_4_json_schema():
    """Example 4: Generate JSON Schema for frontend - NOT YET IMPLEMENTED."""
    print("=" * 60)
    print("Example 4: Generate JSON Schema (Skipped - Not Implemented)")
    print("=" * 60)

    print("JSON Schema generation is not yet implemented.")
    print("This feature will be added in a future version.")
    print()


def example_5_programmable_grading():
    """Example 5: Programmable grading with custom logic."""
    print("=" * 60)
    print("Example 5: Programmable Grading")
    print("=" * 60)

    # Create rubric with programmable rule
    rubric = Rubric(
        name="Programmable Grading Demo",
        rules=[
            ProgrammableRule(
                type="PROGRAMMABLE",
                question_id="essay",
                script="""
# Check for keywords
keywords = ['python', 'programming', 'code']
found = sum(1 for k in keywords if k in answer.lower())

points_awarded = found * 3.0  # 3 points per keyword
feedback = f'Found {found}/3 keywords'
""",
                max_points=9.0,
            )
        ],
    )

    # Test submissions
    submissions = [
        Submission(
            student_id="s1", answers={"essay": "Python is a programming language for code."}
        ),
        Submission(student_id="s2", answers={"essay": "Programming in Python is fun."}),
        Submission(student_id="s3", answers={"essay": "I like writing code."}),
    ]

    # Grade
    results = grade(rubric, submissions)

    # Show results
    for result in results.results:
        detail = result.grade_details[0]
        print(f"{result.student_id}: {detail.points_awarded}/9.0 pts - {detail.feedback}")

    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("REGRADER-ENGINE USAGE EXAMPLES")
    print("=" * 60 + "\n")

    # Run examples
    example_1_basic_usage()
    results = example_2_load_from_files()
    example_3_export_results(results)
    example_4_json_schema()
    example_5_programmable_grading()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
