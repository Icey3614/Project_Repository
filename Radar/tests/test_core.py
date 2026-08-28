"""Lightweight tests for the radar core logic (no GUI needed)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.core import RadarModel, arc_covers, clockwise_angle, normalize  # noqa: E402

TAU = 2.0 * math.pi


def approx(a: float, b: float, tol: float = 1e-9) -> None:
    assert abs(a - b) < tol, f"{a} != {b}"


def test_clockwise_angle() -> None:
    approx(clockwise_angle(0, -1), 0.0)          # up
    approx(clockwise_angle(1, 0), TAU / 4)       # right
    approx(clockwise_angle(0, 1), TAU / 2)       # down
    approx(clockwise_angle(-1, 0), 3 * TAU / 4)  # left


def test_normalize() -> None:
    approx(normalize(TAU), 0.0)
    approx(normalize(TAU + 1.0), 1.0)
    approx(normalize(-0.5), TAU - 0.5)


def test_arc_covers_basic() -> None:
    assert arc_covers(0.0, TAU / 4, TAU / 8)
    assert not arc_covers(0.0, TAU / 4, TAU / 2)
    assert not arc_covers(0.0, TAU / 4, 3 * TAU / 4)


def test_arc_covers_wrap() -> None:
    prev = 3.0 * TAU / 4  # 9 o'clock
    cur = TAU / 8         # just past 12 o'clock
    assert arc_covers(prev, cur, 7 * TAU / 8)   # between 9 and 12 o'clock, clockwise
    assert not arc_covers(prev, cur, TAU / 4)   # 3 o'clock, not yet swept


def test_model_echo_only_after_sweep() -> None:
    model = RadarModel(rpm=60.0)  # one revolution per second
    model.set_cursor(TAU / 4, 0.5)
    assert model.echoes == []
    model.step(0.25)  # sweep noon -> 3 o'clock, crosses the cursor
    assert len(model.echoes) == 1
    echo = model.echoes[0]
    approx(echo.angle, TAU / 4)
    approx(echo.radius, 0.5)
    approx(echo.age, 0.0)
    approx(model.brightness(echo), 1.0)
    model.step(0.1)
    assert 0.0 < model.echoes[0].age < 0.11
    assert model.brightness(model.echoes[0]) == 1.0  # steady, no blinking


def test_model_no_duplicate_echo_on_same_sweep() -> None:
    model = RadarModel(rpm=60.0, sweep_tolerance=0.01)
    model.set_cursor(0.1, 0.5)
    model.step(0.01)  # sweep 0 -> 3.6 deg, cursor at 5.7 deg: not swept yet
    assert len(model.echoes) == 0
    model.step(0.01)  # sweep 3.6 -> 7.2 deg: crossed
    assert len(model.echoes) == 1
    model.step(0.01)  # sweep 7.2 -> 10.8 deg: no second crossing
    assert len(model.echoes) == 1


def test_model_echo_expires() -> None:
    model = RadarModel(rpm=60.0, echo_lifetime=0.5)
    model.set_cursor(TAU / 4, 0.5)
    model.step(0.25)  # crossing, echo age 0
    assert len(model.echoes) == 1
    model.step(0.6)  # ages past the lifetime
    assert model.echoes == []


def test_model_steady_and_default_lifetime() -> None:
    model = RadarModel(rpm=60.0)  # echo_lifetime defaults to 3.0 s, steady (no blink)
    assert model.echo_lifetime == 3.0
    assert model.sweep_tolerance == 0.06
    model.set_cursor(TAU / 8, 0.5)
    model.step(0.25)  # sweep 0 -> 90 deg crosses 45 deg; echo age 0
    echo = model.echoes[0]
    assert model.brightness(echo) == 1.0
    echo.age = 2.9  # still fully lit just before the 3 s mark
    assert model.brightness(echo) == 1.0
    echo.age = 3.0  # expires after 3 seconds
    assert model.brightness(echo) == 0.0


def test_model_moving_cursor_coincides_with_sweep() -> None:
    model = RadarModel(rpm=12.0)  # sweep_tolerance defaults to 0.06 rad
    # The cursor is slightly ahead of the sweep, e.g. moving clockwise faster
    # than the line: the arc-crossing check alone would never fire, but the
    # coincidence rule must light the echo immediately.
    model.set_cursor(0.03, 0.5)
    prev, cur = model.step(1 / 60)  # sweep advances ~0.021 rad from 0
    assert not arc_covers(prev, cur, 0.03)
    assert len(model.echoes) == 1
    assert model.echoes[0].age == 0.0


def test_model_refresh_replaces_same_position() -> None:
    model = RadarModel(rpm=60.0)
    model.set_cursor(TAU / 8, 0.5)
    model.step(0.25)  # crossing 1 (0 -> 90 deg covers 45 deg)
    assert len(model.echoes) == 1
    model.step(0.5)   # 90 -> 270 deg, no crossing
    assert len(model.echoes) == 1
    model.step(0.25)  # 270 -> 0 deg, no crossing
    assert len(model.echoes) == 1
    model.step(0.25)  # 0 -> 90 deg crosses 45 deg again: replace, not stack
    assert len(model.echoes) == 1
    assert model.echoes[0].age == 0.0


def main() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    main()
