"""冒烟测试：里程碑 1 + 2。

通过 TestClient 走 HTTP 接口，并对超时释放/截止释放直接调用服务层函数验证。
测试数据在结束时清理，不影响种子数据。
"""

import random
import string
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["PAYMENT_PROVIDER"] = "mock"  # 冒烟测试固定使用 mock 渠道，不依赖 .env

from app.main import app  # noqa: E402
from app.core.config import settings as app_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Movie,
    MovieSession,
    Order,
    Payment,
    RefundRequest,
    SessionSeat,
    Ticket,
    TransferRecord,
    User,
    Venue,
)
from app.services.order_service import release_at_cutoff, release_expired_locks  # noqa: E402
from app.payments import alipay as alipay_mod  # noqa: E402


def rand_suffix(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def main() -> None:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        checks.append((name, cond, detail))
        print(("PASS" if cond else "FAIL"), name, detail)

    suffix = rand_suffix()
    test_movie_id: int | None = None
    test_venue_id: int | None = None
    session_ids: list[int] = []
    user_ids: list[int] = []
    order_ids: list[int] = []

    with TestClient(app) as client:
        try:
            # ---------- 基础 ----------
            r = client.get("/health")
            check("health", r.status_code == 200 and r.json()["status"] == "ok")

            alipay_keys = bool(
                app_settings.ALIPAY_APP_ID
                and app_settings.ALIPAY_PRIVATE_KEY
                and app_settings.ALIPAY_PUBLIC_KEY
            )
            if alipay_keys:
                alipay_params = {"out_trade_no": "SMOKE1", "total_amount": "45.00", "sign_type": "RSA2"}
                check(
                    "alipay keys load",
                    alipay_mod._private_key() is not None and alipay_mod._public_key() is not None,
                )
                check(
                    "alipay sign content includes sign_type",
                    "sign_type=RSA2" in alipay_mod._sign_content(alipay_params),
                )
                alipay_sig = alipay_mod._sign(alipay_params)
                check("alipay rsa2 signature generated", len(alipay_sig) > 100)
                check(
                    "alipay bad sign rejected",
                    not alipay_mod._verify("bad-sign", alipay_mod._sign_content(alipay_params)),
                )
            else:
                check("alipay keys load", True, "skip：未配置支付宝沙箱")

            def register_user(tag: str) -> tuple[int, str]:
                username = f"{tag}_{rand_suffix()}"
                r = client.post(
                    "/api/v1/auth/register",
                    json={"username": username, "password": "pass123456", "nickname": tag},
                )
                assert r.status_code == 201, r.text
                uid = r.json()["data"]["id"]
                user_ids.append(uid)
                r = client.post(
                    "/api/v1/auth/login",
                    json={"username": username, "password": "pass123456"},
                )
                return uid, r.json()["data"]["access_token"]

            def admin_token() -> str:
                r = client.post(
                    "/api/v1/auth/login",
                    json={"username": "admin", "password": "Admin@123456"},
                )
                return r.json()["data"]["access_token"]

            admin_headers = {"Authorization": f"Bearer {admin_token()}"}
            check("admin login", True)

            # ---------- 电影 / 场馆 ----------
            r = client.post(
                "/api/v1/movies",
                headers=admin_headers,
                json={"title": f"冒烟电影_{suffix}", "duration_min": 90},
            )
            check("create movie", r.status_code == 201 and r.json()["code"] == 0)
            test_movie_id = r.json()["data"]["id"]

            r = client.post(
                "/api/v1/venues",
                headers=admin_headers,
                json={"name": f"冒烟厅_{suffix}", "rows": 3, "cols": 4},
            )
            check("create venue", r.status_code == 201 and r.json()["data"]["capacity"] == 12)
            test_venue_id = r.json()["data"]["id"]

            # ---------- 场次：创建 / 冲突 / 座位图 ----------
            start = datetime.now() + timedelta(days=1)
            start = start.replace(hour=10, minute=0, second=0, microsecond=0)
            payload = {
                "movie_id": test_movie_id,
                "venue_id": test_venue_id,
                "start_at": start.isoformat(),
                "sale_open_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "sale_close_at": (start - timedelta(minutes=30)).isoformat(),
                "base_price": "45.00",
            }
            r = client.post("/api/v1/sessions", headers=admin_headers, json=payload)
            check("create session", r.status_code == 201 and r.json()["code"] == 0, r.text)
            session_id = r.json()["data"]["id"]
            session_ids.append(session_id)
            check(
                "session selling with 12 seats",
                r.json()["data"]["status"] == "SELLING" and r.json()["data"]["remaining"] == 12,
            )

            conflict_payload = dict(payload)
            conflict_payload["start_at"] = (start + timedelta(hours=1)).isoformat()
            r = client.post("/api/v1/sessions", headers=admin_headers, json=conflict_payload)
            check("conflict session rejected", r.status_code == 409, r.text)

            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            seats = r.json()["data"]
            check("seat map 12 seats", r.status_code == 200 and len(seats) == 12)
            available_seats = [s for s in seats if s["status"] == "AVAILABLE"]
            check("12 available seats", len(available_seats) == 12)

            r = client.get("/api/v1/sessions")
            found = any(s["id"] == session_id for s in r.json()["data"]["items"])
            check("session list contains new session", found)

            # ---------- 用户 A：下单 / 锁座 / 支付 ----------
            _, token_a = register_user("smoke_a")
            headers_a = {"Authorization": f"Bearer {token_a}"}
            seat_a = available_seats[0]

            r = client.post(
                "/api/v1/orders",
                headers=headers_a,
                json={"session_id": session_id, "seat_ids": [seat_a["id"]]},
            )
            check(
                "A create order",
                r.status_code == 201 and r.json()["data"]["status"] == "PENDING_PAYMENT",
                r.text,
            )
            order_a_id = r.json()["data"]["id"]
            order_ids.append(order_a_id)
            check(
                "A ticket locked with expiry",
                r.json()["data"]["tickets"][0]["expires_at"] is not None,
            )

            # 用户 B 抢同一座位 -> 失败
            _, token_b = register_user("smoke_b")
            headers_b = {"Authorization": f"Bearer {token_b}"}
            r = client.post(
                "/api/v1/orders",
                headers=headers_b,
                json={"session_id": session_id, "seat_ids": [seat_a["id"]]},
            )
            check("B same seat rejected", r.status_code == 400 and r.json()["code"] == 4000, r.text)

            # A 支付
            r = client.post(f"/api/v1/orders/{order_a_id}/pay", headers=headers_a)
            check("A pay order", r.status_code == 200 and r.json()["data"]["status"] == "PAID", r.text)
            check("A ticket UNUSED", r.json()["data"]["tickets"][0]["status"] == "UNUSED")

            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            by_id = {s["id"]: s for s in r.json()["data"]}
            check("seat A sold", by_id[seat_a["id"]]["status"] == "SOLD")

            # ---------- 支付记录与回调幂等 ----------
            r = client.get(f"/api/v1/orders/{order_a_id}", headers=headers_a)
            payments = r.json()["data"]["payments"]
            check(
                "payment record created",
                len(payments) >= 1 and payments[0]["status"] == "SUCCESS" and payments[0]["method"] == "MOCK",
                r.text,
            )
            trade_no = payments[0]["provider_trade_no"]
            check("mock trade no", trade_no.startswith("MOCK"))
            r = client.post(f"/api/v1/payments/{trade_no}/callback", data={"sign": "mock-sign"})
            check("callback success", r.status_code == 200 and r.text == "success", r.text)
            r = client.post(f"/api/v1/payments/{trade_no}/callback", data={"sign": "bad-sign"})
            check("callback bad sign rejected", r.status_code == 401)
            r = client.get(f"/api/v1/orders/{order_a_id}", headers=headers_a)
            check(
                "callback idempotent",
                r.json()["data"]["status"] == "PAID"
                and r.json()["data"]["payments"][0]["status"] == "SUCCESS"
                and len(r.json()["data"]["tickets"]) == 1,
            )

            # ---------- 用户 B：下单后取消，座位释放 ----------
            seat_b = next(s for s in available_seats if s["id"] != seat_a["id"])
            r = client.post(
                "/api/v1/orders",
                headers=headers_b,
                json={"session_id": session_id, "seat_ids": [seat_b["id"]]},
            )
            check("B create order", r.status_code == 201)
            order_b_id = r.json()["data"]["id"]
            order_ids.append(order_b_id)
            r = client.post(f"/api/v1/orders/{order_b_id}/cancel", headers=headers_b)
            check("B cancel order", r.status_code == 200 and r.json()["data"]["status"] == "CANCELLED")
            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            by_id = {s["id"]: s for s in r.json()["data"]}
            check("seat B released", by_id[seat_b["id"]]["status"] == "AVAILABLE")

            # ---------- 用户 C：3 张上限 ----------
            _, token_c = register_user("smoke_c")
            headers_c = {"Authorization": f"Bearer {token_c}"}
            seats_c = [s["id"] for s in available_seats if s["id"] not in (seat_a["id"], seat_b["id"])][:3]
            r = client.post(
                "/api/v1/orders",
                headers=headers_c,
                json={"session_id": session_id, "seat_ids": seats_c},
            )
            check("C order 3 seats", r.status_code == 201, r.text)
            order_c_id = r.json()["data"]["id"]
            order_ids.append(order_c_id)
            r = client.post(f"/api/v1/orders/{order_c_id}/pay", headers=headers_c)
            check("C pay 3-seat order", r.status_code == 200)

            remaining_seats = [
                s for s in available_seats if s["id"] not in [seat_a["id"], seat_b["id"]] + seats_c
            ]
            r = client.post(
                "/api/v1/orders",
                headers=headers_c,
                json={"session_id": session_id, "seat_ids": [remaining_seats[0]["id"]]},
            )
            check("C 4th active ticket blocked", r.status_code == 400 and r.json()["code"] == 4000, r.text)

            # ---------- 核销 ----------
            r = client.get(f"/api/v1/admin/sessions/{session_id}/tickets", headers=admin_headers)
            check(
                "admin session tickets",
                r.status_code == 200
                and any(t["seat_no"] == seat_a["seat_no"] for t in r.json()["data"]),
                r.text,
            )
            r = client.post(f"/api/v1/admin/sessions/{session_id}/checkin", headers=admin_headers)
            check("admin checkin session", r.status_code == 200 and r.json()["data"]["checked_in"] == 4)
            r = client.get("/api/v1/tickets", headers=headers_a)
            check("A ticket USED after checkin", r.json()["data"][0]["status"] == "USED")

            # ---------- 用户 D：超时释放（直接调服务层） ----------
            _, token_d = register_user("smoke_d")
            headers_d = {"Authorization": f"Bearer {token_d}"}
            seat_d = remaining_seats[0]
            r = client.post(
                "/api/v1/orders",
                headers=headers_d,
                json={"session_id": session_id, "seat_ids": [seat_d["id"]]},
            )
            check("D create pending order", r.status_code == 201)
            order_d_id = r.json()["data"]["id"]
            order_ids.append(order_d_id)
            ticket_d_id = r.json()["data"]["tickets"][0]["id"]

            with SessionLocal() as db:
                t = db.get(Ticket, ticket_d_id)
                t.expires_at = datetime.now() - timedelta(seconds=1)
                seat = db.get(SessionSeat, seat_d["id"])
                seat.lock_expires_at = datetime.now() - timedelta(seconds=1)
                db.commit()
                released = release_expired_locks(db)
                db.commit()
            check("expired lock released", released >= 1)
            with SessionLocal() as db:
                t = db.get(Ticket, ticket_d_id)
                o = db.get(Order, order_d_id)
                seat_status = db.get(SessionSeat, seat_d["id"]).status
            check("D ticket expired", t.status == "EXPIRED")
            check("D order expired", o.status == "EXPIRED")
            check("seat D available again", seat_status == "AVAILABLE")

            # ---------- 停售/支付截止强制释放 ----------
            start2 = start + timedelta(hours=12)
            payload2 = {
                "movie_id": test_movie_id,
                "venue_id": test_venue_id,
                "start_at": start2.isoformat(),
                "sale_open_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "sale_close_at": (start2 - timedelta(minutes=30)).isoformat(),
                "base_price": "45.00",
            }
            r = client.post("/api/v1/sessions", headers=admin_headers, json=payload2)
            check("create session2", r.status_code == 201, r.text)
            session2_id = r.json()["data"]["id"]
            session_ids.append(session2_id)

            r = client.get(f"/api/v1/sessions/{session2_id}/seats")
            seat_e = r.json()["data"][0]
            r = client.post(
                "/api/v1/orders",
                headers=headers_d,
                json={"session_id": session2_id, "seat_ids": [seat_e["id"]]},
            )
            check("D order on session2", r.status_code == 201)
            order_e_id = r.json()["data"]["id"]
            order_ids.append(order_e_id)

            with SessionLocal() as db:
                s2 = db.get(MovieSession, session2_id)
                s2.sale_close_at = datetime.now() - timedelta(minutes=1)
                db.commit()
                cutoff_released = release_at_cutoff(db)
                db.commit()
                o2 = db.get(Order, order_e_id)
                ticket2 = db.scalars(
                    select(Ticket).where(Ticket.order_id == order_e_id)
                ).first()
            check("cutoff release ran", cutoff_released >= 1)
            check("order2 expired at cutoff", o2.status == "EXPIRED")
            check("ticket2 expired at cutoff", ticket2.status == "EXPIRED")

            # ---------- 里程碑 3：退款申请 / 审核 ----------
            uid_e, token_e = register_user("smoke_e")
            headers_e = {"Authorization": f"Bearer {token_e}"}

            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            avail = [s for s in r.json()["data"] if s["status"] == "AVAILABLE"]
            seat_e1 = avail[0]
            r = client.post(
                "/api/v1/orders",
                headers=headers_e,
                json={"session_id": session_id, "seat_ids": [seat_e1["id"]]},
            )
            check("E create order", r.status_code == 201, r.text)
            order_e1 = r.json()["data"]["id"]
            order_ids.append(order_e1)
            ticket_e1 = r.json()["data"]["tickets"][0]["id"]
            r = client.post(f"/api/v1/orders/{order_e1}/pay", headers=headers_e)
            check("E pay order", r.status_code == 200)

            r = client.post(
                f"/api/v1/tickets/{ticket_e1}/refund-request",
                headers=headers_e,
                json={"reason": "行程有变"},
            )
            check("E refund request", r.status_code == 201 and r.json()["data"]["status"] == "PENDING", r.text)
            req_id = r.json()["data"]["id"]
            check(
                "refund 90% amount with 10% fee",
                r.json()["data"]["refund_amount"] == "40.50" and r.json()["data"]["fee"] == "4.50",
            )
            r = client.post(f"/api/v1/tickets/{ticket_e1}/refund-request", headers=headers_e, json={})
            check("duplicate refund blocked", r.status_code == 400 and r.json()["code"] == 4000, r.text)

            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            seat_status = {s["id"]: s["status"] for s in r.json()["data"]}
            check("seat stays sold while pending", seat_status[seat_e1["id"]] == "SOLD")

            r = client.get("/api/v1/refund-requests", headers=headers_e)
            check("my refund requests listed", any(x["id"] == req_id for x in r.json()["data"]))
            r = client.get("/api/v1/admin/refund-requests?status=PENDING", headers=admin_headers)
            check("admin refund list", any(x["id"] == req_id for x in r.json()["data"]))

            r = client.post(f"/api/v1/admin/refund-requests/{req_id}/approve", headers=admin_headers)
            check("approve refund", r.status_code == 200 and r.json()["data"]["status"] == "APPROVED", r.text)
            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            seat_status = {s["id"]: s["status"] for s in r.json()["data"]}
            check("seat available after refund", seat_status[seat_e1["id"]] == "AVAILABLE")
            r = client.get("/api/v1/tickets", headers=headers_e)
            ticket_status = {t["id"]: t["status"] for t in r.json()["data"]}
            check("ticket refunded", ticket_status[ticket_e1] == "REFUNDED")

            # 拒绝路径：先重复申请被拦截，拒绝后可再次申请
            seat_e2 = next(s for s in avail if s["id"] != seat_e1["id"])
            r = client.post(
                "/api/v1/orders",
                headers=headers_e,
                json={"session_id": session_id, "seat_ids": [seat_e2["id"]]},
            )
            check("E order 2", r.status_code == 201)
            order_e2 = r.json()["data"]["id"]
            order_ids.append(order_e2)
            ticket_e2 = r.json()["data"]["tickets"][0]["id"]
            r = client.post(f"/api/v1/orders/{order_e2}/pay", headers=headers_e)
            check("E pay order 2", r.status_code == 200)
            r = client.post(f"/api/v1/tickets/{ticket_e2}/refund-request", headers=headers_e, json={"reason": "临时变化"})
            check("E refund request 2", r.status_code == 201)
            req2_id = r.json()["data"]["id"]
            r = client.post(f"/api/v1/admin/refund-requests/{req2_id}/reject", headers=admin_headers)
            check("reject refund", r.status_code == 200 and r.json()["data"]["status"] == "REJECTED", r.text)
            r = client.get("/api/v1/tickets", headers=headers_e)
            ticket_status = {t["id"]: t["status"] for t in r.json()["data"]}
            check("ticket back to UNUSED after reject", ticket_status[ticket_e2] == "UNUSED")
            r = client.post(f"/api/v1/tickets/{ticket_e2}/refund-request", headers=headers_e, json={})
            check("re-request allowed after reject", r.status_code == 201)

            # 开场前 10 分钟冻结：不允许退款
            start3 = datetime.now() + timedelta(minutes=30)
            payload3 = {
                "movie_id": test_movie_id,
                "venue_id": test_venue_id,
                "start_at": start3.isoformat(),
                "sale_open_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "sale_close_at": (start3 - timedelta(minutes=10)).isoformat(),
                "base_price": "45.00",
            }
            r = client.post("/api/v1/sessions", headers=admin_headers, json=payload3)
            check("create session3", r.status_code == 201, r.text)
            session3_id = r.json()["data"]["id"]
            session_ids.append(session3_id)
            r = client.get(f"/api/v1/sessions/{session3_id}/seats")
            seat_e3 = r.json()["data"][0]
            r = client.post(
                "/api/v1/orders",
                headers=headers_e,
                json={"session_id": session3_id, "seat_ids": [seat_e3["id"]]},
            )
            check("E order on session3", r.status_code == 201, r.text)
            order_e3 = r.json()["data"]["id"]
            order_ids.append(order_e3)
            ticket_e3 = r.json()["data"]["tickets"][0]["id"]
            r = client.post(f"/api/v1/orders/{order_e3}/pay", headers=headers_e)
            check("E pay session3", r.status_code == 200)
            with SessionLocal() as db:
                s3 = db.get(MovieSession, session3_id)
                s3.start_at = datetime.now() + timedelta(minutes=5)
                s3.end_at = s3.start_at + timedelta(minutes=90)
                db.commit()
            r = client.post(f"/api/v1/tickets/{ticket_e3}/refund-request", headers=headers_e, json={})
            check("refund frozen 10min before start", r.status_code == 400 and r.json()["code"] == 4000, r.text)

            # ---------- 里程碑 4：转赠 ----------
            uid_f, token_f = register_user("smoke_f")
            headers_f = {"Authorization": f"Bearer {token_f}"}

            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            avail = [s for s in r.json()["data"] if s["status"] == "AVAILABLE"]
            seat_g = avail[0]
            r = client.post(
                "/api/v1/orders",
                headers=headers_e,
                json={"session_id": session_id, "seat_ids": [seat_g["id"]]},
            )
            check("E buy for transfer", r.status_code == 201)
            order_g = r.json()["data"]["id"]
            order_ids.append(order_g)
            ticket_g = r.json()["data"]["tickets"][0]["id"]
            r = client.post(f"/api/v1/orders/{order_g}/pay", headers=headers_e)
            check("E pay for transfer", r.status_code == 200)

            r = client.post(
                f"/api/v1/tickets/{ticket_g}/transfer",
                headers=headers_e,
                json={"to_user_id": uid_f},
            )
            check("E transfer to F", r.status_code == 200 and r.json()["data"]["origin"] == "GIFTED", r.text)
            r = client.get("/api/v1/tickets?tab=unused", headers=headers_f)
            check(
                "F sees gifted ticket",
                any(t["id"] == ticket_g and t["origin"] == "GIFTED" for t in r.json()["data"]),
            )
            r = client.get("/api/v1/tickets?tab=history", headers=headers_e)
            check(
                "E history shows transferred out",
                any(t["id"] == ticket_g and t["transferred_out"] for t in r.json()["data"]),
            )
            r = client.get("/api/v1/transfers", headers=headers_e)
            check("transfer record listed", any(t["ticket_id"] == ticket_g for t in r.json()["data"]))

            r = client.post(
                f"/api/v1/tickets/{ticket_g}/transfer",
                headers=headers_f,
                json={"to_user_id": uid_e},
            )
            check("gifted ticket cannot re-transfer", r.status_code == 400 and r.json()["code"] == 4000, r.text)
            r = client.post(f"/api/v1/tickets/{ticket_g}/refund-request", headers=headers_f, json={})
            check("gifted ticket cannot refund", r.status_code == 400 and r.json()["code"] == 4000, r.text)

            # 开场前 10 分钟冻结：不可转赠
            r = client.post(
                f"/api/v1/tickets/{ticket_e3}/transfer",
                headers=headers_e,
                json={"to_user_id": uid_f},
            )
            check("transfer frozen 10min before start", r.status_code == 400 and r.json()["code"] == 4000, r.text)

            # 对方 3 张活跃票上限
            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            avail = [s for s in r.json()["data"] if s["status"] == "AVAILABLE"]
            for seat in avail[:2]:
                r = client.post(
                    "/api/v1/orders",
                    headers=headers_e,
                    json={"session_id": session_id, "seat_ids": [seat["id"]]},
                )
                assert r.status_code == 201, r.text
                oid = r.json()["data"]["id"]
                order_ids.append(oid)
                tid = r.json()["data"]["tickets"][0]["id"]
                r = client.post(f"/api/v1/orders/{oid}/pay", headers=headers_e)
                assert r.status_code == 200, r.text
                r = client.post(
                    f"/api/v1/tickets/{tid}/transfer",
                    headers=headers_e,
                    json={"to_user_id": uid_f},
                )
                assert r.status_code == 200, r.text
            r = client.get("/api/v1/tickets?tab=unused", headers=headers_f)
            check("F has 3 unused tickets", len(r.json()["data"]) == 3)

            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            avail = [s for s in r.json()["data"] if s["status"] == "AVAILABLE"]
            r = client.post(
                "/api/v1/orders",
                headers=headers_e,
                json={"session_id": session_id, "seat_ids": [avail[0]["id"]]},
            )
            assert r.status_code == 201, r.text
            oid = r.json()["data"]["id"]
            order_ids.append(oid)
            tid = r.json()["data"]["tickets"][0]["id"]
            r = client.post(f"/api/v1/orders/{oid}/pay", headers=headers_e)
            assert r.status_code == 200, r.text
            r = client.post(
                f"/api/v1/tickets/{tid}/transfer",
                headers=headers_e,
                json={"to_user_id": uid_f},
            )
            check("transfer blocked by recipient cap", r.status_code == 400 and r.json()["code"] == 4000, r.text)

            # ---------- 确认支付后的边界处理（票已过期但渠道已扣款） ----------
            from app.payments.mock import MockPaymentProvider as _MockProvider
            from app.services.payment_service import confirm_paid_order as _confirm

            class _RefundCapture(_MockProvider):
                def __init__(self):
                    self.refunds = []

                def refund(self, payment, amount):
                    self.refunds.append(amount)

            uid_g, token_g = register_user("smoke_g")
            r = client.get(f"/api/v1/sessions/{session_id}/seats")
            avail = [s for s in r.json()["data"] if s["status"] == "AVAILABLE"]

            # 全部票已过期 -> 自动全额退款
            r = client.post(
                "/api/v1/orders",
                headers={"Authorization": f"Bearer {token_g}"},
                json={"session_id": session_id, "seat_ids": [avail[0]["id"]]},
            )
            assert r.status_code == 201, r.text
            oid = r.json()["data"]["id"]
            order_ids.append(oid)
            tid = r.json()["data"]["tickets"][0]["id"]
            with SessionLocal() as db:
                t = db.get(Ticket, tid)
                t.status = "EXPIRED"
                t.expires_at = datetime.now() - timedelta(seconds=1)
                seat = db.get(SessionSeat, avail[0]["id"])
                seat.status = "AVAILABLE"
                seat.lock_order_id = None
                seat.lock_expires_at = None
                pay = Payment(
                    order_id=oid,
                    user_id=uid_g,
                    amount=45,
                    method="MOCK",
                    provider_trade_no=f"ORPHAN{oid}",
                    status="PENDING",
                )
                db.add(pay)
                db.flush()
                prov = _RefundCapture()
                try:
                    _confirm(db, db.get(Order, oid), pay, prov)
                    check("orphan full-expire auto refund", False, "未触发自动退款")
                except Exception as exc:
                    check(
                        "orphan full-expire auto refund",
                        "款项已自动原路退回" in str(exc)
                        and pay.status == "FAILED"
                        and len(prov.refunds) == 1,
                        str(exc),
                    )
                db.commit()

            # 部分票已过期 -> 只支付有效票，退差额
            r = client.post(
                "/api/v1/orders",
                headers={"Authorization": f"Bearer {token_g}"},
                json={"session_id": session_id, "seat_ids": [avail[1]["id"], avail[2]["id"]]},
            )
            assert r.status_code == 201, r.text
            oid2 = r.json()["data"]["id"]
            order_ids.append(oid2)
            tid_a = r.json()["data"]["tickets"][0]["id"]
            tid_b = r.json()["data"]["tickets"][1]["id"]
            with SessionLocal() as db:
                ta = db.get(Ticket, tid_a)
                ta.status = "EXPIRED"
                ta.expires_at = datetime.now() - timedelta(seconds=1)
                seat_a = db.get(SessionSeat, avail[1]["id"])
                seat_a.status = "AVAILABLE"
                seat_a.lock_order_id = None
                seat_a.lock_expires_at = None
                pay2 = Payment(
                    order_id=oid2,
                    user_id=uid_g,
                    amount=90,
                    method="MOCK",
                    provider_trade_no=f"PARTIAL{oid2}",
                    status="PENDING",
                )
                db.add(pay2)
                db.flush()
                prov2 = _RefundCapture()
                _confirm(db, db.get(Order, oid2), pay2, prov2)
                db.refresh(pay2)
                tb = db.get(Ticket, tid_b)
                check(
                    "partial expire refunds difference",
                    pay2.status == "SUCCESS" and len(prov2.refunds) == 1 and tb.status == "UNUSED",
                )
                db.commit()
        finally:
            # ---------- 清理测试数据 ----------
            with SessionLocal() as db:
                if session_ids:
                    ticket_ids_subq = select(Ticket.id).where(Ticket.session_id.in_(session_ids))
                    order_ids_subq = select(Order.id).where(Order.session_id.in_(session_ids))
                    db.execute(delete(TransferRecord).where(TransferRecord.ticket_id.in_(ticket_ids_subq)))
                    db.execute(delete(RefundRequest).where(RefundRequest.ticket_id.in_(ticket_ids_subq)))
                    db.execute(delete(Payment).where(Payment.order_id.in_(order_ids_subq)))
                    db.execute(delete(Ticket).where(Ticket.session_id.in_(session_ids)))
                    db.execute(delete(Order).where(Order.session_id.in_(session_ids)))
                    db.execute(delete(MovieSession).where(MovieSession.id.in_(session_ids)))
                if test_venue_id:
                    db.execute(delete(Venue).where(Venue.id == test_venue_id))
                if test_movie_id:
                    db.execute(delete(Movie).where(Movie.id == test_movie_id))
                if user_ids:
                    db.execute(delete(User).where(User.id.in_(user_ids)))
                db.commit()

    failed = [name for name, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} 通过")
    if failed:
        print("失败项:", failed)
        raise SystemExit(1)
    print("Smoke test 全部通过")


if __name__ == "__main__":
    main()
