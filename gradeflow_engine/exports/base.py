from __future__ import annotations

from pydantic import BaseModel, Field


class BaseExportConfig(BaseModel):
    """Base Pydantic model for export configuration objects.

    Specific export modules should subclass this and provide a
    discriminating `type` Literal field.
    """

    pass


class BaseCsvExportConfig(BaseExportConfig):
    """Base Pydantic model for CSV export configuration objects.

    Specific CSV export modules should subclass this and provide a
    discriminating `type` Literal field.
    """

    encoding: str = Field(default="utf-8", description="File encoding for the CSV export")
