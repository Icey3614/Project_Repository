import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  message,
} from "antd";
import type { TableColumnsType } from "antd";
import { api, get, post } from "../../api/client";
import type { Venue, VenueSeat } from "../../api/types";

interface VenueFormValues {
  name: string;
  rows: number;
  cols: number;
  capacity?: number;
  exits_text?: string;
}

export default function AdminVenues() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [seatVenue, setSeatVenue] = useState<Venue | null>(null);
  const [seats, setSeats] = useState<VenueSeat[]>([]);
  const [enabledMap, setEnabledMap] = useState<Record<number, boolean>>({});

  const load = useCallback(async () => {
    try {
      setVenues(await get<Venue[]>("/venues"));
    } catch (e) {
      message.error((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = async () => {
    const values = (await form.validateFields()) as VenueFormValues;
    const exits = (values.exits_text ?? "")
      .split(/[,，]/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((label) => ({ label, side: "right" }));
    setSaving(true);
    try {
      await post("/venues", {
        name: values.name,
        rows: values.rows,
        cols: values.cols,
        capacity: values.capacity,
        screen_pos: { position: "front" },
        exits,
      });
      message.success("场馆已创建（座位模板已生成）");
      setModalOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (v: Venue) => {
    try {
      await api.delete(`/venues/${v.id}`);
      message.success("已删除");
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const openSeatEditor = async (v: Venue) => {
    try {
      const list = await get<VenueSeat[]>(`/venues/${v.id}/seats`);
      setSeats(list);
      setEnabledMap(Object.fromEntries(list.map((s) => [s.id, s.enabled])));
      setSeatVenue(v);
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const saveSeats = async () => {
    if (!seatVenue) return;
    const changes = seats
      .filter((s) => enabledMap[s.id] !== s.enabled)
      .map((s) => ({ id: s.id, enabled: enabledMap[s.id] }));
    if (changes.length === 0) {
      setSeatVenue(null);
      return;
    }
    try {
      await api.put(`/venues/${seatVenue.id}/seats`, { seats: changes });
      message.success("座位布局已更新");
      setSeatVenue(null);
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const seatAt = (r: number, c: number) => seats.find((s) => s.row_no === r && s.col_no === c);

  const columns: TableColumnsType<Venue> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "场馆名称", dataIndex: "name" },
    { title: "布局", width: 120, render: (_, v) => `${v.rows} 排 x ${v.cols} 列` },
    { title: "容量", dataIndex: "capacity", width: 80 },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (s: string) => <Tag color={s === "ACTIVE" ? "green" : "default"}>{s}</Tag>,
    },
    {
      title: "操作",
      width: 190,
      render: (_, v) => (
        <Space>
          <Button size="small" onClick={() => openSeatEditor(v)}>
            座位编辑
          </Button>
          <Popconfirm title="确认删除该场馆？" onConfirm={() => remove(v)}>
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
      <Button type="primary" style={{ marginBottom: 12 }} onClick={() => setModalOpen(true)}>
        新建场馆
      </Button>
      <Table rowKey="id" columns={columns} dataSource={venues} pagination={false} />

      <Modal
        title="新建场馆"
        open={modalOpen}
        onOk={create}
        confirmLoading={saving}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="场馆名称" rules={[{ required: true }]}>
            <Input placeholder="如：1号厅" />
          </Form.Item>
          <Space>
            <Form.Item name="rows" label="排数" rules={[{ required: true }]}>
              <InputNumber min={1} max={100} />
            </Form.Item>
            <Form.Item name="cols" label="列数" rules={[{ required: true }]}>
              <InputNumber min={1} max={100} />
            </Form.Item>
            <Form.Item name="capacity" label="容量（选填）">
              <InputNumber min={1} />
            </Form.Item>
          </Space>
          <Form.Item name="exits_text" label="出入口（逗号分隔）">
            <Input placeholder="如：入口A, 入口B" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`座位编辑器 - ${seatVenue?.name ?? ""}`}
        open={!!seatVenue}
        onOk={saveSeats}
        onCancel={() => setSeatVenue(null)}
        width={720}
      >
        {seatVenue && (
          <div className="seat-map">
            <div className="seat-screen">荧 幕</div>
            {Array.from({ length: seatVenue.rows }, (_, i) => i + 1).map((r) => (
              <div className="seat-row" key={r}>
                <span className="seat-row-label">{r}排</span>
                {Array.from({ length: seatVenue.cols }, (_, i) => i + 1).map((c) => {
                  const seat = seatAt(r, c);
                  if (!seat) return <span className="seat-empty" key={c} />;
                  const enabled = enabledMap[seat.id];
                  return (
                    <button
                      key={c}
                      className={`seat-btn ${enabled ? "available" : "disabled"}`}
                      title={seat.seat_no}
                      onClick={() => setEnabledMap((m) => ({ ...m, [seat.id]: !m[seat.id] }))}
                    >
                      {seat.seat_no}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
