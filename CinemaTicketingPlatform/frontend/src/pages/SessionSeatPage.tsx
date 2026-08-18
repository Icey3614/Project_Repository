import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Card, Descriptions, message, Space, Spin, Tag, Typography } from "antd";
import dayjs from "dayjs";
import { get, post } from "../api/client";
import type { Order, SessionItem, SessionSeat } from "../api/types";
import SeatMap from "../components/SeatMap";

export default function SessionSeatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<SessionItem | null>(null);
  const [seats, setSeats] = useState<SessionSeat[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(false);
  const [paying, setPaying] = useState(false);

  const load = async () => {
    const [s, ss] = await Promise.all([
      get<SessionItem>(`/sessions/${sessionId}`),
      get<SessionSeat[]>(`/sessions/${sessionId}/seats`),
    ]);
    setSession(s);
    setSeats(ss);
  };

  useEffect(() => {
    load().catch((e) => message.error(e.message));
  }, [sessionId]);

  const selected = useMemo(
    () => seats.filter((s) => selectedIds.includes(s.id)),
    [seats, selectedIds]
  );
  const total = selected.reduce((sum, s) => sum + parseFloat(s.price), 0);
  const selling = session?.status === "SELLING";

  const toggle = (seatId: number) => {
    if (selectedIds.includes(seatId)) {
      setSelectedIds(selectedIds.filter((x) => x !== seatId));
    } else if (selectedIds.length >= 3) {
      message.warning("单次最多选择 3 个座位");
    } else {
      setSelectedIds([...selectedIds, seatId]);
    }
  };

  const handleBuy = async () => {
    if (selectedIds.length === 0) return;
    setLoading(true);
    try {
      const o = await post<Order>("/orders", {
        session_id: Number(sessionId),
        seat_ids: selectedIds,
      });
      setOrder(o);
      setSelectedIds([]);
      message.success("下单成功，请在 20 分钟内完成支付");
    } catch (e) {
      message.error((e as Error).message);
      load();
    } finally {
      setLoading(false);
    }
  };

  const handlePay = async () => {
    if (!order) return;
    setPaying(true);
    try {
      const o = await post<Order>(`/orders/${order.id}/pay`);
      const pay = o.payments?.[0];
      if (pay?.pay_url) {
        window.location.href = pay.pay_url;
        return;
      }
      message.success("支付成功");
      navigate("/me", { state: { tab: "pending" } });
    } catch (e) {
      message.error((e as Error).message);
      setOrder(null);
      load();
    } finally {
      setPaying(false);
    }
  };

  const handleCancel = async () => {
    if (!order) return;
    await post<Order>(`/orders/${order.id}/cancel`);
    message.info("已取消订单");
    setOrder(null);
    load();
  };

  if (!session) {
    return (
      <div style={{ textAlign: "center", padding: 60 }}>
        <Spin />
      </div>
    );
  }

  const expiresAt = order?.tickets[0]?.expires_at;

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="电影">{session.movie_title}</Descriptions.Item>
          <Descriptions.Item label="场馆">{session.venue_name}</Descriptions.Item>
          <Descriptions.Item label="时间">
            {dayjs(session.start_at).format("YYYY-MM-DD HH:mm")}
          </Descriptions.Item>
          <Descriptions.Item label="票价">¥{session.base_price}</Descriptions.Item>
          <Descriptions.Item label="余票">{session.remaining}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={selling ? "green" : "red"}>{selling ? "售票中" : "已停售"}</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <SeatMap seats={seats} selectedIds={selectedIds} onToggle={toggle} />

      {order ? (
        <Card style={{ marginTop: 16 }}>
          <Alert
            type="warning"
            showIcon
            message={
              <Space>
                <span>订单 {order.order_no} 待支付</span>
                {expiresAt && (
                  <span>
                    剩余支付时间：<Countdown expiresAt={expiresAt} />
                  </span>
                )}
              </Space>
            }
            description={`合计 ¥${order.total_amount}`}
          />
          <Space style={{ marginTop: 12 }}>
            <Button type="primary" loading={paying} onClick={handlePay}>
              立即支付（模拟）
            </Button>
            <Button onClick={handleCancel}>取消订单</Button>
          </Space>
        </Card>
      ) : (
        <Card style={{ marginTop: 16 }}>
          <Typography.Text>
            已选 {selected.length} 个座位：
            {selected.map((s) => s.seat_no).join("、") || "请点击上方座位图选座"}
            {selected.length > 0 && <>（合计 ¥{total.toFixed(2)}）</>}
          </Typography.Text>
          <br />
          <Button
            type="primary"
            disabled={selected.length === 0 || !selling}
            loading={loading}
            onClick={handleBuy}
            style={{ marginTop: 12 }}
          >
            立即购买
          </Button>
        </Card>
      )}
    </div>
  );
}

function Countdown({ expiresAt }: { expiresAt: string }) {
  const [left, setLeft] = useState(() => Math.max(0, dayjs(expiresAt).diff(dayjs(), "second")));

  useEffect(() => {
    const timer = setInterval(() => {
      setLeft(Math.max(0, dayjs(expiresAt).diff(dayjs(), "second")));
    }, 1000);
    return () => clearInterval(timer);
  }, [expiresAt]);

  const mm = Math.floor(left / 60);
  const ss = String(left % 60).padStart(2, "0");
  return <span>{left > 0 ? `${mm}:${ss}` : "已过期"}</span>;
}
