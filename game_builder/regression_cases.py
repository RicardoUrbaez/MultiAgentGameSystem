from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegressionCase:
    name: str
    genre: str
    prompt: str


REGRESSION_CASES = (
    RegressionCase("pong", "paddle game", "Build a polished two-player Pong game with scoring, win state, reset, and TestBridge hooks."),
    RegressionCase("breakout", "breakout", "Build a polished Breakout game with a paddle, destructible bricks, lives, progression, reset, and TestBridge hooks."),
    RegressionCase("asteroid_survival", "asteroid survival", "Build an asteroid survival game with ship movement, hazards, score, lives, reset, and TestBridge hooks."),
    RegressionCase("top_down_shooter", "top-down shooter", "Build a compact top-down shooter with movement, shooting, enemies, score, loss state, reset, and TestBridge hooks."),
    RegressionCase("maze", "maze game", "Build a maze game with player movement, objective collection, win/loss states, reset, and TestBridge hooks."),
)


def get_regression_case(name: str) -> RegressionCase:
    for case in REGRESSION_CASES:
        if case.name == name:
            return case
    raise KeyError(f"Unknown regression case: {name}")
