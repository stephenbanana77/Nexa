import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Input, Spin, Card, Tag, message, Popconfirm } from "antd";
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
  steps: Step[];
}

const stepTypeOptions = [
  { value: "sql", label: "SQL", color: "blue" },
  { value: "analyze", label: "Analyze", color: "orange" },
  { value: "insight", label: "Insight", color: "purple" },
  { value: "visualize", label: "Visualize", color: "green" },
  { value: "skill", label: "Skill", color: "cyan" },
];

export default function WorkflowEditPage() {
  const { projectId, workflowId } = useParams<{ projectId: string; workflowId: string }>();
  const navigate = useNavigate();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [description, setDesc] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);

  useEffect(() => {
    if (!workflowId) return;
    api.get(`/api/workflows/detail/${workflowId}`)
      .then(({ data }) => {
        setWorkflow(data);
        setName(data.name);
        setDesc(data.description || "");
        setSteps(data.steps || []);
      })
      .catch(() => message.error("Failed to load workflow"))
      .finally(() => setLoading(false));
  }, [workflowId]);

  const addStep = (type: string) => {
    const defaults: Record<string, any> = {
      sql: { sql_template: "SELECT * FROM data LIMIT 10" },
      analyze: { prompt: "Analyze the results." },
      insight: { prompt: "Provide insights based on the analysis." },
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
        steps: steps.map((s, i) => ({ ...s, sort_order: i })),
      });
      message.success("Workflow saved");
    } catch {
      message.error("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    if (!workflowId) return;
    try {
      await api.post(`/api/workflows/${workflowId}/run`);
      message.info("Workflow run started");
    } catch {
      message.error("Failed to run");
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;
  if (!workflow) return <div style={{ padding: 40, textAlign: "center" }}>Workflow not found</div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%", maxWidth: 800 }}>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/project/${projectId}/workflows`)}
        style={{ color: "#888", marginBottom: 16 }}>
        Back to Workflows
      </Button>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <Input
          size="large"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ fontSize: 20, fontWeight: 600, color: tokens.color.text.primary,
            background: "transparent", border: "none", padding: 0, maxWidth: 400 }}
          placeholder="Workflow name"
        />
        <div style={{ display: "flex", gap: 8 }}>
          <Button icon={<PlayCircleOutlined />} onClick={handleRun}>Run</Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>Save</Button>
        </div>
      </div>
      <Input.TextArea
        value={description}
        onChange={(e) => setDesc(e.target.value)}
        style={{ color: "#888", background: "transparent", border: "none", resize: "none", padding: 0, marginBottom: 24 }}
        placeholder="Description (optional)"
        autoSize
      />

      <Tag color={workflow.status === "draft" ? "default" : "blue"}>{workflow.status}</Tag>

      {/* Steps */}
      <div style={{ marginTop: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h4 style={{ color: tokens.color.text.primary, margin: 0 }}>Steps ({steps.length})</h4>
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
            <span style={{ color: "#666" }}>No steps yet. Add SQL, analyze, or visualize steps above.</span>
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
                    Step {idx + 1}: {step.type.toUpperCase()}
                  </Tag>
                </div>
              }
              extra={
                <Popconfirm title="Remove this step?" onConfirm={() => removeStep(idx)}>
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
                  placeholder="What insights should the AI generate?"
                  autoSize={{ minRows: 2, maxRows: 4 }}
                />
              )}
              {step.type === "visualize" && (
                <Input
                  value={step.config.chart_type || "auto"}
                  onChange={(e) => updateStepConfig(idx, "chart_type", e.target.value)}
                  placeholder="Chart type (auto, bar, line, pie)"
                />
              )}
              {step.type === "skill" && (
                <Input
                  value={step.config.skill_name || ""}
                  onChange={(e) => updateStepConfig(idx, "skill_name", e.target.value)}
                  placeholder="Skill name"
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
                placeholder="Step description (optional)"
                style={{ marginTop: 8 }}
              />
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
