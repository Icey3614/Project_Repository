import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Result,
  Space,
  Spin,
  Steps,
  Tag,
  message,
} from "antd";
import { get, post } from "../api/client";
import type { SetupStatus } from "../api/types";

export default function Setup() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [dbForm] = Form.useForm();
  const [alipayForm] = Form.useForm();

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await get<SetupStatus>("/setup/status"));
    } catch (e) {
      message.error((e as Error).message);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const submitDatabase = async () => {
    const values = await dbForm.validateFields();
    setLoading(true);
    try {
      await post("/setup/database", {
        host: values.host,
        port: values.port,
        username: values.username,
        password: values.password,
        db_name: values.db_name,
      });
      message.success("数据库初始化完成（建库、建表、种子数据）");
      loadStatus();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const submitAlipay = async (useMock: boolean) => {
    const values = useMock ? {} : await alipayForm.validateFields();
    setLoading(true);
    try {
      const r = await post<{ pay_provider: string }>("/setup/alipay", values);
      message.success(r.pay_provider === "mock" ? "已启用模拟支付" : "支付宝沙箱配置已保存");
      loadStatus();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (!status) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin />
      </div>
    );
  }

  const done = status.db_configured && status.alipay_configured;
  const currentStep = status.db_configured ? 1 : 0;

  return (
    <Card title="首次运行配置" style={{ maxWidth: 760, margin: "24px auto" }}>
      <Alert
        style={{ marginBottom: 16 }}
        type={status.mysql_running ? "success" : "error"}
        showIcon
        message={
          <Space>
            MySQL 检测：{status.mysql_running ? "本机已检测到 MySQL 服务" : "未检测到 MySQL，请先启动本机 MySQL"}
            <Tag color={status.db_configured ? "green" : "orange"}>
              {status.db_configured ? "数据库已配置" : "数据库未配置"}
            </Tag>
            <Tag color={status.alipay_configured ? "green" : "default"}>
              {status.alipay_configured ? "支付宝沙箱已配置" : "支付：模拟/未配置"}
            </Tag>
          </Space>
        }
      />

      <Steps
        current={currentStep}
        items={[{ title: "数据库配置" }, { title: "支付配置" }, { title: "完成" }]}
        style={{ marginBottom: 24 }}
      />

      {!status.db_configured && (
        <Form form={dbForm} layout="vertical" initialValues={{ host: "127.0.0.1", port: 3306, db_name: "cinema_platform" }}>
          <Space align="start">
            <Form.Item name="host" label="MySQL 地址" rules={[{ required: true }]}>
              <Input style={{ width: 160 }} />
            </Form.Item>
            <Form.Item name="port" label="端口" rules={[{ required: true }]}>
              <InputNumber min={1} max={65535} style={{ width: 110 }} />
            </Form.Item>
            <Form.Item name="db_name" label="数据库名" rules={[{ required: true }]}>
              <Input style={{ width: 180 }} />
            </Form.Item>
          </Space>
          <Form.Item name="username" label="MySQL 用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="MySQL 密码">
            <Input.Password />
          </Form.Item>
          <Button type="primary" loading={loading} onClick={submitDatabase}>
            检测并初始化数据库
          </Button>
        </Form>
      )}

      {status.db_configured && !status.alipay_configured && (
        <Form form={alipayForm} layout="vertical">
          <Alert
            type="info"
            showIcon
            message="支付宝沙箱配置（选填）：不配置则使用模拟支付"
            style={{ marginBottom: 16 }}
          />
          <Form.Item name="app_id" label="应用 ID">
            <Input />
          </Form.Item>
          <Form.Item name="private_key" label="应用私钥">
            <Input.TextArea rows={4} placeholder="单行 PEM 内容" />
          </Form.Item>
          <Form.Item name="public_key" label="支付宝公钥">
            <Input.TextArea rows={4} placeholder="单行 PEM 内容" />
          </Form.Item>
          <Form.Item name="notify_url" label="异步回调地址（选填，公网部署时填写）">
            <Input placeholder="https://your-domain/api/v1/payments/{trade_no}/callback" />
          </Form.Item>
          <Space>
            <Button type="primary" loading={loading} onClick={() => submitAlipay(false)}>
              保存并启用支付宝沙箱
            </Button>
            <Button loading={loading} onClick={() => submitAlipay(true)}>
              跳过，使用模拟支付
            </Button>
          </Space>
        </Form>
      )}

      {done && (
        <Result
          status="success"
          title="配置完成"
          subTitle="数据库与支付已就绪，可以开始使用"
          extra={
            <Button type="primary" onClick={() => navigate("/")}>
              进入系统
            </Button>
          }
        />
      )}
    </Card>
  );
}
