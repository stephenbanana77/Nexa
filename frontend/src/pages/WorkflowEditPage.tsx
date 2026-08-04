import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Input, Select, Card, message, Spin, Popconfirm } from "antd";
import {
  PlusOutlined, DeleteOutlined, ArrowLeftOutlined,
  ArrowUpOutlined, ArrowDownOutlined, SaveOutlined,
} from "@ant-design/icons";
import { api } from "../services";
import { tokens } from "../theme";

const stepTypeOptions = [
  { label: "SQL Query", value: "sql" },
  { label: "Skill", value: "skill" },
  { label: "Analyze", value: "analyze" },
  { label: "Visualize", value: "visualize" },
  { label: "Insight", value: "insight" },
];

interface Step {
  id?: string;
  type: string;
  config: Record<string, string>;
  description: string;
}

interface WorkflowDetail {
  id: string;
  name: string;
  description: string;
  project_id: string;
  status: string;
  steps: Step[];
}

export default function WorkflowEditPage() {
  const { projectId, workflowId } = useParams<{ projectId: string; workflowId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);

  useEffect(() => {
    if (!workflowId) return;
    api.get(`/api/workflows/detail/${workflowId}`)
      .then(({ data }) => {
        setWorkflow(data);
        setSteps(data.steps?.length ? data.steps : [emptyStep()]);
      })
      .catch(() => message.error("Failed to load workflow"))
      .finally(() => setLoading(false));
  }, [workflowId]);

  const emptyStep = (): Step => ({
    type: "sql",
    config: {},
    description: "",
  });

  const addStep = (afterIndex: number) => {
    const next = [...steps];
    next.splice(afterIndex + 1, 0, emptyStep());
    setSteps(next);
  };

  const removeStep = (index: number) => {
    if (steps.length <= 1) return;
    setSteps(steps.filter((_, i) => i !== index));
  };

  const moveStep = (index: number, dir: 1 | -1) => {
    const target = index + dir;
    if (target < 0 || target >= steps.length) return;
    const next = [...steps];
    [next[index], next[target]] = [next[target], next[index]];
    setSteps(next);
  };

  const updateStep = (index: number, patch: Partial<Step>) => {
    setSteps(steps.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const handleSave = async () => {
    if (!workflowId) return;
    setSaving(true);
    try {
      await api.put(`/api/workflows/${workflowId}`, {
        name: workflow?.name || '',
        description: workflow?.description || '',
        steps: steps.map((s, i) => ({
          sort_order: i,
          type: s.type,
          config: s.config,
          input_refs: [],
          description: s.description,
        })),
      });
      message.success("Saved");
      navigate(`/project/${projectId}`);
    } catch {
      message.error("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;
  if (!workflow) return null;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: tokens.spacing.lg }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/project/${projectId}`)} />
        <div style={{ flex: 1 }}>
          <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>
            Edit: {workflow.name}
          </h2>
        </div>
        <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
          Save
        </Button>
      </div>

      {steps.map((step, i) => (
        <Card
          key={i}
          size="small"
          style={{
            background: tokens.color.bg.card,
            border: `0.5px solid ${tokens.color.border.default}`,
            borderRadius: tokens.radius.md,
            marginBottom: 8,
          }}
          title={
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{
                width: 22, height: 22, borderRadius: "50%", background: "#2563EB",
                color: "#fff", fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                {i + 1}
              </span>
              <Select
                value={step.type}
                onChange={(v) => updateStep(i, { type: v, config: {} })}
                options={stepTypeOptions}
                style={{ width: 140 }}
                size="small"
              />
              <Input
                placeholder="Step description (optional)"
                value={step.description}
                onChange={(e) => updateStep(i, { description: e.target.value })}
                style={{ flex: 1 }}
                size="small"
              />
              <Button size="small" icon={<ArrowUpOutlined />} disabled={i === 0} onClick={() => moveStep(i, -1)} />
              <Button size="small" icon={<ArrowDownOutlined />} disabled={i === steps.length - 1} onClick={() => moveStep(i, 1)} />
              <Popconfirm title="Delete this step?" onConfirm={() => removeStep(i)}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </div>
          }
        >
          {step.type === "sql" && (
            <Input.TextArea
              rows={3}
              placeholder="SQL template or leave empty for AI generation"
              value={step.config.sql_template || ""}
              onChange={(e) => updateStep(i, { config: { ...step.config, sql_template: e.target.value } })}
            />
          )}
          {step.type === "skill" && (
            <Input
              placeholder="Skill name (e.g. data_summary)"
              value={step.config.skill_name || ""}
              onChange={(e) => updateStep(i, { config: { ...step.config, skill_name: e.target.value } })}
            />
          )}
          {(step.type === "analyze" || step.type === "insight") && (
            <Input.TextArea
              rows={2}
              placeholder="Analysis prompt or leave empty for default"
              value={step.config.prompt || ""}
              onChange={(e) => updateStep(i, { config: { ...step.config, prompt: e.target.value } })}
            />
          )}
          {step.type === "visualize" && (
            <Select
              placeholder="Chart type"
              value={step.config.chart_type || "auto"}
              onChange={(v) => updateStep(i, { config: { ...step.config, chart_type: v } })}
              options={[
                { label: "Auto", value: "auto" },
                { label: "Bar", value: "bar" },
                { label: "Line", value: "line" },
                { label: "Pie", value: "pie" },
              ]}
              style={{ width: "100%" }}
            />
          )}
        </Card>
      ))}

      <Button
        type="dashed"
        block
        icon={<PlusOutlined />}
        onClick={() => addStep(steps.length - 1)}
        style={{ marginTop: 8 }}
      >
        Add Step
      </Button>
    </div>
  );
}
