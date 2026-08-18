import random

from app.payments.base import PaymentProvider, PaymentResult


class MockPaymentProvider(PaymentProvider):
    name = "MOCK"

    def create_payment(self, order, amount, db) -> PaymentResult:
        return PaymentResult(
            success=True,
            provider_trade_no=f"MOCK{order.order_no}{random.randint(1000, 9999)}",
            message="mock 支付成功",
        )

    def verify_callback(self, payload: dict) -> bool:
        return payload.get("sign") == "mock-sign"

    def query_order(self, payment) -> bool:
        return payment.status == "SUCCESS"

    def refund(self, payment, amount) -> None:
        return None
