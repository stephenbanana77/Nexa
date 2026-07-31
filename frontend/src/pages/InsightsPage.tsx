import { useEffect, useState } from "react";
import { Card, message } from "antd";
import { BulbOutlined } from "@ant-design/icons";
import api from "../api/client";

interface Insight {
  id: string;
  question: string;
  content: {
    summary?: string;
    sql?: string;
    row_count?: number;
  };
  created_at: string;
}

export default function InsightsPage({ projectId }: { projectId: string }) {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.get(`/api/insights/project/${projectId}`)
      .then(({ data }) => setInsights(data))
      .catch(() => message.error("Failed to load insights"));
  }, [projectId]);

  if (insights.length === 0) {
    return (
      <div style={{ padding: "60px 20px", textAlign: "center" }}>
        <BulbOutlined style={{ fontSize: 36, color: "#444" }} />
        <p style={{ color: "#888", marginTop: 12, fontSize: 14 }}>No insights yet</p>
        <p style={{ color: "#666", fontSize: 13 }}>Ask a question in Chat, then save the result here</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "16px 0", display: "grid", gap: 12 }}>
      {insights.map((insight) => (
        <Card
          key={insight.id}
          onClick={() => setExpanded(expanded === insight.id ? null : insight.id)}
          hoverable
          style={{ background: "#1a1a1a", border: "1px solid #333", cursor: "pointer" }}
          styles={{ body: { padding: 16 } }}
        >
          <div style={{ fontWeight: 500, color: "#ddd", fontSize: 14, marginBottom: 4 }}>
            {insight.question}
          </div>
          <div style={{ color: "#aaa", fontSize: 12, lineHeight: 1.5, marginBottom: 8 }}>
            {insight.content.summary?.slice(0, 150)}...
          </div>
          <div style={{ fontSize: 11, color: "#666" }}>
            {new Date(insight.created_at).toLocaleString()}
            {insight.content.row_count && ` · ${insight.content.row_count} rows`}
          </div>
          {expanded === insight.id && insight.content.sql && (
            <pre style={{
              marginTop: 12,
              background: "#0d0d0d",
              padding: 10,
              borderRadius: 6,
              fontSize: 12,
              color: "#60a5fa",
              overflow: "auto",
            }}>
              {insight.content.sql}
            </pre>
          )}
        </Card>
      ))}
    </div>
  );
}
