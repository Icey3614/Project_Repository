import { Button, Card, Form, Input, message } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../stores/auth";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values: { username: string; password: string; nickname?: string }) => {
    try {
      await register(values.username, values.password, values.nickname);
      message.success("注册成功，请登录");
      navigate("/login");
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  return (
    <Card title="注册" style={{ maxWidth: 420, margin: "40px auto" }}>
      <Form onFinish={onFinish} layout="vertical">
        <Form.Item
          name="username"
          label="用户名"
          rules={[
            { required: true },
            { pattern: /^[a-zA-Z0-9_]+$/, message: "仅支持字母、数字、下划线" },
          ]}
        >
          <Input placeholder="3-50 位字母数字下划线" />
        </Form.Item>
        <Form.Item name="nickname" label="昵称">
          <Input placeholder="选填" />
        </Form.Item>
        <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
          <Input.Password placeholder="至少 6 位" />
        </Form.Item>
        <Button type="primary" htmlType="submit" block>
          注册
        </Button>
        <div style={{ marginTop: 12, textAlign: "center" }}>
          已有账号？<Link to="/login">去登录</Link>
        </div>
      </Form>
    </Card>
  );
}
