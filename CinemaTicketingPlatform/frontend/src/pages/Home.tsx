import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Col, Row, Typography } from "antd";
import { get } from "../api/client";
import type { Movie, Page } from "../api/types";

export default function Home() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    get<Page<Movie>>("/movies?page=1&page_size=12")
      .then((p) => setMovies(p.items))
      .catch((e) => console.error(e));
  }, []);

  return (
    <div>
      <Typography.Title level={3}>热映电影</Typography.Title>
      <Row gutter={[16, 16]}>
        {movies.map((m) => (
          <Col xs={24} sm={12} md={8} lg={6} key={m.id}>
            <Card
              title={m.title}
              extra={<Typography.Text type="secondary">{m.duration_min} 分钟</Typography.Text>}
              actions={[
                <Button type="link" key="detail" onClick={() => navigate(`/movies/${m.id}`)}>
                  查看场次
                </Button>,
              ]}
            >
              <Typography.Paragraph type="secondary" ellipsis={{ rows: 3 }}>
                {m.description ?? "暂无简介"}
              </Typography.Paragraph>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
