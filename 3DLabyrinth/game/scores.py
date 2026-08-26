"""本地排行榜：按难度保存最佳成绩（JSON）。"""

from __future__ import annotations

import json
import os
import time


class Scores:
    MAX_ENTRIES = 5

    def __init__(self, path: str | None = None):
        if path is None:
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
            path = os.path.join(base, "3DLabyrinth", "scores.json")
        self.path = path
        self.data: dict[str, list[dict]] = {}
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = {}
        for key in self.data:
            entries = self.data[key]
            self.data[key] = entries[: self.MAX_ENTRIES] if isinstance(entries, list) else []

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, difficulty: str, elapsed: float, steps: int, seed: int) -> int:
        """记录一次成绩，返回排名（0 起）；未进榜返回 -1。"""
        entries = self.data.setdefault(difficulty, [])
        entry = {
            "time": round(elapsed, 2),
            "steps": steps,
            "seed": seed,
            "date": time.strftime("%Y-%m-%d %H:%M"),
        }
        entries.append(entry)
        entries.sort(key=lambda e: e["time"])
        del entries[self.MAX_ENTRIES:]
        self.data[difficulty] = entries
        self.save()
        try:
            return entries.index(entry)
        except ValueError:
            return -1

    def best(self, difficulty: str) -> dict | None:
        entries = self.data.get(difficulty) or []
        return entries[0] if entries else None

    def top(self, difficulty: str, n: int = 3) -> list[dict]:
        return (self.data.get(difficulty) or [])[:n]
