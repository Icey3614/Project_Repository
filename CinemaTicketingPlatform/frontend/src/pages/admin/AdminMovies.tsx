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
  message,
} from "antd";
import type { TableColumnsType } from "antd";
import dayjs from "dayjs";
import { api, get, post } from "../../api/client";
import type { Movie, Page } from "../../api/types";

export default function AdminMovies() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Movie | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    try {
      const p = await get<Page<Movie>>("/movies?page=1&page_size=100");
      setMovies(p.items);
    } catch (e) {
      message.error((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (m: Movie) => {
    setEditing(m);
    form.setFieldsValue(m);
    setModalOpen(true);
  };

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) await api.put(`/movies/${editing.id}`, values);
      else await post("/movies", values);
      message.success("保存成功");
      setModalOpen(false);
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (m: Movie) => {
    try {
      await api.delete(`/movies/${m.id}`);
      message.success("已删除");
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const columns: TableColumnsType<Movie> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "片名", dataIndex: "title" },
    { title: "时长(分钟)", dataIndex: "duration_min", width: 100 },
    { title: "简介", dataIndex: "description", ellipsis: true },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 160,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "操作",
      width: 140,
      render: (_, m) => (
        <Space>
          <Button size="small" onClick={() => openEdit(m)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该电影？" onConfirm={() => remove(m)}>
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
      <Button type="primary" style={{ marginBottom: 12 }} onClick={openCreate}>
        新增电影
      </Button>
      <Table rowKey="id" columns={columns} dataSource={movies} pagination={{ pageSize: 10 }} />
      <Modal
        title={editing ? "编辑电影" : "新增电影"}
        open={modalOpen}
        onOk={save}
        confirmLoading={saving}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="片名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="duration_min" label="时长（分钟）" rules={[{ required: true }]}>
            <InputNumber min={1} max={600} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="poster_url" label="海报地址">
            <Input placeholder="选填" />
          </Form.Item>
          <Form.Item name="description" label="简介">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
