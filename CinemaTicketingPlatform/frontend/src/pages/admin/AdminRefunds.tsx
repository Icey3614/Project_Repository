import { useCallback, useEffect, useState } from "react";
import { Button, Space, Table, Tag, message } from "antd";
import type { TableColumnsType } from "antd";
import dayjs from "dayjs";
import { get, post } from "../../api/client";
import type { RefundRequest } from "../../api/types";

const STATUS_TAG: Record<string, { text: string; color: string }> = {
  PENDING: { text: "审核中", color: "purple" },
  APPROVED: { text: "已退款", color: "green" },
  REJECTED: { text: "已拒绝", color: "red" },
};

export default function AdminRefunds() {
  const [requests, setRequests] = useState<RefundRequest[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRequests(await get<RefundRequest[]>("/admin/refund-requests"));
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const review = async (id: number, action: "approve" | "reject") => {
    try {
      await post(`/admin/refund-requests/${id}/${action}`);
      message.success(action === "approve" ? "已同意退款" : "已拒绝");
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const columns: TableColumnsType<RefundRequest> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "电影", dataIndex: "movie_title" },
    { title: "座位", dataIndex: "seat_no", width: 80 },
    { title: "用户ID", dataIndex: "user_id", width: 80 },
    { title: "原价", dataIndex: "original_amount", width: 90 },
    { title: "退款金额", dataIndex: "refund_amount", width: 100 },
    { title: "手续费", dataIndex: "fee", width: 90 },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (v: string) => {
        const t = STATUS_TAG[v] ?? { text: v, color: "default" };
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: "申请时间",
      dataIndex: "created_at",
      width: 150,
      render: (v: string) => dayjs(v).format("MM-DD HH:mm"),
    },
    {
      title: "操作",
      width: 150,
      render: (_, r) =>
        r.status === "PENDING" ? (
          <Space>
            <Button size="small" type="primary" onClick={() => review(r.id, "approve")}>
              同意
            </Button>
            <Button size="small" danger onClick={() => review(r.id, "reject")}>
              拒绝
            </Button>
          </Space>
        ) : null,
    },
  ];

  return (
    <Table
      rowKey="id"
      loading={loading}
      columns={columns}
      dataSource={requests}
      pagination={{ pageSize: 10 }}
    />
  );
}
