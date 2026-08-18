from app.core.config import settings
from app.payments.alipay import AlipayPaymentProvider
from app.payments.base import PaymentProvider
from app.payments.mock import MockPaymentProvider


def get_payment_provider() -> PaymentProvider:
    provider = settings.PAYMENT_PROVIDER.upper()
    if provider == "MOCK":
        return MockPaymentProvider()
    if provider == "ALIPAY":
        return AlipayPaymentProvider()
    raise RuntimeError(f"未知的支付渠道: {settings.PAYMENT_PROVIDER}")
