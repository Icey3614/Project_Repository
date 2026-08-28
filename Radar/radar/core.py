"""UI-independent radar sweep logic.

Conventions
-----------
* Angles are radians, measured clockwise from 12 o'clock (top of the
  display), normalized to ``[0, 2π)``.
* Radius is normalized: 0 = screen center, 1 = radar disc edge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

TAU = 2.0 * math.pi


def clockwise_angle(dx: float, dy: float) -> float:
    """Map a screen vector (x right, y down) to a clockwise-from-noon angle."""
    return math.atan2(dx, -dy) % TAU


def normalize(angle: float) -> float:
    """Wrap an angle into ``[0, 2π)``."""
    return angle % TAU


def arc_covers(prev: float, cur: float, target: float, eps: float = 1e-12) -> bool:
    """Whether the clockwise arc swept from ``prev`` to ``cur`` includes ``target``."""
    delta = (cur - prev) % TAU
    rel = (target - prev) % TAU
    # The sweep is leaving the target angle (target == prev): only a full
    # revolution would re-cover it. This avoids a refresh when the sweep ends
    # exactly on the cursor angle and then moves away.
    if rel <= eps and delta < TAU - eps:
        return False
    return rel <= delta + eps


@dataclass
class Echo:
    """A radar echo: the cursor position at the moment it was swept over."""

    angle: float
    radius: float
    age: float = 0.0


class RadarModel:
    """Advances the sweep and manages the fading echoes of the cursor."""

    def __init__(self, rpm: float = 12.0, echo_lifetime: float = 3.0, sweep_tolerance: float = 0.06):
        self.rpm = rpm
        self.echo_lifetime = echo_lifetime
        self.sweep_tolerance = sweep_tolerance
        self.sweep_angle = 0.0
        self._prev_sweep = 0.0
        self.cursor_angle = 0.0
        self.cursor_radius = 0.0
        self.has_cursor = False
        self.echoes: list[Echo] = []

    def set_cursor(self, angle: float, radius: float) -> None:
        self.cursor_angle = angle
        self.cursor_radius = radius
        self.has_cursor = True

    def step(self, dt: float) -> tuple[float, float]:
        """Advance the sweep by ``dt`` seconds; returns ``(prev, cur)`` angles."""
        self.sweep_angle = normalize(self.sweep_angle + TAU * self.rpm / 60.0 * dt)
        prev, cur = self._prev_sweep, self.sweep_angle
        self._prev_sweep = cur

        # Age existing echoes and drop the expired ones.
        survivors: list[Echo] = []
        for echo in self.echoes:
            echo.age += dt
            if echo.age < self.echo_lifetime:
                survivors.append(echo)
        self.echoes = survivors

        # Light the echo when the sweep line passes over the cursor, or when a
        # moving/stationary cursor coincides with the sweep line right now.
        if self.has_cursor and (
            arc_covers(prev, cur, self.cursor_angle) or self._cursor_on_sweep(cur)
        ):
            new_echo = Echo(self.cursor_angle, self.cursor_radius)
            # Refresh the marker in place when the cursor has barely moved,
            # so a stationary cursor shows a single dot (no stacking).
            self.echoes = [e for e in self.echoes if not self._same_position(e, new_echo)]
            self.echoes.insert(0, new_echo)
            del self.echoes[30:]  # keep a bounded trail

        return prev, cur

    def _cursor_on_sweep(self, cur: float) -> bool:
        """Whether the cursor currently lies on the sweep line (small tolerance)."""
        d = abs((self.cursor_angle - cur + math.pi) % TAU - math.pi)
        return d <= self.sweep_tolerance

    def brightness(self, echo: Echo) -> float:
        """Steady brightness: the marker stays fully lit until it expires."""
        return 1.0 if echo.age < self.echo_lifetime else 0.0

    @staticmethod
    def _same_position(a: Echo, b: Echo) -> bool:
        d_angle = abs((a.angle - b.angle + math.pi) % TAU - math.pi)
        return d_angle < 0.03 and abs(a.radius - b.radius) < 0.04
