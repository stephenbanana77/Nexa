import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button, Input, Modal, Select, Switch, message } from "antd";
import {
  ArrowRightOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CopyOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  FileDoneOutlined,
  PlusOutlined,
  SendOutlined,
} from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import ReactECharts from "echarts-for-react";
import api from "../api/client";
import "./ChatPage.css";

interface ChartConfig {
  type: string;
  title: string;
  options: Record<string, unknown>;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  error?: boolean;
  sql?: string;
  columns?: string[];
  rows?: unknown[][];
  row_count?: number;
  charts?: ChartConfig[];
  credibility?: {
    rows_queried: number;
    sql_retries: number;
    mode: string;
    data_coverage: string;
  };
}

interface ProgressStage {
  name: string;
  label: string;
  status: "done" | "running" | "pending";
}

const STAGES: ProgressStage[] = [
  { name: "understanding", label: "Understand the business task", status: "pending" },
  { name: "planning", label: "Plan the analysis", status: "pending" },
  { name: "selecting_skill", label: "Choose analysis method", status: "pending" },
  { name: "sql_generating", label: "Build a governed query", status: "pending" },
  { name: "querying", label: "Run against source data", status: "pending" },
  { name: "analyzing", label: "Explain material findings", status: "pending" },
  { name: "visualizing", label: "Prepare the deliverable", status: "pending" },
];

const TASK_STARTERS = [
  "Every week, compare sales and profit with the previous period. Explain the largest changes and prepare an evidence-backed review.",
  "Check this data for quality problems and tell me what must be fixed before the report is published.",
  "Find the segments that are losing profit despite growing sales, then recommend the next analysis to verify the cause.",
];

function readableError(detail: unknown) {
  if (typeof detail === "string") {
    const normalized = detail.toLowerCase();
    if (normalized.includes("authentication") || normalized.includes("401") || normalized.includes("api key")) {
      return "The model connection was rejected. Open Advanced tools > Provider settings, test the credentials, then run this task again.";
    }
    if (normalized.includes("no available channel") || normalized.includes("503") || normalized.includes("unavailable")) {
      return "The selected model is not available from the provider. Choose another model in Provider settings and retry.";
    }
    if (normalized.includes("timeout") || normalized.includes("timed out")) {
      return "The model did not respond before the run deadline. Retry once or choose a faster model in Provider settings.";
    }
    return detail.replace(/\s*\(request_id:[^)]+\)/gi, "");
  }
  if (Array.isArray(detail)) return detail.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("; ");
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "The analysis did not complete. Check the model connection and try again.";
}

export default function ChatPage({ projectId }: { projectId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [selectedDatasetIds, setSelectedDatasetIds] = useState<string[]>([]);
  const [datasets, setDatasets] = useState<{ id: string; name: string; row_count?: number }[]>([]);
  const [stages, setStages] = useState<ProgressStage[]>(STAGES);
  const [showProgress, setShowProgress] = useState(false);
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [taskName, setTaskName] = useState("");
  const [cadence, setCadence] = useState("manual");
  const [comparePrevious, setComparePrevious] = useState(true);
  const [delivery, setDelivery] = useState("workspace_report");
  const [savingTask, setSavingTask] = useState(false);
  const [searchParams] = useSearchParams();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get(`/api/datasets?project_id=${projectId}`).then(({ data }) => {
      const list = data.items || data;
      const safeList = Array.isArray(list) ? list : [];
      setDatasets(safeList);
      if (safeList.length > 0) setSelectedDatasetIds([safeList[0].id]);
    }).catch(() => {});
  }, [projectId]);

  useEffect(() => {
    const question = searchParams.get("question");
    if (question) setInput(question);
  }, [searchParams]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, showProgress]);

  const selectedDatasets = useMemo(
    () => datasets.filter((dataset) => selectedDatasetIds.includes(dataset.id)),
    [datasets, selectedDatasetIds],
  );

  const latestAnswer = useMemo(
    () => [...messages].reverse().find((item) => item.role === "assistant" && !item.error && item.sql),
    [messages],
  );

  const latestQuestion = useMemo(() => {
    if (!latestAnswer) return "";
    const answerIndex = messages.indexOf(latestAnswer);
    return [...messages.slice(0, answerIndex)].reverse().find((item) => item.role === "user")?.content || "";
  }, [latestAnswer, messages]);

  const resetStages = () => setStages(STAGES.map((stage) => ({ ...stage, status: "pending" })));

  const advanceStage = (name: string) => {
    const target = STAGES.findIndex((stage) => stage.name === name);
    if (target < 0) return;
    setStages((current) => current.map((stage, index) => ({
      ...stage,
      status: index < target ? "done" : index === target ? "running" : "pending",
    })));
  };

  const markStagesDone = () => setStages((current) => current.map((stage) => ({ ...stage, status: "done" })));

  const startNewTask = () => {
    setMessages([]);
    setConversationId(null);
    resetStages();
    setShowProgress(false);
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    if (selectedDatasetIds.length === 0) {
      message.info("Connect or upload data before the agent runs this task");
      navigate(`/project/${projectId}?tab=data`);
      return;
    }

    setInput("");
    setLoading(true);
    resetStages();
    setShowProgress(true);
    setMessages((current) => [...current, { role: "user", content: text }]);

    try {
      const token = localStorage.getItem("nexa_token");
      const body: Record<string, unknown> = {
        project_id: projectId,
        message: text,
        dataset_ids: selectedDatasetIds,
      };
      if (conversationId) body.conversation_id = conversationId;

      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(`Analysis request failed (${response.status})`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalData: Record<string, unknown> = {};
      let failed = false;
      const credibility = { rows_queried: 0, sql_retries: 0, mode: "sql", data_coverage: "unknown" };

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
            const eventName = data.event;
            if (eventName === "understanding") advanceStage("understanding");
            else if (eventName === "planning") advanceStage("planning");
            else if (eventName === "selecting_skill") advanceStage("selecting_skill");
            else if (eventName === "running_skill") { advanceStage("selecting_skill"); credibility.mode = "skill"; }
            else if (eventName === "sql_generating") advanceStage("sql_generating");
            else if (eventName === "querying") advanceStage("querying");
            else if (eventName === "analyzing") advanceStage("analyzing");
            else if (eventName === "visualizing") advanceStage("visualizing");
            else if (eventName === "insight") finalData = data;
            else if (eventName === "conversation_created") setConversationId(data.conversation_id);
            else if (eventName === "retry") credibility.sql_retries += 1;
            else if (eventName === "error" || eventName === "timeout") {
              failed = true;
              const errorText = readableError(data.message);
              setMessages((current) => [...current, { role: "assistant", content: errorText, error: true }]);
            }
          } catch {
            // Ignore malformed keep-alive chunks while preserving the stream.
          }
        }
      }

      setShowProgress(false);
      if (failed) return;
      if (!finalData.summary) throw new Error("The provider returned no analysis result");

      markStagesDone();
      const rowCount = Number(finalData.row_count || 0);
      const totalRows = Number(finalData.total_rows || 0);
      credibility.rows_queried = rowCount;
      credibility.data_coverage = totalRows ? `${rowCount} result rows from ${totalRows.toLocaleString()} source rows` : `${rowCount} result rows`;
      setMessages((current) => [...current, {
        role: "assistant",
        content: String(finalData.summary),
        sql: finalData.sql as string | undefined,
        columns: finalData.columns as string[] | undefined,
        rows: finalData.rows as unknown[][] | undefined,
        row_count: rowCount,
        charts: (finalData.charts || []) as ChartConfig[],
        credibility,
      }]);
    } catch (error) {
      const errorText = error instanceof Error ? error.message : "The analysis did not complete";
      setMessages((current) => [...current, { role: "assistant", content: errorText, error: true }]);
      setShowProgress(false);
    } finally {
      setLoading(false);
    }
  };

  const saveInsight = async (answer: ChatMessage) => {
    try {
      await api.post("/api/insights/", {
        project_id: projectId,
        question: latestQuestion,
        content: {
          summary: answer.content,
          sql: answer.sql,
          columns: answer.columns,
          rows: answer.rows?.slice(0, 20),
          row_count: answer.row_count,
          charts: answer.charts || [],
        },
      });
      message.success("Saved to deliverables");
    } catch {
      message.error("The deliverable could not be saved. The analysis remains in Audit.");
    }
  };

  const openTaskModal = () => {
    if (!latestAnswer) return;
    setTaskName(latestQuestion.slice(0, 80) || "Recurring analysis task");
    setTaskModalOpen(true);
  };

  const saveRepeatableTask = async () => {
    if (!latestAnswer) return;
    setSavingTask(true);
    try {
      await api.post("/api/workflows/chat-to-workflow", {
        project_id: projectId,
        question: latestQuestion,
        sql: latestAnswer.sql,
        charts: latestAnswer.charts || [],
        insight: "Compare the current result with the prior run when available. Explain material changes, cite the query evidence, and state what should be checked next.",
        task_config: {
          name: taskName.trim() || "Recurring analysis task",
          cadence,
          compare_previous: comparePrevious,
          delivery,
          dataset_ids: selectedDatasetIds,
          scheduler_status: "not_connected",
        },
      });
      message.success("Repeatable task saved");
      setTaskModalOpen(false);
      navigate(`/project/${projectId}?tab=workflows`);
    } catch {
      message.error("The repeatable task could not be saved");
    } finally {
      setSavingTask(false);
    }
  };

  const downloadAnalysis = (answer: ChatMessage) => {
    const md = `# Nexa analysis\n\n${answer.content}\n\n${answer.sql ? `## Query\n\n\`\`\`sql\n${answer.sql}\n\`\`\`` : ""}`;
    const url = URL.createObjectURL(new Blob([md], { type: "text/markdown" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "nexa-analysis.md";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 100);
  };

  return (
    <div className="agent-workspace">
      <section className="agent-conversation">
        <header className="agent-conversation-header">
          <div>
            <span className="agent-kicker">Data task agent</span>
            <h2>{conversationId ? "Continue the task" : "Describe the outcome you need"}</h2>
          </div>
          {messages.length > 0 && (
            <Button type="text" icon={<PlusOutlined />} onClick={startNewTask}>New task</Button>
          )}
        </header>

        <div className="agent-thread">
          {messages.length === 0 && !loading && (
            <div className="agent-empty">
              <div className="agent-empty-mark">N</div>
              <h3>Give the agent a recurring responsibility</h3>
              <p>Include the decision, comparison period, and what should trigger attention. You can refine the task after the first run.</p>
              <div className="agent-starters">
                {TASK_STARTERS.map((starter) => (
                  <button type="button" key={starter} onClick={() => setInput(starter)}>
                    <span>{starter}</span><ArrowRightOutlined />
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((item, index) => item.role === "user" ? (
            <div className="task-message" key={index}>
              <span className="task-message-label">Task</span>
              <p>{item.content}</p>
            </div>
          ) : (
            <article className={`agent-answer ${item.error ? "agent-answer-error" : ""}`} key={index}>
              <div className="agent-answer-rail">
                {item.error ? <ExclamationCircleOutlined /> : <CheckCircleOutlined />}
              </div>
              <div className="agent-answer-body">
                {item.error && <strong className="error-title">Run did not complete</strong>}
                <ReactMarkdown>{item.content}</ReactMarkdown>

                {item.charts?.map((chart, chartIndex) => (
                  <div className="agent-chart" key={`${chart.title}-${chartIndex}`}>
                    <strong>{chart.title}</strong>
                    <ReactECharts option={chart.options} style={{ height: 260, width: "100%" }} theme="dark" notMerge />
                  </div>
                ))}

                {item.rows && item.columns && item.rows.length > 0 && (
                  <div className="agent-result-table">
                    <div className="result-table-heading">Query result <span>{item.row_count} rows</span></div>
                    <div className="result-table-scroll">
                      <table>
                        <thead><tr>{item.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
                        <tbody>{item.rows.slice(0, 10).map((row, rowIndex) => (
                          <tr key={rowIndex}>{row.map((value, columnIndex) => <td key={columnIndex}>{String(value ?? "")}</td>)}</tr>
                        ))}</tbody>
                      </table>
                    </div>
                  </div>
                )}

                {item.sql && (
                  <details className="query-evidence">
                    <summary>View query evidence</summary>
                    <pre>{item.sql}</pre>
                  </details>
                )}

                {!item.error && item.sql && (
                  <div className="answer-actions">
                    <Button type="primary" icon={<BranchesOutlined />} onClick={openTaskModal}>Save as repeatable task</Button>
                    <Button icon={<FileDoneOutlined />} onClick={() => saveInsight(item)}>Save deliverable</Button>
                    <Button icon={<DownloadOutlined />} onClick={() => downloadAnalysis(item)} aria-label="Download analysis" />
                    <Button icon={<CopyOutlined />} onClick={() => navigator.clipboard.writeText(item.content)} aria-label="Copy analysis" />
                  </div>
                )}
              </div>
            </article>
          ))}

          {showProgress && (
            <div className="agent-running">
              <span className="running-signal" />
              <div>
                <strong>Agent is working through the task</strong>
                <span>{stages.find((stage) => stage.status === "running")?.label || "Preparing the analysis"}</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <footer className="agent-composer">
          {datasets.length === 0 ? (
            <button className="connect-data-prompt" type="button" onClick={() => navigate(`/project/${projectId}?tab=data`)}>
              <DatabaseOutlined /> Connect data before assigning a task <ArrowRightOutlined />
            </button>
          ) : (
            <Select
              mode="multiple"
              value={selectedDatasetIds}
              onChange={setSelectedDatasetIds}
              options={datasets.map((dataset) => ({ value: dataset.id, label: dataset.name }))}
              maxTagCount={1}
              className="dataset-picker"
              aria-label="Datasets used by the agent"
            />
          )}
          <Input.TextArea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Describe the analysis task or ask the agent to refine the result..."
            autoSize={{ minRows: 2, maxRows: 6 }}
            disabled={loading}
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                handleSend();
              }
            }}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} disabled={!input.trim()} aria-label="Run task" />
        </footer>
      </section>

      <aside className="agent-task-panel">
        <div className="task-panel-section">
          <span className="task-panel-label">Current data</span>
          {selectedDatasets.length === 0 ? (
            <p className="panel-muted">No source selected.</p>
          ) : selectedDatasets.map((dataset) => (
            <div className="data-source-row" key={dataset.id}>
              <DatabaseOutlined />
              <span><strong>{dataset.name}</strong><small>{dataset.row_count?.toLocaleString() || "-"} rows</small></span>
            </div>
          ))}
        </div>

        <div className="task-panel-section">
          <span className="task-panel-label">Run plan</span>
          <ol className="task-stage-list">
            {stages.map((stage) => (
              <li key={stage.name} className={stage.status}>
                <span className="stage-marker" />
                <span>{stage.label}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="task-panel-section task-panel-outcome">
          <span className="task-panel-label">Outcome</span>
          {latestAnswer ? (
            <>
              <strong>Ready to reuse</strong>
              <p>The query and evidence are available. Save this run as a repeatable task when the result matches the business need.</p>
              <Button block icon={<BranchesOutlined />} onClick={openTaskModal}>Configure repeat task</Button>
            </>
          ) : (
            <p className="panel-muted">A completed run can become a reusable task with comparison and delivery preferences.</p>
          )}
        </div>
      </aside>

      <Modal
        title="Save as repeatable task"
        open={taskModalOpen}
        onOk={saveRepeatableTask}
        onCancel={() => setTaskModalOpen(false)}
        confirmLoading={savingTask}
        okText="Save task"
        width={560}
      >
        <div className="task-config-form">
          <label>
            <span>Task name</span>
            <Input value={taskName} onChange={(event) => setTaskName(event.target.value)} />
          </label>
          <label>
            <span>Intended cadence</span>
            <Select
              value={cadence}
              onChange={setCadence}
              options={[
                { value: "manual", label: "Run on demand" },
                { value: "on_new_data", label: "When new data arrives" },
                { value: "weekly", label: "Weekly" },
                { value: "monthly", label: "Monthly" },
              ]}
            />
          </label>
          <label>
            <span>Deliver as</span>
            <Select
              value={delivery}
              onChange={setDelivery}
              options={[
                { value: "workspace_report", label: "Workspace report" },
                { value: "review_queue", label: "Review queue" },
                { value: "download", label: "Downloadable report" },
              ]}
            />
          </label>
          <div className="task-config-switch">
            <span><strong>Compare with prior run</strong><small>Highlight what changed instead of repeating the same summary.</small></span>
            <Switch checked={comparePrevious} onChange={setComparePrevious} />
          </div>
          {cadence !== "manual" && (
            <div className="scheduler-note"><ClockCircleOutlined /> Cadence is saved with the task. Automatic scheduling remains off until a scheduler is connected.</div>
          )}
        </div>
      </Modal>
    </div>
  );
}
