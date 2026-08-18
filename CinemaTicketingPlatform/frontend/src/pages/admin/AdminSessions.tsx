import { useCallback, useEffect, useState } from "react";
import {
  Button,
  DatePicker,
  Form,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  message,
} from "antd";
import type { TableColumnsType } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { api, get, post } from "../../api/client";
import type { Movie, Page, SessionItem, Venue } from "../../api/types";

const STATUS_TAG: Record<string, { text: string; color: string }> = {
  SCHEDULED: { text: "未开售", color: "default" },
  SELLING: { text: "售票中", color: "green" },
  SOLD_OUT: { text: "已售罄", color: "red" },
  STOPPED: { text: "已停售", color: "orange" },
  ENDED: { text: "已结束", color: "default" },
};

interface CreateValues {
  movie_id: number;
  venue_id: number;
  start_at: Dayjs;
  sale_open_at: Dayjs;
  sale_close_at: Dayjs;
  base_price: number;
}

interface EditValues {
  sale_open_at: Dayjs;
  sale_close_at: Dayjs;
  base_price: number;
}

const fmt = (d: Dayjs) => d.format("YYYY-MM-DDTHH:mm:ss");

export default function AdminSessions() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [movies, setMovies] = useState<Movie[]>([]);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [editSession, setEditSession] = useState<SessionItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const load = useCallback(async () => {
    try {
      const [s, m, v] = await Promise.all([
        get<Page<SessionItem>>("/sessions?page=1&page_size=100"),
        get<Page<Movie>>("/movies?page=1&page_size=100"),
        get<Venue[]>("/venues"),
      ]);
      setSessions(s.items);
      setMovies(m.items);
      setVenues(v);
    } catch (e) {
      message.error((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = async () => {
    const values = (await createForm.validateFields()) as CreateValues;
    setSaving(true);
    try {
      await post("/sessions", {
        movie_id: values.movie_id,
        venue_id: values.venue_id,
        start_at: fmt(values.start_at),
        sale_open_at: fmt(values.sale_open_at),
        sale_close_at: fmt(values.sale_close_at),
        base_price: String(values.base_price),
      });
      message.success("排片成功");
      setCreateOpen(false);
      createForm.resetFields();
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const openEdit = (s: SessionItem) => {
    setEditSession(s);
    editForm.setFieldsValue({
      sale_open_at: dayjs(s.sale_open_at),
      sale_close_at: dayjs(s.sale_close_at),
      base_price: parseFloat(s.base_price),
    });
  };

  const saveEdit = async () => {
    if (!editSession) return;
    const values = (await editForm.validateFields()) as EditValues;
    setSaving(true);
    try {
      await api.put(`/sessions/${editSession.id}`, {
        sale_open_at: fmt(values.sale_open_at),
        sale_close_at: fmt(values.sale_close_at),
        base_price: String(values.base_price),
      });
      message.success("场次已更新");
      setEditSession(null);
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (s: SessionItem) => {
    try {
      await api.delete(`/sessions/${s.id}`);
      message.success("已删除");
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const columns: TableColumnsType<SessionItem> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "电影", dataIndex: "movie_title" },
    { title: "场馆", dataIndex: "venue_name", width: 110 },
    {
      title: "开场时间",
      dataIndex: "start_at",
      width: 160,
      render: (v: string) => dayjs(v).format("MM-DD HH:mm"),
    },
    { title: "票价", dataIndex: "base_price", width: 80 },
    {
      title: "余票",
      width: 90,
      render: (_, s) => `${s.remaining}/${s.total_seats}`,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (v: string) => {
        const t = STATUS_TAG[v] ?? { text: v, color: "default" };
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: "操作",
      width: 150,
      render: (_, s) => (
        <Space>
          <Button size="small" onClick={() => openEdit(s)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该场次？" onConfirm={() => remove(s)}>
            <Button size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Button type="primary" style={{ marginBottom: 12 }} onClick={() => setCreateOpen(true)}>
        新增场次
      </Button>
      <Table rowKey="id" columns={columns} dataSource={sessions} pagination={{ pageSize: 10 }} />

      <Modal
        title="新增场次"
        open={createOpen}
        onOk={create}
        confirmLoading={saving}
        onCancel={() => setCreateOpen(false)}
        width={560}
      >
        <Form form={createForm} layout="vertical" initialValues={{ base_price: 45 }}>
          <Form.Item name="movie_id" label="电影" rules={[{ required: true }]}>
            <Select options={movies.map((m) => ({ value: m.id, label: m.title }))} />
          </Form.Item>
          <Form.Item name="venue_id" label="场馆" rules={[{ required: true }]}>
            <Select options={venues.map((v) => ({ value: v.id, label: v.name }))} />
          </Form.Item>
          <Form.Item name="start_at" label="开场时间" rules={[{ required: true }]}>
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>
          <Space style={{ width: "100%" }} align="start">
            <Form.Item name="sale_open_at" label="开售时间" rules={[{ required: true }]}>
              <DatePicker showTime />
            </Form.Item>
            <Form.Item name="sale_close_at" label="停售时间" rules={[{ required: true }]}>
              <DatePicker showTime />
            </Form.Item>
          </Space>
          <Form.Item name="base_price" label="票价（元）" rules={[{ required: true }]}>
            <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`编辑场次 #${editSession?.id ?? ""}`}
        open={!!editSession}
        onOk={saveEdit}
        confirmLoading={saving}
        onCancel={() => setEditSession(null)}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="sale_open_at" label="开售时间" rules={[{ required: true }]}>
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="sale_close_at" label="停售时间" rules={[{ required: true }]}>
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="base_price" label="票价（元）" rules={[{ required: true }]}>
            <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
