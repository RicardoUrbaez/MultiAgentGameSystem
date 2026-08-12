from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from .workspace_tools import PHASER_TEMPLATE_DIR


class AssetEntry(BaseModel):
    key: str
    type: str
    path: str
    tags: list[str]
    animation: dict[str, object] | None = None


def get_asset_manifest_path() -> Path:
    return PHASER_TEMPLATE_DIR / "public" / "assets" / "library" / "asset-manifest.json"


def load_asset_manifest() -> dict[str, AssetEntry]:
    data = json.loads(get_asset_manifest_path().read_text(encoding="utf-8"))
    entries = data.get("assets", [])
    return {entry["key"]: AssetEntry.model_validate(entry) for entry in entries}


def validate_asset_keys(asset_keys: list[str]) -> list[str]:
    available = load_asset_manifest()
    invalid = sorted(set(asset_keys) - set(available))
    if invalid:
        raise ValueError(f"Unknown approved asset keys: {', '.join(invalid)}")
    return asset_keys
