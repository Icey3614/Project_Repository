"""配置与本地状态管理。

config.json —— 连接配置（API Key、Base URL、刷新间隔），与程序同目录；
state.json  —— 本地消费统计（根据余额变化推算的累计消费金额）。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_REFRESH_INTERVAL = 10
DEFAULT_ALERT_THRESHOLD = 10.0

# 常用平台 Base URL（便于下拉选择，仍支持手动输入）
PRESET_BASE_URLS: list[tuple[str, str]] = [
    ("DeepSeek 官方（OpenAI 格式）", "https://api.deepseek.com"),
    ("DeepSeek 官方（Anthropic 格式）", "https://api.deepseek.com/anthropic"),
    ("OpenAI", "https://api.openai.com"),
    ("智谱 GLM", "https://open.bigmodel.cn/api/paas/v4"),
    ("阿里通义千问 DashScope", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    ("Moonshot Kimi", "https://api.moonshot.cn/v1"),
    ("百度千帆", "https://qianfan.baidubce.com/v2"),
    ("腾讯混元", "https://api.hunyuan.cloud.tencent.com/v1"),
    ("硅基流动 SiliconFlow", "https://api.siliconflow.cn/v1"),
    ("Groq", "https://api.groq.com/openai/v1"),
]


@dataclass
class Config:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    refresh_interval: int = DEFAULT_REFRESH_INTERVAL
    alert_enabled: bool = False
    alert_threshold: float = DEFAULT_ALERT_THRESHOLD
    custom_base_urls: list[str] = field(default_factory=list)

    def validate(self) -> str | None:
        if not self.api_key.strip():
            return "API Key 不能为空"
        return None


@dataclass
class State:
    prev_total: dict[str, float] = field(default_factory=dict)
    accumulated: dict[str, float] = field(default_factory=dict)
    alert_fired: bool = False


def config_path(app_dir: Path) -> Path:
    return app_dir / CONFIG_FILE


def state_path(app_dir: Path) -> Path:
    return app_dir / STATE_FILE


def load_config(app_dir: Path) -> Config | None:
    path = config_path(app_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg = Config(
            api_key=str(data.get("api_key", "")),
            base_url=str(data.get("base_url", DEFAULT_BASE_URL)) or DEFAULT_BASE_URL,
            refresh_interval=int(data.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)),
            alert_enabled=bool(data.get("alert_enabled", False)),
            alert_threshold=float(data.get("alert_threshold", DEFAULT_ALERT_THRESHOLD)),
            custom_base_urls=[
                str(url) for url in data.get("custom_base_urls", []) if url
            ],
        )
        if cfg.refresh_interval <= 0:
            cfg.refresh_interval = DEFAULT_REFRESH_INTERVAL
        if cfg.alert_threshold <= 0:
            cfg.alert_threshold = DEFAULT_ALERT_THRESHOLD
        return cfg
    except Exception:
        return None


def save_config(app_dir: Path, cfg: Config) -> None:
    data = {
        "api_key": cfg.api_key,
        "base_url": cfg.base_url,
        "refresh_interval": cfg.refresh_interval,
        "alert_enabled": cfg.alert_enabled,
        "alert_threshold": cfg.alert_threshold,
        "custom_base_urls": cfg.custom_base_urls,
    }
    config_path(app_dir).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def clear_config(app_dir: Path) -> list[Path]:
    """删除 config.json 与 state.json，返回实际删除的文件列表。"""
    removed: list[Path] = []
    for path in (config_path(app_dir), state_path(app_dir)):
        try:
            if path.exists():
                path.unlink()
                removed.append(path)
        except OSError:
            pass
    return removed


def load_state(app_dir: Path) -> State:
    path = state_path(app_dir)
    if not path.exists():
        return State()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return State(
            prev_total={
                str(k): float(v) for k, v in (data.get("prev_total") or {}).items()
            },
            accumulated={
                str(k): float(v) for k, v in (data.get("accumulated") or {}).items()
            },
            alert_fired=bool(data.get("alert_fired", False)),
        )
    except Exception:
        return State()


def save_state(app_dir: Path, state: State) -> None:
    data = {
        "prev_total": state.prev_total,
        "accumulated": state.accumulated,
        "alert_fired": state.alert_fired,
    }
    state_path(app_dir).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_consumption(state: State, totals: dict[str, float]) -> dict[str, float]:
    """根据余额变化累计消费金额。

    每次成功刷新后调用：余额下降的部分计入累计消费；
    余额上升（充值/赠金到账）只更新基准、不产生负消费。
    """
    for currency, total in totals.items():
        prev = state.prev_total.get(currency)
        if prev is None:
            state.prev_total[currency] = total
            state.accumulated[currency] = 0.0
            continue
        delta = prev - total
        if delta > 0:
            state.accumulated[currency] = state.accumulated.get(currency, 0.0) + delta
        state.prev_total[currency] = total
    return state.accumulated


def state_to_dict(state: State) -> dict:
    return asdict(state)
