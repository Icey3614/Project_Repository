import { Tabs } from "antd";
import AdminCheckin from "./AdminCheckin";
import AdminMovies from "./AdminMovies";
import AdminRefunds from "./AdminRefunds";
import AdminSessions from "./AdminSessions";
import AdminVenues from "./AdminVenues";

export default function AdminConsole() {
  return (
    <Tabs
      items={[
        { key: "movies", label: "电影管理", children: <AdminMovies /> },
        { key: "venues", label: "场馆管理", children: <AdminVenues /> },
        { key: "sessions", label: "排片管理", children: <AdminSessions /> },
        { key: "refunds", label: "退款审核", children: <AdminRefunds /> },
        { key: "checkin", label: "核销", children: <AdminCheckin /> },
      ]}
    />
  );
}
