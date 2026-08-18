import { Button, Card, Form, Input, message } from "antd";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../stores/auth";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: { pathname: string } } };

  const onFinish = async (values: { username: string; password: string }) => {
    try {
      await login(values.username, values.password);
      message.success("登录成功");
      navigate(location.state?.from?.pathname ?? "/");
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  return (
    <Card title="登录" style={{ maxWidth: 420, margin: "40px auto" }}>
      <Form onFinish={onFinish} layout="vertical">
        <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
          <Input placeholder="用户名" />
        </Form.Item>
        <Form.Item name="password" label="密码" rules={[{ required: true }]}>
          <Input.Password placeholder="密码" />
        </Form.Item>
        <Button type="primary" htmlType="submit" block>
          登录
        </Button>
        <div style={{ marginTop: 12, textAlign: "center" }}>
          还没有账号？<Link to="/register">去注册</Link>
        </div>
      </Form>
    </Card>
  );
}
