import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Card, Tag, Spin, Empty } from "antd";
import {
  MessageOutlined, ThunderboltOutlined, BranchesOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
} from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import { api } from "../services";
import { tokens } from "../theme";

interface RunStep {
  id: string;
  sort_order: number;
  type: string;
  input_summary?: string;
  output_summary?: string;
  sql?: string;
  error?: string;
  duration_ms?: number;
  chart_config?: Record<string, unknown>;
}

interface RunItem {
  id: string;
  type: string;
  status: string;
  duration_ms?: number;
  token_estimate?: number;
  started_at: string;
  steps?: RunStep[];
}

const typeIcons: Record<string, React.ReactNode> = {
  chat: <MessageOutlined />,
  skill: <ThunderboltOutlined />,
  workflow: <BranchesOutlined />,
};

const typeLabels: Record<string, string> = {
  chat: "Chat Analysis",
  skill: "Skill Execution",
  workflow: "Workflow Run",
};

const stepLabels: Record<string, string> = {
  understand: "Understand",
  plan: "Plan",
  select_skill: "Select Skill",
  execute_skill: "Execute Skill",
  sql: "Generate SQL",
  execute: "Execute Query",
  analyze: "Analyze",
  visualize: "Visualize",
  compose: "Compose",
  insight: "Insight",
};

export default function RunHistoryPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRun, setExpandedRun] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<RunItem | null>(null);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    api
      .get(`/api/runs/${projectId}`)
      .then(({ data }) => setRuns(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  const loadDetail = (runId: string) => {
    if (expandedRun === runId) {
      setExpandedRun(null);
      setRunDetail(null);
      return;
    }
    setExpandedRun(runId);
    api.get(`/api/runs/detail/${runId}`).then(({ data }) => setRunDetail(data)).catch(() => {});
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%" }}>
      <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>Run History</h2>
      <p style={{ color: tokens.color.text.muted, fontSize: tokens.fontSize.base, marginTop: 4 }}>
        Every analysis run, fully traceable. Click to expand steps.
      </p>

      {runs.length === 0 ? (
        <Empty description="No runs yet. Start a chat analysis!" style={{ marginTop: 40 }}
          imageStyle={{ filter: "grayscale(0.5)" }} />
      ) : (
        <div style={{ marginTop: tokens.spacing.lg }}>
          {runs.map((run) => (
            <div key={run.id}>
              <Card
                size="small"
                style={{
                  background: tokens.color.bg.card,
                  border: `0.5px solid ${tokens.color.border.default}`,
                  borderRadius: tokens.radius.md,
                  marginBottom: 8,
                  cursor: "pointer",
                }}
                onClick={() => loadDetail(run.id)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 18, color: tokens.color.text.tertiary }}>
                    {typeIcons[run.type]}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div style={{ color: tokens.color.text.primary, fontWeight: 500 }}>
                      {typeLabels[run.type] || run.type}
                    </div>
                    <div style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted }}>
                      {run.started_at ? new Date(run.started_at).toLocaleString() : ""}
                    </div>
                  </div>
                  <Tag color={run.status === "done" ? "#2563EB" : run.status === "failed" ? "#dc2626" : "#d29922"}>
                    {run.status === "done" ? <CheckCircleOutlined /> : run.status === "failed" ? <CloseCircleOutlined /> : <ClockCircleOutlined />}
                    {" "}{run.status}
                  </Tag>
                  {run.duration_ms && (
                    <span style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted }}>
                      {(run.duration_ms / 1000).toFixed(1)}s
                    </span>
                  )}
                  {run.token_estimate && (
                    <span style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted }}>
                      ~{run.token_estimate} tk
                    </span>
                  )}
                </div>
              </Card>

              {expandedRun === run.id && runDetail && (
                <div style={{
                  background: tokens.color.bg.page,
                  borderRadius: tokens.radius.md,
                  padding: tokens.spacing.lg,
                  marginBottom: 12,
                  marginTop: -4,
                }}>
                  <div style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted, marginBottom: 8, textTransform: "uppercase" }}>
                    Agent Plan
                  </div>
                  {(runDetail.steps || []).map((step) => (
                    <div key={step.id} style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "6px 0", borderBottom: `0.5px solid ${tokens.color.border.default}`,
                    }}>
                      <span style={{
                        width: 20, height: 20, borderRadius: "50%", background: step.error ? "#dc2626" : "#2563EB",
                        color: "#fff", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center",
                      }}>
                        {step.sort_order}
                      </span>
                      <span style={{ color: tokens.color.text.primary, fontSize: tokens.fontSize.sm, minWidth: 100 }}>
                        {stepLabels[step.type] || step.type}
                      </span>
                      {step.duration_ms && (
                        <span style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted }}>
                          {(step.duration_ms / 1000).toFixed(2)}s
                        </span>
                      )}
                      {step.sql && (
                        <code style={{
                          fontSize: 16, color: tokens.color.text.tertiary,
                          background: "#1a1a1a", padding: "2px 6px", borderRadius: 4,
                          maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>
                          {step.sql}
                        </code>
                      )}
                      {step.error && (
                        <span style={{ fontSize: tokens.fontSize.xs, color: "#dc2626" }}>
                          {step.error.substring(0, 80)}
                        </span>
                      )}
                      {step.chart_config && (
                        <ReactECharts
                          option={step.chart_config as Record<string, unknown>}
                          style={{ height: 120, width: 200 }}
                          theme="dark"
                          notMerge
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
