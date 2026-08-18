import { useCallback, useEffect, useState } from "react";
import { Button, Select, Space, Table, Tag, message } from "antd";
import type { TableColumnsType } from "antd";
import dayjs from "dayjs";
import { get, post } from "../../api/client";
import type { Page, SessionItem, TicketAdminOut } from "../../api/types";

const STATUS_TAG: Record<string, { text: string; color: string }> = {
  PENDING_PAYMENT: { text: "待支付", color: "orange" },
  UNUSED: { text: "待使用", color: "blue" },
  USED: { text: "已使用", color: "green" },
  REFUND_APPLIED: { text: "退款审核中", color: "purple" },
  REFUNDED: { text: "已退款", color: "red" },
  EXPIRED: { text: "已过期", color: "default" },
};

export default function AdminCheckin() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [tickets, setTickets] = useState<TicketAdminOut[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    get<Page<SessionItem>>("/sessions?page=1&page_size=100")
      .then((p) => setSessions(p.items))
      .catch((e) => message.error((e as Error).message));
  }, []);

  const loadTickets = useCallback(async (id: number) => {
    setLoading(true);
    try {
      setTickets(await get<TicketAdminOut[]>(`/admin/sessions/${id}/tickets`));
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkinOne = async (t: TicketAdminOut) => {
    try {
      await post(`/admin/tickets/${t.id}/checkin`);
      message.success(`${t.seat_no} 已核销`);
      if (selectedId) loadTickets(selectedId);
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const checkinAll = async () => {
    if (!selectedId) return;
    try {
      const r = await post<{ checked_in: number }>(`/admin/sessions/${selectedId}/checkin`);
      message.success(`已核销 ${r.checked_in} 张票`);
      loadTickets(selectedId);
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const columns: TableColumnsType<TicketAdminOut> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "座位", dataIndex: "seat_no", width: 80 },
    { title: "持有者", dataIndex: "owner_username", width: 110 },
    { title: "购买者", dataIndex: "purchaser_username", width: 110 },
    {
      title: "来源",
      dataIndex: "origin",
      width: 90,
      render: (v: string) => <Tag color={v === "GIFTED" ? "gold" : "geekblue"}>{v === "GIFTED" ? "受赠" : "自购"}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 110,
      render: (v: string) => {
        const t = STATUS_TAG[v] ?? { text: v, color: "default" };
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: "核销时间",
      dataIndex: "checked_in_at",
      width: 150,
      render: (v: string | null) => (v ? dayjs(v).format("MM-DD HH:mm:ss") : "-"),
    },
    {
      title: "操作",
      width: 100,
      render: (_, t) => (
        <Button size="small" type="primary" disabled={t.status !== "UNUSED"} onClick={() => checkinOne(t)}>
          核销
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Select
          style={{ width: 360 }}
          placeholder="选择场次"
          value={selectedId}
          onChange={(v: number) => {
            setSelectedId(v);
            loadTickets(v);
          }}
          options={sessions.map((s) => ({
            value: s.id,
            label: `${s.movie_title} | ${s.venue_name} | ${dayjs(s.start_at).format("MM-DD HH:mm")}`,
          }))}
        />
        <Button type="primary" disabled={!selectedId} onClick={checkinAll}>
          整场一键核销
        </Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={tickets}
        pagination={{ pageSize: 20 }}
      />
    </div>
  );
}
