import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Card, Tag, Modal, Input, Spin, Empty, message, Steps } from "antd";
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined, ClockCircleOutlined, FileDoneOutlined } from "@ant-design/icons";
import { api } from "../services";
import { tokens } from "../theme";

interface WorkflowItem {
  id: string;
  name: string;
  description: string;
  status: string;
  version: number;
  step_count: number;
  inputs?: {
    task?: {
      cadence?: string;
      compare_previous?: boolean;
      delivery?: string;
      scheduler_status?: string;
    };
  };
  last_run_at?: string;
}

const stepLabels: Record<string, string> = {
  sql: "SQL Query", skill: "Skill", analyze: "Analyze",
  visualize: "Visualize", insight: "Insight",
};

const cadenceLabels: Record<string, string> = {
  manual: "On demand",
  on_new_data: "When data changes",
  weekly: "Weekly",
  monthly: "Monthly",
};

const humanizeRunError = (detail: unknown) => {
  const text = typeof detail === "string" ? detail : "A workflow step failed";
  const normalized = text.toLowerCase();
  if (normalized.includes("authentication") || normalized.includes("401") || normalized.includes("api key")) {
    return "The analysis step could not use the model connection. Test the credentials in Advanced tools > Provider settings.";
  }
  if (normalized.includes("no available channel") || normalized.includes("503")) {
    return "The selected model is unavailable. Choose another model in Provider settings.";
  }
  if (normalized.includes("timeout")) return "The analysis step exceeded the model deadline.";
  return text.replace(/\s*\(request_id:[^)]+\)/gi, "");
};

export default function WorkflowPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModal, setCreateModal] = useState(false);
  const [runModal, setRunModal] = useState<string | null>(null);
  const [runSteps, setRunSteps] = useState<{ type: string; status: string; detail?: string }[]>([]);
  const [runStatus, setRunStatus] = useState<"running" | "complete" | "partial" | "error">("running");
  const [runError, setRunError] = useState("");
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const loadWorkflows = useCallback(() => {
    if (!projectId) return;
    api.get(`/api/workflows/${projectId}`)
      .then(({ data }) => setWorkflows(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => { loadWorkflows(); }, [loadWorkflows]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    await api.post("/api/workflows", { name: newName, description: newDesc, project_id: projectId });
    message.success("Workflow created");
    setCreateModal(false);
    setNewName("");
    setNewDesc("");
    loadWorkflows();
  };

  const handleDelete = async (id: string) => {
    await api.delete(`/api/workflows/${id}`);
    message.success("Deleted");
    loadWorkflows();
  };

  const handleRun = async (id: string) => {
    setRunModal(id);
    setRunSteps([]);
    setRunStatus("running");
    setRunError("");
    try {
      const resp = await fetch(`/api/workflows/${id}/run`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("nexa_token")}` },
      });
      if (!resp.ok) throw new Error(`Run request failed (${resp.status})`);
      const reader = resp.body?.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n"); buf = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const d = JSON.parse(line.slice(6));
            if (d.event === "step_start") {
              setRunSteps(prev => [...prev, { type: d.type, status: "process" }]);
            } else if (d.event === "step_done") {
              const detail = d.insight ? String(d.insight).slice(0, 120) : d.result?.row_count != null ? `${d.result.row_count} rows returned` : "Completed";
              setRunSteps(prev => prev.map((s, index) => index === prev.length - 1 ? { ...s, status: "finish", detail } : s));
            } else if (d.event === "step_error") {
              const detail = humanizeRunError(d.message);
              setRunSteps(prev => prev.map((s, index) => index === prev.length - 1 ? { ...s, status: "error", detail } : s));
              setRunError(detail);
            } else if (d.event === "workflow_done") {
              setRunStatus(d.status === "complete" ? "complete" : "partial");
              if (d.error) setRunError(humanizeRunError(d.error));
            }
          } catch {}
        }
      }
      setRunStatus((current) => current === "running" ? "complete" : current);
      loadWorkflows();
    } catch (error) {
      setRunStatus("error");
      setRunError(humanizeRunError(error instanceof Error ? error.message : "Run failed"));
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>Automations</h2>
          <p style={{ color: tokens.color.text.muted, fontSize: tokens.fontSize.base, margin: "4px 0 0" }}>
            Re-run proven analysis paths when new data arrives
          </p>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModal(true)}>
          New automation
        </Button>
      </div>

      {workflows.length === 0 ? (
        <Empty description="No repeatable tasks yet. Run an Agent task first, then save it as an automation." style={{ marginTop: 40 }} imageStyle={{ filter: "grayscale(0.5)" }} />
      ) : (
        <div style={{ marginTop: tokens.spacing.lg }}>
          {workflows.map((wf) => (
            <Card
              key={wf.id}
              size="small"
              style={{
                background: tokens.color.bg.card, borderRadius: tokens.radius.md,
                border: `0.5px solid ${tokens.color.border.default}`, marginBottom: 8,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ color: tokens.color.text.primary, fontWeight: 500 }}>{wf.name}</div>
                  <div style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted, display: "flex", gap: 12, flexWrap: "wrap", marginTop: 3 }}>
                    <span>{wf.step_count} steps · v{wf.version}</span>
                    <span><ClockCircleOutlined /> {cadenceLabels[wf.inputs?.task?.cadence || "manual"] || "On demand"}</span>
                    <span><FileDoneOutlined /> {wf.inputs?.task?.compare_previous ? "Compares prior run" : "Standalone result"}</span>
                    <span>{wf.last_run_at ? `Last run ${new Date(wf.last_run_at).toLocaleString()}` : "Not run yet"}</span>
                  </div>
                </div>
                <Tag color={wf.status === "active" ? "#2563EB" : wf.status === "draft" ? "#d29922" : "#666"}>
                  {wf.status}
                </Tag>
                <Button size="small" icon={<PlayCircleOutlined />} onClick={() => handleRun(wf.id)}>Run</Button>
                <Button size="small" icon={<EditOutlined />} onClick={() => navigate(`/project/${projectId}/workflow/${wf.id}`)} />
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(wf.id)} />
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal title="New automation" open={createModal} onOk={handleCreate} onCancel={() => setCreateModal(false)}>
        <Input placeholder="Name" value={newName} onChange={e => setNewName(e.target.value)} style={{ marginBottom: 8 }} />
        <Input.TextArea placeholder="Description" value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={2} />
      </Modal>

      <Modal title="Task run" open={!!runModal} footer={<Button onClick={() => setRunModal(null)} disabled={runStatus === "running"}>Close</Button>} onCancel={() => setRunModal(null)} closable={runStatus !== "running"}>
        <div style={{ padding: "10px 12px", marginBottom: 16, borderRadius: 6, background: runStatus === "complete" ? "#18261a" : runStatus === "running" ? "#1d2329" : "#2b1d1a", color: runStatus === "complete" ? "#8fc65a" : runStatus === "running" ? "#9db8d1" : "#f08a67" }}>
          {runStatus === "running" && "Running the saved analysis path..."}
          {runStatus === "complete" && "Run completed. Results and evidence are available in Audit."}
          {runStatus === "partial" && `Run stopped after a partial result. ${runError}`}
          {runStatus === "error" && `Run could not start. ${runError}`}
        </div>
        <Steps
          direction="vertical"
          size="small"
          current={runSteps.filter(s => s.status === "finish").length}
          items={runSteps.map((s) => ({
            title: stepLabels[s.type] || s.type,
            description: s.detail,
            status: (s.status === "finish" ? "finish" : s.status === "error" ? "error" : "process") as "finish" | "error" | "process",
          }))}
        />
      </Modal>
    </div>
  );
}
