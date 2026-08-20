"""DeepSeek API 客户端。"""

from __future__ import annotations

from dataclasses import dataclass, field

import requests


class ApiError(Exception):
    """API 请求失败，message 可直接展示给用户。"""


@dataclass
class BalanceEntry:
    currency: str
    total_balance: float
    granted_balance: float
    topped_up_balance: float


@dataclass
class BalanceResult:
    is_available: bool
    balances: list[BalanceEntry] = field(default_factory=list)

    def totals(self) -> dict[str, float]:
        return {e.currency: e.total_balance for e in self.balances}


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        timeout: float = 10.0,
    ):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def fetch_balance(self) -> BalanceResult:
        if not self.api_key:
            raise ApiError("API Key 未配置，请在设置中填写")

        url = f"{self.base_url}/user/balance"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        try:
            resp = self._session.get(url, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ApiError(f"网络请求失败：{exc}") from exc

        if resp.status_code == 401:
            raise ApiError("API Key 无效或未授权（401）")
        if resp.status_code == 403:
            raise ApiError("没有访问权限（403）")
        if resp.status_code == 402:
            raise ApiError("余额不足（402）")
        if resp.status_code == 429:
            raise ApiError("请求过于频繁（429），请稍后再试")
        if resp.status_code != 200:
            raise ApiError(f"HTTP {resp.status_code}：{resp.text[:200]}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise ApiError("返回内容不是有效的 JSON") from exc

        try:
            entries = [
                BalanceEntry(
                    currency=str(item.get("currency", "CNY")),
                    total_balance=float(item.get("total_balance", 0) or 0),
                    granted_balance=float(item.get("granted_balance", 0) or 0),
                    topped_up_balance=float(item.get("topped_up_balance", 0) or 0),
                )
                for item in data.get("balance_infos", [])
            ]
            return BalanceResult(
                is_available=bool(data.get("is_available", False)),
                balances=entries,
            )
        except (TypeError, ValueError) as exc:
            raise ApiError(f"解析余额数据失败：{exc}") from exc
