from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GameManifest(BaseModel):
    engine: Literal["PHASER_2D"] = "PHASER_2D"
    genre: str
    title: str
    player_count: int = Field(ge=1)
    camera: Literal["STATIC", "FOLLOW", "ROOM", "SCROLLING", "TOP_DOWN"]
    physics: Literal["ARCADE", "NONE"]
    scenes: list[str]
    mechanics: list[str]
    required_assets: list[str]
    acceptance_tests: list[str]
    has_menu: bool
    has_audio: bool
    has_particles: bool
    has_progression: bool
