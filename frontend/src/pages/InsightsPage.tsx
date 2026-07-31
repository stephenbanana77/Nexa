import { useEffect, useState } from "react";
import { Card, Button, Popconfirm, Pagination, message } from "antd";
import { BulbOutlined, DeleteOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import ReactECharts from "echarts-for-react";
import api from "../api/client";

interface ChartConfig {
  type: "bar" | "line" | "pie" | "scatter";
  title: string;
  options: Record<string, any>;
}

interface Insight {
  id: string;
  question: string;
  content: {
    summary?: string;
    sql?: string;
    row_count?: number;
    charts?: ChartConfig[];
    key_findings?: string[];
    tables?: { columns: string[]; rows: any[][] }[];
  };
  created_at: string;
}

const PAGE_SIZE = 6;

export default function InsightsPage({ projectId }: { projectId: string }) {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.get(`/api/insights/project/${projectId}`)
      .then(({ data }) => setInsights(data))
      .catch(() => message.error("Failed to load insights"));
  }, [projectId]);

  const handleDelete = async (insightId: string) => {
    setDeleting(true);
    try {
      await api.delete(`/api/insights/${insightId}`);
      setInsights((prev) => prev.filter((i) => i.id !== insightId));
      if (expanded === insightId) setExpanded(null);
      message.success("Insight deleted");
    } catch {
      message.error("Failed to delete insight");
    } finally {
      setDeleting(false);
    }
  };

  // reset page when insights change
  const totalPages = Math.max(1, Math.ceil(insights.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginatedInsights = insights.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

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
      {paginatedInsights.map((insight) => (
        <Card
          key={insight.id}
          hoverable
          style={{ background: "#1a1a1a", border: "1px solid #333" }}
          styles={{ body: { padding: 16 } }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div
              style={{ flex: 1, cursor: "pointer" }}
              onClick={() => setExpanded(expanded === insight.id ? null : insight.id)}
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
            </div>
            <Popconfirm
              title="Delete this insight?"
              onConfirm={() => handleDelete(insight.id)}
              okText="Delete"
              cancelText="Cancel"
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                loading={deleting && expanded === insight.id}
              />
            </Popconfirm>
          </div>

          {expanded === insight.id && (
            <div style={{ marginTop: 12, borderTop: "1px solid #333", paddingTop: 12 }}>
              {/* Full summary with Markdown */}
              <ReactMarkdown>{insight.content.summary || ""}</ReactMarkdown>

              {/* Key findings */}
              {insight.content.key_findings && insight.content.key_findings.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ color: "#aaa", fontSize: 11, marginBottom: 6, textTransform: "uppercase" }}>
                    Key Findings
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 18, color: "#ccc", fontSize: 13, lineHeight: 1.7 }}>
                    {insight.content.key_findings.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* SQL */}
              {insight.content.sql && (
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

              {/* ECharts charts */}
              {insight.content.charts && insight.content.charts.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  {insight.content.charts.map((chart, ci) => (
                    <div key={ci} style={{ marginBottom: 16 }}>
                      <div style={{ color: "#aaa", fontSize: 11, marginBottom: 6, textTransform: "uppercase" }}>
                        {chart.title}
                      </div>
                      <ReactECharts
                        option={chart.options}
                        style={{ height: 260, width: "100%" }}
                        theme="dark"
                        notMerge
                      />
                    </div>
                  ))}
                </div>
              )}

              {/* Tables */}
              {insight.content.tables && insight.content.tables.length > 0 && insight.content.tables.map((table, ti) => (
                <div key={ti} style={{ marginTop: 12, overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                    <thead>
                      <tr>
                        {table.columns.map((col: string) => (
                          <th key={col} style={{ padding: "4px 10px", borderBottom: "1px solid #333", textAlign: "left", color: "#888" }}>
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {table.rows.slice(0, 15).map((row: any[], ri: number) => (
                        <tr key={ri}>
                          {row.map((val: any, ci: number) => (
                            <td key={ci} style={{ padding: "3px 10px", borderBottom: "0.5px solid #222", color: "#ccc" }}>
                              {String(val)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </Card>
      ))}

      {insights.length > PAGE_SIZE && (
        <div style={{ display: "flex", justifyContent: "center", marginTop: 8 }}>
          <Pagination
            current={safePage}
            total={insights.length}
            pageSize={PAGE_SIZE}
            onChange={(p) => setPage(p)}
            size="small"
          />
        </div>
      )}
    </div>
  );
}
