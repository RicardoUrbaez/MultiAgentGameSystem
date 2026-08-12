from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TestStatus = Literal["PASS", "FAIL", "NOT_RUN"]


class TestReport(BaseModel):
    build: TestStatus
    page_load: TestStatus
    console: TestStatus
    controls: TestStatus
    mechanics: TestStatus
    scoring: TestStatus
    win_loss: TestStatus
    reset: TestStatus
    design_compliance: TestStatus
    performance_sanity: TestStatus
    evidence: dict[str, object] = Field(default_factory=dict)
    defects: list[str] = Field(default_factory=list)
    fresh_for_iteration: int = Field(ge=0)

    @property
    def success(self) -> bool:
        return all(
            value == "PASS"
            for value in (
                self.build,
                self.page_load,
                self.console,
                self.controls,
                self.mechanics,
                self.scoring,
                self.win_loss,
                self.reset,
                self.design_compliance,
                self.performance_sanity,
            )
        )
