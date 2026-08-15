"""设置加载与校验。

默认值与 settings.json 同构；settings.json 里的字段会覆盖默认值，
未填写的字段使用默认值，方便迭代时只改需要的部分。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .generator import ALGORITHMS

SIZE_KEYS = ("small", "medium", "large", "extra_large")
SIZE_LABELS = {
    "small": "小规模",
    "medium": "中规模",
    "large": "大规模",
    "extra_large": "超大规模",
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "size_preset": "medium",
    "algorithm": "recursive_backtracker",
    "seed": None,
    "presets": {
        "small": {"width": 10, "height": 10, "cell_size": 48},
        "medium": {"width": 20, "height": 20, "cell_size": 32},
        "large": {"width": 35, "height": 35, "cell_size": 18},
        "extra_large": {"width": 60, "height": 60, "cell_size": 10},
    },
    "style": {
        "background": "#ffffff",
        "wall_color": "#1f2430",
        "wall_width": 3,
        "start_color": "#2e9e5b",
        "end_color": "#d64545",
        "trail_color": "#a6d9f7",
        "start_size_ratio": 0.7,
        "end_size_ratio": 0.7,
        "margin": 10,
    },
    "output": {"directory": "output", "filename": "maze.png"},
}


@dataclass
class Preset:
    key: str
    width: int
    height: int
    cell_size: int


@dataclass
class Style:
    background: str
    wall_color: str
    wall_width: int
    start_color: str
    end_color: str
    trail_color: str
    start_size_ratio: float
    end_size_ratio: float
    margin: int


@dataclass
class Settings:
    size_preset: str
    algorithm: str
    seed: int | None
    presets: dict[str, Preset]
    style: Style
    output_dir: Path
    output_name: str

    def get_preset(self, size: str | None = None) -> Preset:
        key = (size or self.size_preset).lower()
        if key not in self.presets:
            raise ValueError(f"未知规模: {key}，可选: {', '.join(SIZE_KEYS)}")
        return self.presets[key]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            out[key] = _deep_merge(base[key], value)
        else:
            out[key] = value
    return out


def _default_settings_path() -> Path | None:
    candidates = [Path.cwd() / "settings.json"]
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "settings.json")
    else:
        candidates.append(Path(__file__).resolve().parent.parent / "settings.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_settings(path: str | Path | None = None) -> Settings:
    """加载设置；path 为 None 时自动查找 settings.json。"""
    data = json.loads(json.dumps(DEFAULT_SETTINGS))  # 深拷贝默认值
    target = Path(path) if path is not None else _default_settings_path()
    if target is not None and target.is_file():
        with target.open("r", encoding="utf-8") as fh:
            user_data = json.load(fh)
        data = _deep_merge(data, user_data)

    preset_key = str(data["size_preset"]).lower()
    if preset_key not in SIZE_KEYS:
        raise ValueError(f"settings.json 中 size_preset 无效: {preset_key}")
    algorithm = str(data["algorithm"]).lower()
    if algorithm not in ALGORITHMS:
        raise ValueError(f"settings.json 中 algorithm 无效: {algorithm}")

    presets: dict[str, Preset] = {}
    for key in SIZE_KEYS:
        raw = data["presets"][key]
        presets[key] = Preset(
            key=key,
            width=int(raw["width"]),
            height=int(raw["height"]),
            cell_size=int(raw["cell_size"]),
        )

    seed = data["seed"]
    if seed is not None:
        seed = int(seed)

    return Settings(
        size_preset=preset_key,
        algorithm=algorithm,
        seed=seed,
        presets=presets,
        style=Style(**data["style"]),
        output_dir=Path(data["output"]["directory"]),
        output_name=str(data["output"]["filename"]),
    )
