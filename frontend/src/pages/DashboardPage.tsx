import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Card, Spin, Empty } from "antd";
import ReactECharts from "echarts-for-react";
import ReactMarkdown from "react-markdown";
import { api } from "../services";
import { tokens } from "../theme";

interface InsightItem {
  id: string;
  question: string;
  content: {
    summary?: string;
    sql?: string;
    charts?: Array<{
      title: string;
      type: string;
      options: Record<string, unknown>;
    }>;
    row_count?: number;
  };
  created_at: string;
}

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    api.get(`/api/insights/project/${projectId}`)
      .then(({ data }) => setInsights(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%" }}>
      <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>
        Dashboard
      </h2>
      <p style={{ color: tokens.color.text.muted, fontSize: tokens.fontSize.base, marginTop: 4 }}>
        Auto-generated from your saved insights
      </p>

      {insights.length === 0 ? (
        <Empty
          description={
            <span>
              No insights yet.<br />
              Start a chat analysis, then click <b>Save Insight</b> or <b>Generate Dashboard</b>.
            </span>
          }
          style={{ marginTop: 40 }}
        />
      ) : (
        <div style={{ marginTop: tokens.spacing.lg }}>
          {/* All charts in a grid */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))",
            gap: 16,
            marginBottom: 24,
          }}>
            {insights.flatMap((ins) =>
              (ins.content?.charts || []).map((chart, ci) => (
                <Card
                  key={`${ins.id}-${ci}`}
                  title={chart.title}
                  style={{
                    background: tokens.color.bg.card,
                    border: `0.5px solid ${tokens.color.border.default}`,
                    borderRadius: tokens.radius.md,
                  }}
                  styles={{ body: { padding: 12 } }}
                >
                  <ReactECharts
                    option={chart.options}
                    style={{ height: 260, width: "100%" }}
                    theme="dark"
                    notMerge
                  />
                </Card>
              ))
            )}
          </div>

          {/* Summary cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {insights.map((ins) => (
              <Card
                key={ins.id}
                size="small"
                style={{
                  background: tokens.color.bg.card,
                  border: `0.5px solid ${tokens.color.border.default}`,
                  borderRadius: tokens.radius.md,
                }}
              >
                <div style={{ fontWeight: 500, color: tokens.color.text.primary, marginBottom: 4 }}>
                  {ins.question}
                </div>
                {ins.content?.summary && (
                  <ReactMarkdown>
                    {typeof ins.content.summary === "string"
                      ? ins.content.summary
                      : JSON.stringify(ins.content.summary)}
                  </ReactMarkdown>
                )}
                <div style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted, marginTop: 4 }}>
                  {ins.created_at && `Saved ${new Date(ins.created_at).toLocaleString()}`}
                  {ins.content?.row_count !== undefined && ` · ${ins.content.row_count} rows`}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
