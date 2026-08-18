import { useEffect, type ReactElement } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Button, Result, Spin } from "antd";
import { getToken } from "../api/client";
import { useAuth } from "../stores/auth";

export default function RequireAdmin({ children }: { children: ReactElement }) {
  const { user, fetchMe } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) fetchMe();
  }, [user, fetchMe]);

  if (!getToken()) return <Navigate to="/login" replace />;
  if (!user) {
    return (
      <div style={{ textAlign: "center", padding: 60 }}>
        <Spin />
      </div>
    );
  }
  if (user.role !== "ADMIN") {
    return (
      <Result
        status="403"
        title="403"
        subTitle="需要管理员权限"
        extra={
          <Button type="primary" onClick={() => navigate("/")}>
            返回首页
          </Button>
        }
      />
    );
  }
  return children;
}
