import { useEffect, type ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getToken } from "../api/client";
import { useAuth } from "../stores/auth";

export default function RequireAuth({ children }: { children: ReactElement }) {
  const { user, fetchMe } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (!user) fetchMe();
  }, [user, fetchMe]);

  if (!getToken()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}
