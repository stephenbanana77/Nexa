import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Card, Empty, Spin, Tag, Table } from "antd";
import {
  BranchesOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  MessageOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import { api } from "../services";
import { tokens } from "../theme";

interface RunLineage {
  question?: string;
  question_sanitized?: boolean;
  latest_sql?: string;
  final_sql?: string;
  sql_attempts?: { attempt: number; sql?: string }[];
  errors?: { attempt?: number; message: string }[];
  sql_retries?: { attempt?: number; error?: string; next_action?: string }[];
  system_retries?: { attempt?: number; message?: string; will_retry?: boolean }[];
  schema?: {
    text?: string;
    sha256?: string;
    length?: number;
    source?: string;
  };
  result?: {
    columns?: string[];
    row_count?: number;
    sample_rows?: unknown[][];
  };
  answer?: {
    summary?: string;
    preview?: string;
  };
  policy_decision?: SQLPolicyDecision;
}

interface SQLPolicyDecision {
  is_safe: boolean;
  final_sql?: string;
  reason?: string;
  operation?: string;
  auto_limit_added?: boolean;
  max_rows?: number;
  timeout_sec?: number;
  risk_flags?: string[];
}

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
  lineage?: RunLineage | null;
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
        Every analysis run, with evidence for the question, SQL, result, and answer.
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
                role="button"
                tabIndex={0}
                aria-expanded={expandedRun === run.id}
                style={{
                  background: tokens.color.bg.card,
                  border: `0.5px solid ${tokens.color.border.default}`,
                  borderRadius: tokens.radius.md,
                  marginBottom: 8,
                  cursor: "pointer",
                }}
                onClick={() => loadDetail(run.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    loadDetail(run.id);
                  }
                }}
              >
                <RunSummary run={run} />
              </Card>

              {expandedRun === run.id && runDetail && (
                <div style={{
                  background: tokens.color.bg.page,
                  borderRadius: tokens.radius.md,
                  padding: tokens.spacing.lg,
                  marginBottom: 12,
                  marginTop: -4,
                  border: `0.5px solid ${tokens.color.border.light}`,
                }}>
                  <LineagePanel lineage={runDetail.lineage} />
                  <StepTimeline steps={runDetail.steps || []} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RunSummary({ run }: { run: RunItem }) {
  const lineage = run.lineage || {};
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <span style={{ fontSize: 18, color: tokens.color.text.tertiary }}>
        {typeIcons[run.type]}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: tokens.color.text.primary, fontWeight: 500 }}>
          {typeLabels[run.type] || run.type}
        </div>
        <div style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {lineage.question || (run.started_at ? new Date(run.started_at).toLocaleString() : "")}
        </div>
      </div>
      {lineage.final_sql && (
        <Tag color="#1e3a5f" icon={<SafetyCertificateOutlined />}>
          lineage
        </Tag>
      )}
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
  );
}

function LineagePanel({ lineage }: { lineage?: RunLineage | null }) {
  if (!lineage || Object.keys(lineage).length === 0) {
    return (
      <section style={{ marginBottom: tokens.spacing.lg }}>
        <SectionLabel>Evidence Chain</SectionLabel>
        <div style={{ color: tokens.color.text.muted, fontSize: tokens.fontSize.xs }}>
          No lineage was recorded for this run.
        </div>
      </section>
    );
  }

  return (
    <section style={{ marginBottom: tokens.spacing.xl }}>
      <SectionLabel>Evidence Chain</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: tokens.spacing.sm }}>
        <EvidenceField label="Question" value={lineage.question || "Unknown"} />
        <EvidenceField label="Schema source" value={lineage.schema?.source || "Unknown"} />
        <EvidenceField label="Schema hash" value={lineage.schema?.sha256?.slice(0, 12) || "None"} mono />
        <EvidenceField label="Rows returned" value={String(lineage.result?.row_count ?? "Unknown")} />
        <EvidenceField label="SQL attempts" value={String(lineage.sql_attempts?.length || 0)} />
        <EvidenceField label="SQL retries" value={String(lineage.sql_retries?.length || 0)} />
        <EvidenceField label="System retries" value={String(lineage.system_retries?.length || 0)} />
        <EvidenceField label="Policy" value={lineage.policy_decision?.is_safe ? "Allowed" : lineage.policy_decision ? "Blocked" : "Unknown"} />
        <EvidenceField label="Timeout" value={lineage.policy_decision?.timeout_sec ? `${lineage.policy_decision.timeout_sec}s` : "Unknown"} />
      </div>

      {lineage.policy_decision && (
        <div style={{ marginTop: tokens.spacing.md, display: "flex", gap: tokens.spacing.sm, flexWrap: "wrap" }}>
          {lineage.policy_decision.auto_limit_added && <Tag color="#1e3a5f">LIMIT added</Tag>}
          {(lineage.policy_decision.risk_flags || []).map((flag) => (
            <Tag key={flag} color={flag === "select_star" ? "#d29922" : "#444"}>
              {flag.replaceAll("_", " ")}
            </Tag>
          ))}
          {lineage.policy_decision.reason && <Tag color="#dc2626">{lineage.policy_decision.reason}</Tag>}
        </div>
      )}

      {lineage.final_sql && (
        <div style={{ marginTop: tokens.spacing.md }}>
          <SmallLabel>Final SQL</SmallLabel>
          <CodeBlock>{lineage.final_sql}</CodeBlock>
        </div>
      )}

      {(lineage.sql_attempts?.length || 0) > 1 && (
        <div style={{ marginTop: tokens.spacing.md }}>
          <SmallLabel>SQL Attempts</SmallLabel>
          {lineage.sql_attempts?.map((attempt) => (
            <CodeBlock key={attempt.attempt}>{`#${attempt.attempt} ${attempt.sql || ""}`}</CodeBlock>
          ))}
        </div>
      )}

      {(lineage.errors?.length || 0) > 0 && (
        <div style={{ marginTop: tokens.spacing.md }}>
          <SmallLabel>Errors / Retries</SmallLabel>
          {lineage.errors?.map((error, index) => (
            <div key={`${error.attempt || 0}-${index}`} style={{ color: "#f87171", fontSize: tokens.fontSize.xs, marginTop: 4 }}>
              Attempt {error.attempt || index + 1}: {error.message}
            </div>
          ))}
        </div>
      )}

      {(lineage.sql_retries?.length || 0) > 0 && (
        <RetryList
          title="SQL Retries"
          items={lineage.sql_retries?.map((retry) => ({
            key: `sql-${retry.attempt}`,
            text: `Attempt ${retry.attempt || "?"}: ${retry.error || "SQL failed"} -> ${retry.next_action || "retry"}`,
          })) || []}
        />
      )}

      {(lineage.system_retries?.length || 0) > 0 && (
        <RetryList
          title="System Retries"
          items={lineage.system_retries?.map((retry) => ({
            key: `system-${retry.attempt}`,
            text: `Attempt ${retry.attempt || "?"}: ${retry.message || "System error"}${retry.will_retry ? " -> retrying" : ""}`,
          })) || []}
        />
      )}

      {(lineage.result?.sample_rows?.length || 0) > 0 && (
        <div style={{ marginTop: tokens.spacing.md }}>
          <SmallLabel>Sample Result</SmallLabel>
          <Table
            size="small"
            pagination={false}
            rowKey="_key"
            scroll={{ x: "max-content" }}
            dataSource={toTableRows(lineage.result?.columns || [], lineage.result?.sample_rows || [])}
            columns={(lineage.result?.columns || []).map((column) => ({
              title: column,
              dataIndex: column,
              key: column,
              ellipsis: true,
            }))}
          />
        </div>
      )}

      {lineage.answer?.summary && (
        <div style={{ marginTop: tokens.spacing.md }}>
          <SmallLabel>Answer Summary</SmallLabel>
          <div style={{ color: tokens.color.text.secondary, fontSize: tokens.fontSize.xs, lineHeight: 1.6 }}>
            {lineage.answer.summary}
          </div>
        </div>
      )}
    </section>
  );
}

function StepTimeline({ steps }: { steps: RunStep[] }) {
  return (
    <section>
      <SectionLabel>Agent Plan</SectionLabel>
      {steps.map((step) => (
        <div key={step.id} style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "6px 0",
          borderBottom: `0.5px solid ${tokens.color.border.default}`,
        }}>
          <span style={{
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: step.error ? "#dc2626" : "#2563EB",
            color: "#fff",
            fontSize: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: "0 0 auto",
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
          {step.sql && <InlineCode>{step.sql}</InlineCode>}
          {step.error && (
            <span style={{ fontSize: tokens.fontSize.xs, color: "#dc2626" }}>
              {step.error.substring(0, 80)}
            </span>
          )}
          {step.chart_config && (
            <ReactECharts
              option={step.chart_config}
              style={{ height: 120, width: 200 }}
              theme="dark"
              notMerge
            />
          )}
        </div>
      ))}
    </section>
  );
}

function RetryList({ title, items }: { title: string; items: { key: string; text: string }[] }) {
  return (
    <div style={{ marginTop: tokens.spacing.md }}>
      <SmallLabel>{title}</SmallLabel>
      {items.map((item) => (
        <div key={item.key} style={{ color: tokens.color.text.secondary, fontSize: tokens.fontSize.xs, marginTop: 4 }}>
          {item.text}
        </div>
      ))}
    </div>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted, marginBottom: 8, textTransform: "uppercase" }}>
      {children}
    </div>
  );
}

function SmallLabel({ children }: { children: string }) {
  return (
    <div style={{ fontSize: tokens.fontSize.caption, color: tokens.color.text.muted, marginBottom: 4 }}>
      {children}
    </div>
  );
}

function EvidenceField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ background: tokens.color.bg.card, border: `0.5px solid ${tokens.color.border.light}`, borderRadius: tokens.radius.md, padding: tokens.spacing.md }}>
      <div style={{ color: tokens.color.text.muted, fontSize: tokens.fontSize.caption, marginBottom: 4 }}>{label}</div>
      <div style={{ color: tokens.color.text.primary, fontSize: tokens.fontSize.xs, fontFamily: mono ? "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" : undefined, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {value}
      </div>
    </div>
  );
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre style={{
      margin: "4px 0 0",
      background: tokens.color.bg.code,
      color: tokens.color.accent.blueLight,
      border: `0.5px solid ${tokens.color.border.light}`,
      borderRadius: tokens.radius.md,
      padding: tokens.spacing.md,
      fontSize: tokens.fontSize.xs,
      overflow: "auto",
      whiteSpace: "pre-wrap",
    }}>
      {children}
    </pre>
  );
}

function InlineCode({ children }: { children: string }) {
  return (
    <code style={{
      fontSize: 16,
      color: tokens.color.text.tertiary,
      background: tokens.color.bg.card,
      padding: "2px 6px",
      borderRadius: 4,
      maxWidth: 400,
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap",
    }}>
      {children}
    </code>
  );
}

function toTableRows(columns: string[], rows: unknown[][]) {
  return rows.map((row, rowIndex) => {
    const item: Record<string, unknown> = { _key: rowIndex };
    columns.forEach((column, columnIndex) => {
      item[column] = row[columnIndex];
    });
    return item;
  });
}
