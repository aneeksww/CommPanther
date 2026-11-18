from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Category = Literal[
    "urgent",
    "important",
    "later",
    "no_action",
]

DeadlineStatus = Literal[
    "confirmed",
    "unclear",
    "absent",
]


class AnalysisResult(BaseModel):
    category: Category
    rationale: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    key_details: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    deadline: datetime | None = None
    deadline_status: DeadlineStatus

    @model_validator(mode="before")
    @classmethod
    def normalize_values(cls, values):
        deadline = values.get("deadline")

        if deadline in ("", "null", "None", None):
            values["deadline"] = None

        if values.get("deadline_status") == "absent":
            values["deadline"] = None

        return values