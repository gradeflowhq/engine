from pydantic import BaseModel, Field


class Result(BaseModel):
    output: bool | int | float = Field(description="Output generated from evaluating the answer")
    passed: bool = Field(description="Whether the answer passed the rule check")
    feedback: str = Field(description="Feedback or comments")
    rule: str = Field(description="ID of the rule that was applied")


class QuestionResult(Result):
    question_id: str = Field(description="Question identifier")
    points: float = Field(description="Points awarded for this question")
    max_points: float = Field(description="Maximum points possible")
