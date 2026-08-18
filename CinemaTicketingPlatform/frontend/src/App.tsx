import { useEffect, useState } from "react";
import { Link, Route, Routes, useNavigate } from "react-router-dom";
import { Button, Dropdown, Layout, Space, Typography } from "antd";
import { LogoutOutlined, ProfileOutlined, SettingOutlined, UserOutlined } from "@ant-design/icons";
import Home from "./pages/Home";
import Login from "./pages/Login";
import MovieDetail from "./pages/MovieDetail";
import Register from "./pages/Register";
import RequireAdmin from "./components/RequireAdmin";
import RequireAuth from "./components/RequireAuth";
import Setup from "./pages/Setup";
import SessionSeatPage from "./pages/SessionSeatPage";
import UserCenter from "./pages/UserCenter";
import AdminConsole from "./pages/admin/AdminConsole";
import { useAuth } from "./stores/auth";
import { get } from "./api/client";
import type { SetupStatus } from "./api/types";

const { Header, Content } = Layout;

export default function App() {
  const { user, fetchMe, logout } = useAuth();
  const navigate = useNavigate();
  const [, setSetupChecked] = useState(false);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  useEffect(() => {
    get<SetupStatus>("/setup/status")
      .then((s) => {
        if (!s.db_configured && window.location.pathname !== "/setup") {
          navigate("/setup", { replace: true });
        }
      })
      .catch(() => undefined)
      .finally(() => setSetupChecked(true));
  }, [navigate]);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Link to="/">
          <Typography.Title level={4} style={{ color: "#fff", margin: 0 }}>
            🎬 电影购票平台
          </Typography.Title>
        </Link>
        <Space>
          {user ? (
            <Dropdown
              menu={{
                items: [
                  { key: "me", icon: <ProfileOutlined />, label: "我的电影票" },
                  ...(user.role === "ADMIN"
                    ? [{ key: "admin", icon: <SettingOutlined />, label: "管理后台" }]
                    : []),
                  { type: "divider" },
                  { key: "logout", icon: <LogoutOutlined />, label: "退出登录" },
                ],
                onClick: ({ key }) => {
                  if (key === "me") navigate("/me");
                  if (key === "admin") navigate("/admin");
                  if (key === "logout") {
                    logout();
                    navigate("/");
                  }
                },
              }}
            >
              <Button type="text" icon={<UserOutlined />} style={{ color: "#fff" }}>
                {user.nickname || user.username}
              </Button>
            </Dropdown>
          ) : (
            <Space>
              <Link to="/login">
                <Button type="primary">登录</Button>
              </Link>
              <Link to="/register">
                <Button>注册</Button>
              </Link>
            </Space>
          )}
        </Space>
      </Header>
      <Content style={{ padding: 24, maxWidth: 1100, margin: "0 auto", width: "100%" }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/setup" element={<Setup />} />
          <Route path="/movies/:id" element={<MovieDetail />} />
          <Route
            path="/sessions/:sessionId"
            element={
              <RequireAuth>
                <SessionSeatPage />
              </RequireAuth>
            }
          />
          <Route
            path="/me"
            element={
              <RequireAuth>
                <UserCenter />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAdmin>
                <AdminConsole />
              </RequireAdmin>
            }
          />
        </Routes>
      </Content>
    </Layout>
  );
}
