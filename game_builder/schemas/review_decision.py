from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewDecision(BaseModel):
    route: Literal["APPROVE", "REVISE_DEVELOPER", "REPLAN", "HUMAN_REVIEW"]
    score: int = Field(ge=0, le=100)
    reasoning: str
    defects: list[str] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)
