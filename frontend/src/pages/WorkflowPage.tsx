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
  sql: "SQL 查询", skill: "技能", analyze: "分析",
  visualize: "可视化", insight: "生成洞察",
};

const cadenceLabels: Record<string, string> = {
  manual: "按需运行",
  on_new_data: "数据变化时",
  weekly: "每周",
  monthly: "每月",
};

const humanizeRunError = (detail: unknown) => {
  const text = typeof detail === "string" ? detail : "工作流步骤执行失败";
  const normalized = text.toLowerCase();
  if (normalized.includes("authentication") || normalized.includes("401") || normalized.includes("api key")) {
    return "分析步骤无法连接模型。请在「高级工具 > 模型设置」中测试凭据。";
  }
  if (normalized.includes("no available channel") || normalized.includes("503")) {
    return "所选模型当前不可用。请在「模型设置」中更换模型。";
  }
  if (normalized.includes("timeout")) return "分析步骤超过模型响应时限。";
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
    try {
      const { data } = await api.post("/api/workflows", { name: newName, description: newDesc, project_id: projectId });
      message.success("自动化草稿已创建，请配置运行步骤");
      setCreateModal(false);
      setNewName("");
      setNewDesc("");
      navigate(`/project/${projectId}/workflow/${data.id}`);
    } catch {
      message.error("自动化创建失败，请稍后重试");
    }
  };

  const handleDelete = async (id: string) => {
    await api.delete(`/api/workflows/${id}`);
    message.success("已删除");
    loadWorkflows();
  };

  const handleRun = async (id: string) => {
    const workflow = workflows.find((item) => item.id === id);
    if (!workflow?.step_count) {
      message.warning("请先配置至少一个运行步骤");
      navigate(`/project/${projectId}/workflow/${id}`);
      return;
    }
    setRunModal(id);
    setRunSteps([]);
    setRunStatus("running");
    setRunError("");
    try {
      const resp = await fetch(`/api/workflows/${id}/run`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("nexa_token")}` },
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        const detail = typeof body?.detail === "string" ? body.detail : "";
        throw new Error(detail.toLowerCase().includes("no steps") ? "请先配置至少一个运行步骤" : detail || `运行请求失败（${resp.status}）`);
      }
      const reader = resp.body?.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let finalStatus: "complete" | "partial" | null = null;
      let finalError = "";
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
              const detail = d.insight ? String(d.insight).slice(0, 120) : d.result?.row_count != null ? `返回 ${d.result.row_count} 行` : "已完成";
              setRunSteps(prev => prev.map((s, index) => index === prev.length - 1 ? { ...s, status: "finish", detail } : s));
            } else if (d.event === "step_error") {
              const detail = humanizeRunError(d.message);
              setRunSteps(prev => prev.map((s, index) => index === prev.length - 1 ? { ...s, status: "error", detail } : s));
              setRunError(detail);
            } else if (d.event === "workflow_done") {
              finalStatus = d.status === "complete" ? "complete" : "partial";
              finalError = d.error ? humanizeRunError(d.error) : "";
            }
          } catch {}
        }
      }
      if (finalStatus === "complete") {
        setRunStatus("complete");
      } else if (finalStatus === "partial") {
        setRunStatus("partial");
        setRunError(finalError);
      } else {
        setRunStatus("error");
        setRunError("运行结束，但没有收到明确的完成状态，请到「审计」中确认结果。");
      }
      loadWorkflows();
    } catch (error) {
      setRunStatus("error");
      setRunError(humanizeRunError(error instanceof Error ? error.message : "运行失败"));
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>自动化</h2>
          <p style={{ color: tokens.color.text.muted, fontSize: tokens.fontSize.base, margin: "4px 0 0" }}>
            新数据到达时，重复执行已经验证过的分析路径
          </p>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModal(true)}>
          新建自动化
        </Button>
      </div>

      {workflows.length === 0 ? (
        <Empty description="还没有可重复任务。请先运行一个 Agent 任务，再将它保存为自动化。" style={{ marginTop: 40 }} imageStyle={{ filter: "grayscale(0.5)" }} />
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
                    <span>{wf.step_count} 个步骤 · v{wf.version}</span>
                    <span><ClockCircleOutlined /> {cadenceLabels[wf.inputs?.task?.cadence || "manual"] || "按需运行"}</span>
                    <span><FileDoneOutlined /> {wf.inputs?.task?.compare_previous ? "与上次运行对比" : "独立结果"}</span>
                    <span>{wf.last_run_at ? `上次运行：${new Date(wf.last_run_at).toLocaleString("zh-CN")}` : "尚未运行"}</span>
                  </div>
                </div>
                <Tag color={!wf.step_count ? "#d29922" : wf.status === "active" ? "#2563EB" : wf.status === "draft" ? "#d29922" : "#666"}>
                  {!wf.step_count ? "未配置" : wf.status === "active" ? "已启用" : wf.status === "draft" ? "草稿" : wf.status}
                </Tag>
                {wf.step_count > 0 ? (
                  <>
                    <Button size="small" icon={<PlayCircleOutlined />} onClick={() => handleRun(wf.id)}>运行</Button>
                    <Button size="small" icon={<EditOutlined />} onClick={() => navigate(`/project/${projectId}/workflow/${wf.id}`)} aria-label="编辑自动化" title="编辑自动化" />
                  </>
                ) : (
                  <Button size="small" type="primary" icon={<EditOutlined />} onClick={() => navigate(`/project/${projectId}/workflow/${wf.id}`)}>配置流程</Button>
                )}
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(wf.id)} aria-label="删除自动化" title="删除自动化" />
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal title="新建自动化" open={createModal} onOk={handleCreate} onCancel={() => setCreateModal(false)} okText="创建并配置">
        <p style={{ color: tokens.color.text.muted, marginTop: 0 }}>
          先创建草稿，下一步配置数据查询、分析和交付步骤。未配置步骤的自动化不能运行。
        </p>
        <Input placeholder="名称" value={newName} onChange={e => setNewName(e.target.value)} style={{ marginBottom: 8 }} />
        <Input.TextArea placeholder="描述" value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={2} />
      </Modal>

      <Modal title="任务运行" open={!!runModal} footer={<Button onClick={() => setRunModal(null)} disabled={runStatus === "running"}>关闭</Button>} onCancel={() => setRunModal(null)} closable={runStatus !== "running"}>
        <div style={{ padding: "10px 12px", marginBottom: 16, borderRadius: 6, background: runStatus === "complete" ? "#18261a" : runStatus === "running" ? "#1d2329" : "#2b1d1a", color: runStatus === "complete" ? "#8fc65a" : runStatus === "running" ? "#9db8d1" : "#f08a67" }}>
          {runStatus === "running" && "正在执行已保存的分析路径..."}
          {runStatus === "complete" && "运行完成，可在「审计」中查看结果和证据。"}
          {runStatus === "partial" && `运行在产生部分结果后停止。${runError}`}
          {runStatus === "error" && `运行无法启动。${runError}`}
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
