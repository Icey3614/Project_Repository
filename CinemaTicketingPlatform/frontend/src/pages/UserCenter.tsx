import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Button,
  Card,
  Empty,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import dayjs from "dayjs";
import { get, post } from "../api/client";
import type { Order, RefundRequest, Ticket } from "../api/types";

const STATUS_TAG: Record<string, { text: string; color: string }> = {
  PENDING_PAYMENT: { text: "待支付", color: "orange" },
  UNUSED: { text: "待使用", color: "blue" },
  USED: { text: "已使用", color: "green" },
  REFUND_APPLIED: { text: "退款审核中", color: "purple" },
  REFUNDED: { text: "已退款", color: "red" },
  EXPIRED: { text: "已过期", color: "default" },
};

export default function UserCenter() {
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<Ticket[]>([]);
  const [unused, setUnused] = useState<Ticket[]>([]);
  const [history, setHistory] = useState<Ticket[]>([]);
  const [refunds, setRefunds] = useState<RefundRequest[]>([]);
  const [transferTicket, setTransferTicket] = useState<Ticket | null>(null);
  const [toUserId, setToUserId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, u, h, r] = await Promise.all([
        get<Ticket[]>("/tickets?tab=pending"),
        get<Ticket[]>("/tickets?tab=unused"),
        get<Ticket[]>("/tickets?tab=history"),
        get<RefundRequest[]>("/refund-requests"),
      ]);
      setPending(p);
      setUnused(u);
      setHistory(h);
      setRefunds(r);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pay = async (t: Ticket) => {
    try {
      const o = await post<Order>(`/orders/${t.order_id}/pay`);
      const p = o.payments?.[0];
      if (p?.pay_url) {
        window.location.href = p.pay_url;
        return;
      }
      message.success("支付成功");
      load();
    } catch (e) {
      message.error((e as Error).message);
      load();
    }
  };

  const syncPayment = async (t: Ticket) => {
    try {
      await post(`/orders/${t.order_id}/sync-payment`);
      message.success("支付状态已更新");
      load();
    } catch (e) {
      message.error((e as Error).message);
      load();
    }
  };

  const cancel = async (t: Ticket) => {
    await post(`/orders/${t.order_id}/cancel`);
    message.info("已取消订单");
    load();
  };

  const applyRefund = async (t: Ticket) => {
    try {
      await post(`/tickets/${t.id}/refund-request`, { reason: "用户主动申请退款" });
      message.success("退款申请已提交，等待管理员审核");
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const confirmTransfer = async () => {
    if (!transferTicket || !toUserId) {
      message.warning("请输入对方用户 ID");
      return;
    }
    try {
      await post(`/tickets/${transferTicket.id}/transfer`, { to_user_id: toUserId });
      message.success("转赠成功");
      setTransferTicket(null);
      setToUserId(null);
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const renderTicket = (t: Ticket, extra?: ReactNode) => {
    const st = STATUS_TAG[t.status] ?? { text: t.status, color: "default" };
    return (
      <Card size="small" key={t.id} style={{ marginBottom: 8 }}>
        <Space direction="vertical" size={2}>
          <Space>
            <Typography.Text strong>{t.movie_title}</Typography.Text>
            <Tag color={st.color}>{st.text}</Tag>
            <Tag color={t.origin === "GIFTED" ? "gold" : "geekblue"}>
              {t.origin === "GIFTED" ? "受赠" : "自购"}
            </Tag>
            {t.transferred_out && (
              <Tag color="cyan">已转赠{t.transferred_to ? `给 ${t.transferred_to}` : ""}</Tag>
            )}
          </Space>
          <Typography.Text type="secondary">
            {t.venue_name} · {dayjs(t.start_at).format("MM-DD HH:mm")} · {t.seat_no} · ¥{t.price}
          </Typography.Text>
          {extra}
        </Space>
      </Card>
    );
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 60 }}>
        <Spin />
      </div>
    );
  }

  return (
    <Card>
      <Tabs
        items={[
          {
            key: "pending",
            label: `待支付 (${pending.length})`,
            children:
              pending.length === 0 ? (
                <Empty description="暂无待支付订单" />
              ) : (
                pending.map((t) =>
                  renderTicket(
                    t,
                    <Space style={{ marginTop: 8 }}>
                      <Button type="primary" size="small" onClick={() => pay(t)}>
                        去支付
                      </Button>
                      <Button size="small" onClick={() => syncPayment(t)}>
                        刷新状态
                      </Button>
                      <Popconfirm title="确认取消该订单？" onConfirm={() => cancel(t)}>
                        <Button size="small">取消订单</Button>
                      </Popconfirm>
                      {t.expires_at && (
                        <Typography.Text type="danger">
                          剩余 <Countdown expiresAt={t.expires_at} />
                        </Typography.Text>
                      )}
                    </Space>
                  )
                )
              ),
          },
          {
            key: "unused",
            label: `待使用 (${unused.length})`,
            children:
              unused.length === 0 ? (
                <Empty description="暂无待使用电影票" />
              ) : (
                unused.map((t) =>
                  renderTicket(
                    t,
                    <Space style={{ marginTop: 8 }}>
                      <Button size="small" onClick={() => setTransferTicket(t)}>
                        转赠
                      </Button>
                      <Popconfirm title="确认申请退款？（收取 10% 手续费）" onConfirm={() => applyRefund(t)}>
                        <Button size="small" danger>
                          申请退款
                        </Button>
                      </Popconfirm>
                    </Space>
                  )
                )
              ),
          },
          {
            key: "history",
            label: `历史购买 (${history.length})`,
            children:
              history.length === 0 ? (
                <Empty description="暂无历史记录" />
              ) : (
                history.map((t) => renderTicket(t))
              ),
          },
          {
            key: "refunds",
            label: `退款申请 (${refunds.length})`,
            children:
              refunds.length === 0 ? (
                <Empty description="暂无退款申请" />
              ) : (
                refunds.map((r) => (
                  <Card size="small" key={r.id} style={{ marginBottom: 8 }}>
                    <Space>
                      <Typography.Text strong>{r.movie_title}</Typography.Text>
                      <Tag color={r.status === "PENDING" ? "purple" : r.status === "APPROVED" ? "green" : "red"}>
                        {r.status === "PENDING" ? "审核中" : r.status === "APPROVED" ? "已退款" : "已拒绝"}
                      </Tag>
                    </Space>
                    <br />
                    <Typography.Text type="secondary">
                      {r.seat_no} · 原价 ¥{r.original_amount} · 退款 ¥{r.refund_amount}（手续费 ¥{r.fee}）
                    </Typography.Text>
                  </Card>
                ))
              ),
          },
        ]}
      />

      <Modal
        title={`转赠电影票 - ${transferTicket?.seat_no ?? ""}`}
        open={!!transferTicket}
        onOk={confirmTransfer}
        onCancel={() => {
          setTransferTicket(null);
          setToUserId(null);
        }}
      >
        <Typography.Paragraph>
          输入对方用户 ID（对方收到后该票标记为“受赠”，不可再转赠、不可退款）
        </Typography.Paragraph>
        <InputNumber
          style={{ width: "100%" }}
          placeholder="对方用户 ID"
          value={toUserId}
          onChange={(v) => setToUserId(v)}
          min={1}
        />
      </Modal>
    </Card>
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
