from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentResult:
    success: bool
    provider_trade_no: str
    pay_url: str | None = None
    message: str = ""


class PaymentProvider(ABC):
    """支付抽象层：新增渠道只需实现一个子类，并在 factory 中注册。"""

    name: str = "base"

    @abstractmethod
    def create_payment(self, order, amount: Decimal, db) -> PaymentResult:
        """发起支付；mock 立即返回成功，真实网关返回跳转参数。"""

    @abstractmethod
    def verify_callback(self, payload: dict) -> bool:
        """校验异步回调签名。"""

    @abstractmethod
    def query_order(self, payment) -> bool:
        """主动查询订单是否已支付（本地开发无公网回调时的兜底）。"""

    @abstractmethod
    def refund(self, payment, amount: Decimal) -> None:
        """退款（mock 为空操作，沙箱接入后调用支付宝退款接口）。"""
