"""游戏设置：定义、加载与保存（config.json）。"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# 地图预设：key -> (列数, 行数)
MAP_PRESETS: dict[str, tuple[int, int]] = {
    "small": (15, 15),
    "medium": (20, 20),
    "large": (30, 20),
}
MAP_NAMES = {"small": "小地图", "medium": "中地图", "large": "大地图"}

SPEED_MIN = 3
SPEED_MAX = 20
SPEED_DEFAULT = 8

DUEL_TIME_OPTIONS = (60, 90, 120, 180)


@dataclass
class Settings:
    mode: str = "single"        # single 单人 / duel 双人竞技
    duel_timer: bool = False    # 双人模式倒计时开关
    duel_time: int = 90         # 双人倒计时时长（秒）
    map_key: str = "medium"
    speed: int = SPEED_DEFAULT
    wrap: bool = False
    speed_up: bool = True

    @property
    def grid_size(self) -> tuple[int, int]:
        return MAP_PRESETS.get(self.map_key, MAP_PRESETS["medium"])

    def adjust(self, field: str, delta: int) -> None:
        if field == "mode":
            self.mode = "duel" if self.mode == "single" else "single"
        elif field == "duel_timer":
            self.duel_timer = not self.duel_timer
        elif field == "duel_time":
            options = DUEL_TIME_OPTIONS
            index = options.index(self.duel_time) if self.duel_time in options else 0
            self.duel_time = options[(index + delta) % len(options)]
        elif field == "map":
            keys = list(MAP_PRESETS)
            index = keys.index(self.map_key)
            self.map_key = keys[(index + delta) % len(keys)]
        elif field == "speed":
            self.speed = max(SPEED_MIN, min(SPEED_MAX, self.speed + delta))
        elif field in ("wrap", "speed_up"):
            setattr(self, field, not getattr(self, field))

    def config_path(self) -> Path:
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).resolve().parent
        else:
            base = Path(__file__).resolve().parent
        return base / "config.json"

    def save(self) -> None:
        try:
            self.config_path().write_text(
                json.dumps(asdict(self), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    @classmethod
    def load(cls) -> "Settings":
        settings = cls()
        try:
            data = json.loads(settings.config_path().read_text(encoding="utf-8"))
            settings.mode = data.get("mode", settings.mode)
            settings.duel_timer = bool(data.get("duel_timer", settings.duel_timer))
            settings.duel_time = int(data.get("duel_time", settings.duel_time))
            settings.map_key = data.get("map_key", settings.map_key)
            settings.speed = int(data.get("speed", settings.speed))
            settings.wrap = bool(data.get("wrap", settings.wrap))
            settings.speed_up = bool(data.get("speed_up", settings.speed_up))
        except (OSError, ValueError, TypeError):
            pass
        settings.speed = max(SPEED_MIN, min(SPEED_MAX, settings.speed))
        if settings.map_key not in MAP_PRESETS:
            settings.map_key = "medium"
        if settings.mode not in ("single", "duel"):
            settings.mode = "single"
        if settings.duel_time not in DUEL_TIME_OPTIONS:
            settings.duel_time = DUEL_TIME_OPTIONS[0]
        return settings
