"""支付宝沙箱支付渠道（RSA2 签名，无需官方 SDK）。

依赖 cryptography 完成 PKCS1v15 + SHA256 签名/验签。
"""

import base64
import json
import time
from datetime import datetime
from urllib.parse import urlencode

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings
from app.payments.base import PaymentProvider, PaymentResult


def _private_key():
    pem = (
        "-----BEGIN PRIVATE KEY-----\n"
        f"{settings.ALIPAY_PRIVATE_KEY}\n"
        "-----END PRIVATE KEY-----"
    )
    return serialization.load_pem_private_key(pem.encode("utf-8"), password=None)


def _public_key():
    pem = (
        "-----BEGIN PUBLIC KEY-----\n"
        f"{settings.ALIPAY_PUBLIC_KEY}\n"
        "-----END PUBLIC KEY-----"
    )
    return serialization.load_pem_public_key(pem.encode("utf-8"))


def _sign_content(params: dict) -> str:
    """按支付宝规则：仅剔除 sign 与空值，保留 sign_type，按 key 升序拼接。"""
    items = []
    for key in sorted(params):
        value = params[key]
        if value is None or value == "" or key == "sign":
            continue
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        items.append(f"{key}={value}")
    return "&".join(items)


def _sign(params: dict) -> str:
    content = _sign_content(params)
    signature = _private_key().sign(
        content.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")


def _verify(sign: str, content: str) -> bool:
    return _verify_bytes(sign, content.encode("utf-8"))


def _verify_bytes(sign: str, content: bytes) -> bool:
    try:
        _public_key().verify(
            base64.b64decode(sign),
            content,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def _verify_response(data: dict, charset: str) -> bool:
    """校验开放平台 JSON 响应签名。

    支付宝对响应业务字段（alipay_*_response）的 JSON 序列化值签名，
    且按响应声明的字符集（GBK）计算，因此需要按原编码重新编码后验签。
    """
    response_key = next((k for k in data if k not in ("sign", "sign_type")), None)
    if response_key is None:
        return False
    enc = "gb18030" if charset in ("gbk", "gb2312", "gb18030") else "utf-8"
    content = json.dumps(
        data[response_key], ensure_ascii=False, separators=(",", ":")
    ).encode(enc)
    return _verify_bytes(data.get("sign", ""), content)


def _gateway_request(params: dict) -> dict:
    """调用支付宝开放平台接口并验证响应签名。"""
    params.setdefault("app_id", settings.ALIPAY_APP_ID)
    params.setdefault("format", "JSON")
    params.setdefault("charset", "utf-8")
    params.setdefault("sign_type", "RSA2")
    params.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    params.setdefault("version", "1.0")
    params["sign"] = _sign(params)
    resp = httpx.post(settings.ALIPAY_GATEWAY, data=params, timeout=10)
    resp.raise_for_status()
    charset = (resp.charset_encoding or "utf-8").lower()
    enc = "gb18030" if charset in ("gbk", "gb2312", "gb18030") else "utf-8"
    try:
        data = json.loads(resp.content.decode(enc, errors="replace"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        data = json.loads(resp.content.decode("utf-8", errors="replace"))
    if not _verify_response(data, charset):
        raise RuntimeError("支付宝响应验签失败")
    return data


class AlipayPaymentProvider(PaymentProvider):
    name = "ALIPAY"

    def create_payment(self, order, amount, db) -> PaymentResult:
        if not (settings.ALIPAY_APP_ID and settings.ALIPAY_PRIVATE_KEY and settings.ALIPAY_PUBLIC_KEY):
            raise RuntimeError("支付宝沙箱配置不完整，请检查 .env")
        params = {
            "app_id": settings.ALIPAY_APP_ID,
            "method": "alipay.trade.page.pay",
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": settings.ALIPAY_NOTIFY_URL,
            "return_url": settings.ALIPAY_RETURN_URL,
            "biz_content": json.dumps(
                {
                    "out_trade_no": order.order_no,
                    "total_amount": f"{amount:.2f}",
                    "subject": f"电影票订单 {order.order_no}",
                    "product_code": "FAST_INSTANT_TRADE_PAY",
                },
                ensure_ascii=False,
            ),
        }
        params["sign"] = _sign(params)
        pay_url = f"{settings.ALIPAY_GATEWAY}?{urlencode(params)}"
        return PaymentResult(
            success=False,
            provider_trade_no=order.order_no,
            pay_url=pay_url,
            message="请前往支付宝完成支付",
        )

    def verify_callback(self, payload: dict) -> bool:
        return _verify(payload.get("sign", ""), _sign_content(payload))

    def query_order(self, payment) -> bool:
        params = {
            "app_id": settings.ALIPAY_APP_ID,
            "method": "alipay.trade.query",
            "biz_content": json.dumps(
                {"out_trade_no": payment.provider_trade_no}, ensure_ascii=False
            ),
        }
        data = _gateway_request(params)
        return data.get("code") == "10000" and data.get("trade_status") in (
            "TRADE_SUCCESS",
            "TRADE_FINISHED",
        )

    def refund(self, payment, amount) -> None:
        params = {
            "app_id": settings.ALIPAY_APP_ID,
            "method": "alipay.trade.refund",
            "biz_content": json.dumps(
                {
                    "out_trade_no": payment.provider_trade_no,
                    "refund_amount": f"{amount:.2f}",
                    "out_request_no": f"RF{payment.order_id}{int(time.time())}",
                },
                ensure_ascii=False,
            ),
        }
        data = _gateway_request(params)
        if data.get("code") != "10000":
            raise RuntimeError(f"支付宝退款失败: {data.get('sub_msg')}")
