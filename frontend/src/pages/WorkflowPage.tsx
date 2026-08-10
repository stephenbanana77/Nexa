import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Card, Tag, Modal, Input, Spin, Empty, message, Steps } from "antd";
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { api } from "../services";
import { tokens } from "../theme";

interface WorkflowItem {
  id: string;
  name: string;
  description: string;
  status: string;
  version: number;
  step_count: number;
  last_run_at?: string;
}

const stepLabels: Record<string, string> = {
  sql: "SQL Query", skill: "Skill", analyze: "Analyze",
  visualize: "Visualize", insight: "Insight",
};

export default function WorkflowPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModal, setCreateModal] = useState(false);
  const [runModal, setRunModal] = useState<string | null>(null);
  const [runSteps, setRunSteps] = useState<{ type: string; status: string }[]>([]);
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
    try {
      const resp = await fetch(`/api/workflows/${id}/run`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("nexa_token")}` },
      });
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
              setRunSteps(prev => prev.map((s) => prev.length - 1 === prev.indexOf(s) ? { ...s, status: "finish" } : s));
            } else if (d.event === "error") {
              setRunSteps(prev => prev.map((s) => prev.length - 1 === prev.indexOf(s) ? { ...s, status: "error" } : s));
            }
          } catch {}
        }
      }
      message.success("Workflow finished");
    } catch {
      message.error("Run failed");
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>Workflows</h2>
          <p style={{ color: tokens.color.text.muted, fontSize: tokens.fontSize.base, margin: "4px 0 0" }}>
            Repeatable analysis pipelines
          </p>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModal(true)}>
          New Workflow
        </Button>
      </div>

      {workflows.length === 0 ? (
        <Empty description="No workflows yet" style={{ marginTop: 40 }} imageStyle={{ filter: "grayscale(0.5)" }} />
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
                  <div style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted }}>
                    {wf.step_count} steps · v{wf.version}
                    {wf.last_run_at ? ` · Last run: ${new Date(wf.last_run_at).toLocaleDateString()}` : " · Never run"}
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

      <Modal title="New Workflow" open={createModal} onOk={handleCreate} onCancel={() => setCreateModal(false)}>
        <Input placeholder="Name" value={newName} onChange={e => setNewName(e.target.value)} style={{ marginBottom: 8 }} />
        <Input.TextArea placeholder="Description" value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={2} />
      </Modal>

      <Modal title="Workflow Running" open={!!runModal} footer={null} onCancel={() => setRunModal(null)}>
        <Steps
          direction="vertical"
          size="small"
          current={runSteps.filter(s => s.status === "finish").length}
          items={runSteps.map((s) => ({
            title: stepLabels[s.type] || s.type,
            status: (s.status === "finish" ? "finish" : s.status === "error" ? "error" : "process") as "finish" | "error" | "process",
          }))}
        />
      </Modal>
    </div>
  );
}
