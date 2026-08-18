import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Card, Descriptions, Empty, Space, Tag, Typography } from "antd";
import dayjs from "dayjs";
import { get } from "../api/client";
import type { Movie, Page, SessionItem } from "../api/types";

const STATUS_TAG: Record<string, { text: string; color: string }> = {
  SCHEDULED: { text: "未开售", color: "default" },
  SELLING: { text: "售票中", color: "green" },
  SOLD_OUT: { text: "已售罄", color: "red" },
  STOPPED: { text: "已停售", color: "orange" },
  ENDED: { text: "已结束", color: "default" },
};

export default function MovieDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [movie, setMovie] = useState<Movie | null>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);

  useEffect(() => {
    Promise.all([
      get<Movie>(`/movies/${id}`),
      get<Page<SessionItem>>(`/sessions?movie_id=${id}&page_size=50`),
    ])
      .then(([m, p]) => {
        setMovie(m);
        setSessions(p.items);
      })
      .catch((e) => console.error(e));
  }, [id]);

  const grouped = useMemo(() => {
    const map = new Map<string, SessionItem[]>();
    for (const s of sessions) {
      const key = dayjs(s.start_at).format("YYYY-MM-DD");
      map.set(key, [...(map.get(key) ?? []), s]);
    }
    return [...map.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1));
  }, [sessions]);

  if (!movie) return null;

  return (
    <div>
      <Typography.Title level={3}>{movie.title}</Typography.Title>
      <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="时长">{movie.duration_min} 分钟</Descriptions.Item>
        <Descriptions.Item label="简介">{movie.description ?? "暂无"}</Descriptions.Item>
      </Descriptions>
      <Typography.Title level={4}>场次安排</Typography.Title>
      {grouped.length === 0 && <Empty description="暂无场次" />}
      {grouped.map(([date, items]) => (
        <Card key={date} title={date} style={{ marginBottom: 12 }}>
          <Space direction="vertical" style={{ width: "100%" }}>
            {items.map((s) => {
              const tag = STATUS_TAG[s.status] ?? { text: s.status, color: "default" };
              const selling = s.status === "SELLING";
              return (
                <div
                  key={s.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "8px 0",
                    borderBottom: "1px solid #f0f0f0",
                  }}
                >
                  <Space>
                    <span>{dayjs(s.start_at).format("HH:mm")} - {dayjs(s.end_at).format("HH:mm")}</span>
                    <span>{s.venue_name}</span>
                    <span>¥{s.base_price}</span>
                    <span>余票 {s.remaining}/{s.total_seats}</span>
                    <Tag color={tag.color}>{tag.text}</Tag>
                  </Space>
                  <Button
                    type="primary"
                    disabled={!selling}
                    onClick={() => navigate(`/sessions/${s.id}`)}
                  >
                    选座购票
                  </Button>
                </div>
              );
            })}
          </Space>
        </Card>
      ))}
    </div>
  );
}
