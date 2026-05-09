from pydantic import BaseModel, Field, field_validator


class Result(BaseModel):
    output: bool | int | float = Field(description="Output generated from evaluating the answer")
    passed: bool = Field(description="Whether the answer passed the rule check")
    feedback: str = Field(description="Feedback or comments")
    rule: str = Field(description="Display name of the rule that produced the result")
    graded: bool = Field(default=True, description="Whether the result has been graded")


class QuestionResult(Result):
    points: float = Field(description="Points awarded for this question")
    max_points: float = Field(description="Maximum points possible")

    @field_validator("points", "max_points")
    @classmethod
    def round_to_two_decimals(cls, v: float) -> float:
        return round(v, 2)
