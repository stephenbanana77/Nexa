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
  { name: "understanding", label: "理解业务任务", status: "pending" },
  { name: "planning", label: "制定分析计划", status: "pending" },
  { name: "selecting_skill", label: "选择分析方法", status: "pending" },
  { name: "sql_generating", label: "生成受控查询", status: "pending" },
  { name: "querying", label: "查询源数据", status: "pending" },
  { name: "analyzing", label: "解释关键发现", status: "pending" },
  { name: "visualizing", label: "准备交付结果", status: "pending" },
];

const TASK_STARTERS = [
  "每周对比销售额和利润与上一周期的变化，解释波动最大的部分，并准备一份有数据证据的复盘。",
  "检查这份数据的质量问题，并告诉我报告发布前必须修复哪些问题。",
  "找出销售额增长但利润下降的细分市场，并建议下一步分析来验证原因。",
];

function readableError(detail: unknown) {
  if (typeof detail === "string") {
    const normalized = detail.toLowerCase();
    if (normalized.includes("authentication") || normalized.includes("401") || normalized.includes("api key")) {
      return "模型连接被拒绝。请打开「高级工具 > 模型设置」，测试凭据后重新运行任务。";
    }
    if (normalized.includes("no available channel") || normalized.includes("503") || normalized.includes("unavailable")) {
      return "当前服务商无法提供所选模型。请在「模型设置」中更换模型后重试。";
    }
    if (normalized.includes("timeout") || normalized.includes("timed out")) {
      return "模型未在运行时限内响应。请重试，或在「模型设置」中选择响应更快的模型。";
    }
    return detail.replace(/\s*\(request_id:[^)]+\)/gi, "");
  }
  if (Array.isArray(detail)) return detail.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("; ");
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "分析未完成。请检查模型连接后重试。";
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
      message.info("请先连接或上传数据，再让 Agent 执行任务");
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
      if (!response.ok) throw new Error(`分析请求失败（${response.status}）`);

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
      if (!finalData.summary) throw new Error("模型服务未返回分析结果");

      markStagesDone();
      const rowCount = Number(finalData.row_count || 0);
      const totalRows = Number(finalData.total_rows || 0);
      credibility.rows_queried = rowCount;
      credibility.data_coverage = totalRows ? `源数据 ${totalRows.toLocaleString()} 行，本次返回 ${rowCount} 行` : `本次返回 ${rowCount} 行`;
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
      const errorText = error instanceof Error ? error.message : "分析未完成";
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
      message.success("已保存到交付物");
    } catch {
      message.error("交付物保存失败，本次分析仍可在「审计」中查看");
    }
  };

  const openTaskModal = () => {
    if (!latestAnswer) return;
    setTaskName(latestQuestion.slice(0, 80) || "重复分析任务");
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
        insight: "如果存在上次运行结果，请进行对比。解释重要变化，引用查询证据，并说明下一步需要检查什么。",
        task_config: {
          name: taskName.trim() || "重复分析任务",
          cadence,
          compare_previous: comparePrevious,
          delivery,
          dataset_ids: selectedDatasetIds,
          scheduler_status: "not_connected",
        },
      });
      message.success("可重复任务已保存");
      setTaskModalOpen(false);
      navigate(`/project/${projectId}?tab=workflows`);
    } catch {
      message.error("可重复任务保存失败，请稍后重试");
    } finally {
      setSavingTask(false);
    }
  };

  const downloadAnalysis = (answer: ChatMessage) => {
    const md = `# Nexa 分析结果\n\n${answer.content}\n\n${answer.sql ? `## 查询语句\n\n\`\`\`sql\n${answer.sql}\n\`\`\`` : ""}`;
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
            <span className="agent-kicker">数据任务 Agent</span>
            <h2>{conversationId ? "继续完善任务" : "描述你需要的结果"}</h2>
          </div>
          {messages.length > 0 && (
            <Button type="text" icon={<PlusOutlined />} onClick={startNewTask}>新任务</Button>
          )}
        </header>

        <div className="agent-thread">
          {messages.length === 0 && !loading && (
            <div className="agent-empty">
              <div className="agent-empty-mark">N</div>
              <h3>交给 Agent 一项需要持续完成的数据任务</h3>
              <p>说明要做的业务判断、对比周期，以及什么情况需要关注。首次运行后还可以继续调整。</p>
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
              <span className="task-message-label">任务</span>
              <p>{item.content}</p>
            </div>
          ) : (
            <article className={`agent-answer ${item.error ? "agent-answer-error" : ""}`} key={index}>
              <div className="agent-answer-rail">
                {item.error ? <ExclamationCircleOutlined /> : <CheckCircleOutlined />}
              </div>
              <div className="agent-answer-body">
                {item.error && <strong className="error-title">本次运行未完成</strong>}
                <ReactMarkdown>{item.content}</ReactMarkdown>

                {item.charts?.map((chart, chartIndex) => (
                  <div className="agent-chart" key={`${chart.title}-${chartIndex}`}>
                    <strong>{chart.title}</strong>
                    <ReactECharts option={chart.options} style={{ height: 260, width: "100%" }} theme="dark" notMerge />
                  </div>
                ))}

                {item.rows && item.columns && item.rows.length > 0 && (
                  <div className="agent-result-table">
                    <div className="result-table-heading">查询结果 <span>{item.row_count} 行</span></div>
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
                    <summary>查看查询证据</summary>
                    <pre>{item.sql}</pre>
                  </details>
                )}

                {!item.error && item.sql && (
                  <div className="answer-actions">
                    <Button type="primary" icon={<BranchesOutlined />} onClick={openTaskModal}>保存为可重复任务</Button>
                    <Button icon={<FileDoneOutlined />} onClick={() => saveInsight(item)}>保存交付物</Button>
                    <Button icon={<DownloadOutlined />} onClick={() => downloadAnalysis(item)} aria-label="下载分析结果" title="下载分析结果" />
                    <Button icon={<CopyOutlined />} onClick={() => navigator.clipboard.writeText(item.content)} aria-label="复制分析结果" title="复制分析结果" />
                  </div>
                )}
              </div>
            </article>
          ))}

          {showProgress && (
            <div className="agent-running">
              <span className="running-signal" />
              <div>
                <strong>Agent 正在处理任务</strong>
                <span>{stages.find((stage) => stage.status === "running")?.label || "正在准备分析"}</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <footer className="agent-composer">
          {datasets.length === 0 ? (
            <button className="connect-data-prompt" type="button" onClick={() => navigate(`/project/${projectId}?tab=data`)}>
              <DatabaseOutlined /> 先接入数据，再分配任务 <ArrowRightOutlined />
            </button>
          ) : (
            <Select
              mode="multiple"
              value={selectedDatasetIds}
              onChange={setSelectedDatasetIds}
              options={datasets.map((dataset) => ({ value: dataset.id, label: dataset.name }))}
              maxTagCount={1}
              className="dataset-picker"
              aria-label="Agent 使用的数据集"
            />
          )}
          <Input.TextArea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="描述分析任务，或让 Agent 继续完善结果..."
            autoSize={{ minRows: 2, maxRows: 6 }}
            disabled={loading}
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                handleSend();
              }
            }}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} disabled={!input.trim()} aria-label="运行任务" title="运行任务" />
        </footer>
      </section>

      <aside className="agent-task-panel">
        <div className="task-panel-section">
          <span className="task-panel-label">当前数据</span>
          {selectedDatasets.length === 0 ? (
            <p className="panel-muted">尚未选择数据源。</p>
          ) : selectedDatasets.map((dataset) => (
            <div className="data-source-row" key={dataset.id}>
              <DatabaseOutlined />
              <span><strong>{dataset.name}</strong><small>{dataset.row_count?.toLocaleString() || "-"} 行</small></span>
            </div>
          ))}
        </div>

        <div className="task-panel-section">
          <span className="task-panel-label">运行计划</span>
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
          <span className="task-panel-label">运行结果</span>
          {latestAnswer ? (
            <>
              <strong>可以复用</strong>
              <p>查询和证据已保留。确认结果符合业务需要后，可将本次运行保存为可重复任务。</p>
              <Button block icon={<BranchesOutlined />} onClick={openTaskModal}>配置重复任务</Button>
            </>
          ) : (
            <p className="panel-muted">任务完成后，可以设置对比和交付方式并沉淀为可复用任务。</p>
          )}
        </div>
      </aside>

      <Modal
        title="保存为可重复任务"
        open={taskModalOpen}
        onOk={saveRepeatableTask}
        onCancel={() => setTaskModalOpen(false)}
        confirmLoading={savingTask}
        okText="保存任务"
        width={560}
      >
        <div className="task-config-form">
          <label>
            <span>任务名称</span>
            <Input value={taskName} onChange={(event) => setTaskName(event.target.value)} />
          </label>
          <label>
            <span>运行频率</span>
            <Select
              value={cadence}
              onChange={setCadence}
              options={[
                { value: "manual", label: "按需运行" },
                { value: "on_new_data", label: "新数据到达时" },
                { value: "weekly", label: "每周" },
                { value: "monthly", label: "每月" },
              ]}
            />
          </label>
          <label>
            <span>交付方式</span>
            <Select
              value={delivery}
              onChange={setDelivery}
              options={[
                { value: "workspace_report", label: "工作区报告" },
                { value: "review_queue", label: "审核队列" },
                { value: "download", label: "可下载报告" },
              ]}
            />
          </label>
          <div className="task-config-switch">
            <span><strong>与上次运行对比</strong><small>突出发生的变化，不再重复相同摘要。</small></span>
            <Switch checked={comparePrevious} onChange={setComparePrevious} />
          </div>
          {cadence !== "manual" && (
            <div className="scheduler-note"><ClockCircleOutlined /> 运行频率会随任务保存；连接调度器之前，自动调度不会启动。</div>
          )}
        </div>
      </Modal>
    </div>
  );
}
