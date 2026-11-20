import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Alert, Button, Input, Spin, Card, Tag, message, Popconfirm, Select, Tooltip } from "antd";
import { SaveOutlined, PlayCircleOutlined, ArrowLeftOutlined, PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { api } from "../services";
import { tokens } from "../theme";

interface Step {
  id?: string;
  type: string;
  sort_order: number;
  config: Record<string, any>;
  input_refs?: string[];
  output_ref?: string;
  description: string;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  project_id: string;
  status: string;
  inputs?: { dataset_ids?: string[] };
  steps: Step[];
}

interface DatasetOption {
  id: string;
  name: string;
  row_count: number;
}

const stepTypeOptions = [
  { value: "sql", label: "SQL", color: "blue" },
  { value: "analyze", label: "分析", color: "orange" },
  { value: "insight", label: "洞察", color: "purple" },
  { value: "visualize", label: "可视化", color: "green" },
  { value: "skill", label: "技能", color: "cyan" },
];

export default function WorkflowEditPage() {
  const { projectId, workflowId } = useParams<{ projectId: string; workflowId: string }>();
  const navigate = useNavigate();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [name, setName] = useState("");
  const [description, setDesc] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const [datasetIds, setDatasetIds] = useState<string[]>([]);
  const [initialState, setInitialState] = useState<{ name: string; desc: string; stepsJson: string; datasetsJson: string } | null>(null);

  const isDirty = initialState
    ? name !== initialState.name || description !== initialState.desc || JSON.stringify(steps) !== initialState.stepsJson
      || JSON.stringify(datasetIds) !== initialState.datasetsJson
    : false;

  useEffect(() => {
    if (!workflowId) return;
    api.get(`/api/workflows/detail/${workflowId}`)
      .then(({ data }) => {
        setWorkflow(data);
        setName(data.name);
        setDesc(data.description || "");
        setSteps(data.steps || []);
        const boundDatasets = data.inputs?.dataset_ids || [];
        setDatasetIds(boundDatasets);
        setInitialState({
          name: data.name,
          desc: data.description || "",
          stepsJson: JSON.stringify(data.steps || []),
          datasetsJson: JSON.stringify(boundDatasets),
        });
      })
      .catch(() => message.error("工作流加载失败，请稍后重试"))
      .finally(() => setLoading(false));
  }, [workflowId]);

  useEffect(() => {
    if (!projectId) return;
    api.get(`/api/datasets?project_id=${projectId}`)
      .then(({ data }) => setDatasets(Array.isArray(data) ? data : []))
      .catch(() => message.error("数据集列表加载失败"));
  }, [projectId]);

  const addStep = (type: string) => {
    const defaults: Record<string, any> = {
      sql: { sql_template: "SELECT * FROM data LIMIT 10" },
      analyze: { prompt: "分析查询结果。" },
      insight: { prompt: "基于分析结果提供业务洞察。" },
      visualize: { chart_type: "auto" },
      skill: { skill_name: "" },
    };
    const config = defaults[type] || {};
    setSteps((prev) => [...prev, { type, sort_order: prev.length, config: { ...config }, description: "" }]);
  };

  const updateStepConfig = (idx: number, key: string, value: string) => {
    setSteps((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], config: { ...next[idx].config, [key]: value } };
      return next;
    });
  };

  const removeStep = (idx: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== idx).map((s, i) => ({ ...s, sort_order: i })));
  };

  const handleSave = async () => {
    if (!workflowId) return;
    setSaving(true);
    try {
      await api.put(`/api/workflows/${workflowId}`, {
        name, description,
        inputs: { dataset_ids: datasetIds },
        steps: steps.map((s, i) => ({ ...s, sort_order: i })),
      });
      setInitialState({
        name,
        desc: description,
        stepsJson: JSON.stringify(steps),
        datasetsJson: JSON.stringify(datasetIds),
      });
      message.success("工作流已保存");
    } catch {
      message.error("保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    if (!workflowId) return;
    if (steps.length === 0) {
      message.warning("请先添加并保存至少一个运行步骤");
      return;
    }
    if (datasetIds.length === 0) {
      message.warning("请先选择并保存这个自动化使用的数据集");
      return;
    }
    if (isDirty) {
      message.warning("流程有未保存的修改，请保存后再运行");
      return;
    }
    setRunning(true);
    try {
      const response = await fetch(`/api/workflows/${workflowId}/run`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("nexa_token")}` },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = typeof body?.detail === "string" ? body.detail : "";
        throw new Error(detail.toLowerCase().includes("no steps") ? "请先配置至少一个运行步骤" : detail || `运行请求失败（${response.status}）`);
      }
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalStatus: string | null = null;
      let finalError = "";
      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.event === "workflow_done") {
              finalStatus = event.status;
              finalError = event.error || "";
            }
          } catch {}
        }
      }
      if (finalStatus === "complete") message.success("任务运行完成，请在「审计」中查看证据");
      else if (finalStatus) message.error(`任务产生部分结果后停止${finalError ? `：${finalError}` : ""}`);
      else message.error("运行结束，但没有收到明确的完成状态，请到「审计」中确认结果");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "运行失败，请稍后重试");
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;
  if (!workflow) return <div style={{ padding: 40, textAlign: "center" }}>未找到工作流</div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%", maxWidth: 800 }}>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/project/${projectId}?tab=workflows`)}
        style={{ color: "#888", marginBottom: 16 }}>
        返回自动化列表
      </Button>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <Input
          size="large"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ fontSize: 20, fontWeight: 600, color: tokens.color.text.primary,
            background: "transparent", border: "none", padding: 0, maxWidth: 400 }}
          placeholder="工作流名称"
        />
        <div style={{ display: "flex", gap: 8 }}>
          <Tooltip title={steps.length === 0 ? "请先添加并保存至少一个步骤" : datasetIds.length === 0 ? "请先选择数据集" : isDirty ? "请先保存流程修改" : "运行自动化"}>
            <span>
              <Button icon={<PlayCircleOutlined />} onClick={handleRun} loading={running} disabled={steps.length === 0 || datasetIds.length === 0 || isDirty}>运行</Button>
            </span>
          </Tooltip>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}
            danger={isDirty}
          >{isDirty ? "保存*" : "保存"}</Button>
        </div>
      </div>
      <Input.TextArea
        value={description}
        onChange={(e) => setDesc(e.target.value)}
        style={{ color: "#888", background: "transparent", border: "none", resize: "none", padding: 0, marginBottom: 24 }}
        placeholder="描述（可选）"
        autoSize
      />

      <div style={{ marginBottom: 16 }}>
        <div style={{ color: tokens.color.text.tertiary, marginBottom: 6 }}>运行数据集</div>
        <Select
          mode="multiple"
          value={datasetIds}
          onChange={setDatasetIds}
          placeholder="选择这个自动化固定使用的数据集"
          style={{ width: "100%" }}
          options={datasets.map((dataset) => ({
            value: dataset.id,
            label: `${dataset.name}（${dataset.row_count.toLocaleString()} 行）`,
          }))}
        />
      </div>

      <Tag color={workflow.status === "draft" ? "default" : "blue"}>{workflow.status === "draft" ? "草稿" : workflow.status === "active" ? "已启用" : workflow.status}</Tag>

      {steps.length === 0 && (
        <Alert
          type="warning"
          showIcon
          message="这个自动化还不能运行"
          description="请添加至少一个步骤并保存。通常从 SQL 查询开始，再添加分析、洞察或可视化步骤。"
          style={{ marginTop: 16 }}
        />
      )}
      {steps.length > 0 && datasetIds.length === 0 && (
        <Alert
          type="warning"
          showIcon
          message="还没有绑定数据集"
          description="自动化不会再使用项目里最后打开的数据。请选择固定数据集并保存后再运行。"
          style={{ marginTop: 16 }}
        />
      )}

      {/* Steps */}
      <div style={{ marginTop: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h4 style={{ color: tokens.color.text.primary, margin: 0 }}>步骤（{steps.length}）</h4>
          <div style={{ display: "flex", gap: 4 }}>
            {stepTypeOptions.map((opt) => (
              <Button key={opt.value} size="small" icon={<PlusOutlined />} onClick={() => addStep(opt.value)}>
                {opt.label}
              </Button>
            ))}
          </div>
        </div>

        {steps.length === 0 ? (
          <Card style={{ background: tokens.color.bg.card, border: `0.5px dashed ${tokens.color.border.default}` }}>
            <span style={{ color: "#666" }}>还没有步骤，请从上方添加 SQL、分析或可视化步骤。</span>
          </Card>
        ) : (
          steps.map((step, idx) => (
            <Card
              key={idx}
              size="small"
              style={{ marginBottom: 8, background: tokens.color.bg.card }}
              title={
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Tag color={stepTypeOptions.find((o) => o.value === step.type)?.color || "default"}>
                    步骤 {idx + 1}：{stepTypeOptions.find((option) => option.value === step.type)?.label || step.type.toUpperCase()}
                  </Tag>
                </div>
              }
              extra={
                <Popconfirm title="删除这个步骤？" onConfirm={() => removeStep(idx)}>
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              }
              styles={{ body: { padding: "8px 12px" } }}
            >
              {step.type === "sql" && (
                <Input.TextArea
                  value={step.config.sql_template || ""}
                  onChange={(e) => updateStepConfig(idx, "sql_template", e.target.value)}
                  placeholder="SELECT * FROM data"
                  style={{ fontFamily: "monospace", fontSize: 12 }}
                  autoSize={{ minRows: 2, maxRows: 6 }}
                />
              )}
              {["analyze", "insight"].includes(step.type) && (
                <Input.TextArea
                  value={step.config.prompt || ""}
                  onChange={(e) => updateStepConfig(idx, "prompt", e.target.value)}
                  placeholder="希望 AI 生成什么洞察？"
                  autoSize={{ minRows: 2, maxRows: 4 }}
                />
              )}
              {step.type === "visualize" && (
                <Input
                  value={step.config.chart_type || "auto"}
                  onChange={(e) => updateStepConfig(idx, "chart_type", e.target.value)}
                  placeholder="图表类型（auto、bar、line、pie）"
                />
              )}
              {step.type === "skill" && (
                <Input
                  value={step.config.skill_name || ""}
                  onChange={(e) => updateStepConfig(idx, "skill_name", e.target.value)}
                  placeholder="技能名称"
                />
              )}
              <Input
                size="small"
                value={step.description}
                onChange={(e) => {
                  setSteps((prev) => {
                    const next = [...prev];
                    next[idx] = { ...next[idx], description: e.target.value };
                    return next;
                  });
                }}
                placeholder="步骤描述（可选）"
                style={{ marginTop: 8 }}
              />
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
