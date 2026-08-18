from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PaymentOut(BaseModel):
    id: int
    order_id: int
    method: str
    provider_trade_no: str
    status: str
    amount: Decimal
    pay_url: str | None
    created_at: datetime
    paid_at: datetime | None
