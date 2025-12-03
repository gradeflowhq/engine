from pydantic import BaseModel, Field


class BaseParserConfig(BaseModel):
    empty_marker: str = Field(default="N/A", description="Marker indicating an empty answer.")


class TextParserConfig(BaseParserConfig):
    trim_whitespace: bool = Field(
        default=True,
        description="Whether to trim leading and trailing whitespace from raw answers.",
    )
    normalize_case: bool = Field(
        default=False, description="Whether to normalize the case of raw answers."
    )


class MultiValuedParserConfig(TextParserConfig):
    delimiter: str = Field(
        default=",", description="Delimiter for separating multiple-valued raw answers."
    )
