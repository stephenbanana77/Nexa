import { useState } from "react";
import { Modal, Select, message, Steps } from "antd";
import ReactECharts from "echarts-for-react";
import ReactMarkdown from "react-markdown";
import { tokens } from "../theme";
import type { Skill } from "../types";

interface Props {
  skill: Skill | null;
  projectId: string;
  datasets: { id: string; name: string }[];
  open: boolean;
  onClose: () => void;
}

interface StepState {
  type: string;
  status: "wait" | "process" | "finish" | "error";
  result?: unknown;
}

export default function SkillExecutionModal({ skill, projectId, datasets, open, onClose }: Props) {
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<StepState[]>([]);
  const [output, setOutput] = useState<{
    chart?: Record<string, unknown>;
    insight?: string;
    columns?: string[];
    rows?: unknown[][];
  }>({});

  const handleRun = async () => {
    if (!skill || !selectedDataset) return;

    setRunning(true);
    const def = skill.definition;
    setSteps(def.steps.map((s: { type: string }) => ({ type: s.type, status: "wait" as const })));

    const token = localStorage.getItem("nexa_token");
    const skillId = skill.id || skill.name;

    try {
      const response = await fetch(`/api/skills/${skillId}/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ project_id: projectId, dataset_id: selectedDataset, params: {} }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            const evt = data.event;

            if (evt === "step_start") {
              setSteps((prev) => prev.map((s, i) => i === data.step - 1 ? { ...s, status: "process" as const } : s));
            } else if (evt === "step_done") {
              setSteps((prev) => prev.map((s, i) => i === data.step - 1 ? { ...s, status: "finish" as const } : s));

              if (data.type === "sql" && data.result) {
                setOutput((prev) => ({
                  ...prev,
                  columns: data.result.columns,
                  rows: data.result.rows,
                }));
              } else if (data.type === "visualize" && data.chart) {
                setOutput((prev) => ({ ...prev, chart: data.chart }));
              } else if (data.type === "insight" && data.insight) {
                setOutput((prev) => ({ ...prev, insight: data.insight }));
              }
            } else if (evt === "step_error") {
              setSteps((prev) => prev.map((s, i) => i === data.step - 1 ? { ...s, status: "error" as const } : s));
            }
          } catch {
            // Ignore malformed SSE fragments; the stream may split JSON across chunks.
          }
        }
      }
    } catch {
      message.error("Skill execution failed");
    } finally {
      setRunning(false);
    }
  };

  const onClose_ = () => {
    setSteps([]);
    setOutput({});
    setRunning(false);
    setSelectedDataset(null);
    onClose();
  };

  return (
    <Modal
      title={skill?.title || "Run Skill"}
      open={open}
      onCancel={onClose_}
      width={700}
      footer={null}
      destroyOnClose
    >
      {!running && steps.length === 0 && (
        <>
          <div style={{ marginBottom: tokens.spacing.lg }}>
            <span style={{ color: tokens.color.text.tertiary, fontSize: tokens.fontSize.sm }}>Select Dataset</span>
            <Select
              style={{ width: "100%", marginTop: tokens.spacing.xs }}
              placeholder="Choose a dataset..."
              value={selectedDataset}
              onChange={setSelectedDataset}
              options={datasets.map((d) => ({ label: d.name, value: d.id }))}
            />
          </div>
          <button
            onClick={handleRun}
            disabled={!selectedDataset}
            style={{
              width: "100%", padding: "10px 0", borderRadius: tokens.radius.md,
              background: selectedDataset ? "#2563EB" : "#333", color: "#fff",
              border: "none", cursor: selectedDataset ? "pointer" : "not-allowed",
              fontSize: tokens.fontSize.md, fontWeight: 500,
            }}
          >
            Run {skill?.title}
          </button>
        </>
      )}

      {(running || steps.length > 0) && (
        <div>
          <Steps
            size="small"
            current={steps.findIndex((s) => s.status === "process")}
            status={steps.find((s) => s.status === "error") ? "error" : "process"}
            items={steps.map((s) => ({
              title: s.type.toUpperCase(),
              status: s.status === "error" ? "error" : s.status === "finish" ? "finish" : s.status === "process" ? "process" : "wait",
            }))}
          />

          {output.chart && (
            <div style={{ marginTop: tokens.spacing.lg }}>
              <div style={{ fontSize: tokens.fontSize.xs, color: tokens.color.text.muted, marginBottom: 4, textTransform: "uppercase" }}>
                {output.chart.title as string || "Chart"}
              </div>
              <ReactECharts
                option={output.chart.options as Record<string, unknown>}
                style={{ height: 250, width: "100%" }}
                theme="dark"
                notMerge
              />
            </div>
          )}

          {output.insight && (
            <div style={{ marginTop: tokens.spacing.lg, background: tokens.color.bg.page, padding: tokens.spacing.lg, borderRadius: tokens.radius.md }}>
              <ReactMarkdown>{output.insight}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
