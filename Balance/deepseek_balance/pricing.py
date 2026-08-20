"""峰谷定价：以北京时间（Asia/Shanghai）为准。

官方规则（2026-08-17 起生效）：
高峰时段为北京时间 9:00-12:00、14:00-18:00，其余为空闲时段；
空闲时段价格为高峰时段价格的一半。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

try:
    from zoneinfo import ZoneInfo

    BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    BEIJING_TZ = None

PEAK_WINDOWS: tuple[tuple[time, time], ...] = (
    (time(9, 0), time(12, 0)),
    (time(14, 0), time(18, 0)),
)
PEAK_MULTIPLIER = 1.0
OFFPEAK_MULTIPLIER = 0.5

# 每百万 tokens 的高峰价格（元），闲时价格 = 高峰 × 0.5
MODEL_PEAK_PRICES: dict[str, dict[str, float]] = {
    "deepseek-v4-flash": {"输入": 3.0, "输出": 9.0},
    "deepseek-v4-pro": {"输入": 9.0, "输出": 27.0},
}


@dataclass
class PricingStatus:
    is_peak: bool
    multiplier: float
    period_name: str
    discount_text: str
    window_text: str
    now_text: str


def beijing_now() -> datetime:
    if BEIJING_TZ is not None:
        return datetime.now(BEIJING_TZ)
    return datetime.now()


def pricing_status(now: datetime | None = None) -> PricingStatus:
    dt = now or beijing_now()
    t = dt.time()
    is_peak = any(start <= t < end for start, end in PEAK_WINDOWS)
    multiplier = PEAK_MULTIPLIER if is_peak else OFFPEAK_MULTIPLIER
    return PricingStatus(
        is_peak=is_peak,
        multiplier=multiplier,
        period_name="高峰" if is_peak else "闲时",
        discount_text="全价" if is_peak else "5 折",
        window_text="高峰 09:00–12:00 / 14:00–18:00",
        now_text=f"北京时间 {dt.strftime('%H:%M:%S')}",
    )


def current_prices(status: PricingStatus) -> dict[str, dict[str, float]]:
    return {
        model: {
            kind: round(price * status.multiplier, 2)
            for kind, price in items.items()
        }
        for model, items in MODEL_PEAK_PRICES.items()
    }
