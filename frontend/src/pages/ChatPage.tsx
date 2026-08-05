import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Input, message, Select } from "antd";
import { SendOutlined, SaveOutlined, BookOutlined, PlusOutlined, BranchesOutlined, ShareAltOutlined, DownloadOutlined, CopyOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import ReactECharts from "echarts-for-react";
import api from "../api/client";
import "./ChatPage.css";

interface ChartConfig {
  type: string;
  title: string;
  options: Record<string, any>;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  columns?: string[];
  rows?: any[][];
  row_count?: number;
  charts?: ChartConfig[];
}

interface ProgressStage {
  name: string;
  label: string;
  status: "done" | "running" | "pending";
}

const STAGES: ProgressStage[] = [
  { name: "understanding", label: "Understanding intent", status: "pending" },
  { name: "planning", label: "Planning analysis", status: "pending" },
  { name: "selecting_skill", label: "Selecting skill", status: "pending" },
  { name: "sql_generating", label: "Generating SQL", status: "pending" },
  { name: "querying", label: "Querying data", status: "pending" },
  { name: "analyzing", label: "Analyzing results", status: "pending" },
  { name: "visualizing", label: "Generating charts", status: "pending" },
];

export default function ChatPage({ projectId }: { projectId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<{id: string; name: string}[]>([]);

  useEffect(() => {
    if (!projectId) return;
    api.get(`/api/datasets?project_id=${projectId}`).then(({ data }) => {
      const list = data.items || data;
      setDatasets(Array.isArray(list) ? list : []);
      if (list.length > 0) setSelectedDatasetId(list[0].id);
    }).catch(() => {});
  }, [projectId]);
  const [stages, setStages] = useState<ProgressStage[]>(STAGES);
  const [showProgress, setShowProgress] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, showProgress]);

  const resetStages = () => setStages(STAGES.map((s) => ({ ...s, status: "pending" as const })));

  const updateStage = (eventName: string, status: "running" | "done") => {
    setStages((prev) =>
      prev.map((s) => {
        if (s.name === eventName) return { ...s, status };
        return s;
      })
    );
  };

  const newConversation = () => {
    setMessages([]);
    setConversationId(null);
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setLoading(true);
    resetStages();
    setShowProgress(true);
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    try {
      const token = localStorage.getItem("nexa_token");
      const body: any = { project_id: projectId, message: text, dataset_id: selectedDatasetId || undefined };
      if (conversationId) body.conversation_id = conversationId;

      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) throw new Error("Stream failed");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalData: any = {};

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) continue;
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              const eventName = data.event;

              if (eventName === "understanding") {
                updateStage("understanding", "done");
              } else if (eventName === "planning") {
                updateStage("planning", "running");
              } else if (eventName === "selecting_skill") {
                updateStage("planning", "done");
                updateStage("selecting_skill", "running");
              } else if (eventName === "running_skill") {
                updateStage("selecting_skill", "done");
              } else if (eventName === "sql_generating") {
                updateStage("planning", "done");
                updateStage("sql_generating", "running");
              } else if (eventName === "querying") {
                updateStage("sql_generating", "done");
                updateStage("querying", "running");
              } else if (eventName === "analyzing") {
                updateStage("querying", "done");
                updateStage("analyzing", "running");
              } else if (eventName === "visualizing") {
                updateStage("analyzing", "done");
                updateStage("visualizing", "running");
              } else if (eventName === "insight") {
                setShowProgress(false);
                finalData = data;
              } else if (eventName === "conversation_created") {
                setConversationId(data.conversation_id);
              } else if (eventName === "done") {
                setShowProgress(false);
              } else if (eventName === "retry") {
                // Reset stages for retry attempt
                resetStages();
                setShowProgress(true);
                setLoading(true);
              } else if (eventName === "error") {
                setShowProgress(false);
                message.error(data.message || "Analysis failed");
              }
            } catch {}
          }
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: finalData.summary || "Analysis complete",
          sql: finalData.sql,
          columns: finalData.columns,
          rows: finalData.rows,
          row_count: finalData.row_count,
          charts: finalData.charts || [],
        },
      ]);
    } catch (err: any) {
      message.error(err.message || "Chat failed");
      setShowProgress(false);
    } finally {
      setLoading(false);
    }
  };

  const statusColors: Record<string, string> = {
    done: "#22c55e",
    running: "#d29922",
    pending: "#484f58",
  };

  const saveInsight = async (msg: ChatMessage) => {
    try {
      const userMsg = messages.find((m) => m.role === "user" && messages.indexOf(m) < messages.indexOf(msg));
      await api.post("/api/insights/", {
        project_id: projectId,
        question: userMsg?.content || "",
        content: {
          summary: msg.content,
          sql: msg.sql,
          columns: msg.columns,
          rows: msg.rows?.slice(0, 20),
          row_count: msg.row_count,
          charts: msg.charts || [],
        },
      });
      message.success("Insight saved");
    } catch {
      message.error("Failed to save insight");
    }
  };

  const saveAsWorkflow = async () => {
    try {
      const { data } = await api.get(`/api/runs/${projectId}?limit=1`);
      if (data.length > 0) {
        await api.post(`/api/workflows/from-run/${data[0].id}`);
        message.success("Saved as Workflow — check Workflows tab");
      } else {
        message.warning("No analysis run found to convert");
      }
    } catch {
      message.error("Failed to save workflow");
    }
  };

  const openInNotebook = async (msg: ChatMessage) => {
    try {
      const userMsg = messages.find((m) => m.role === "user" && messages.indexOf(m) < messages.indexOf(msg));
      const cells: any[] = [];
      cells.push({ cell_type: "markdown", content: `# Analysis: ${userMsg?.content || ""}`, sort_order: 0 });
      if (msg.sql) cells.push({ cell_type: "sql", content: msg.sql, sort_order: 1 });
      cells.push({ cell_type: "markdown", content: `## Result\n\n${msg.content}`, sort_order: cells.length });
      await api.post("/api/notebooks/", { project_id: projectId, cells });
      message.success("Opened in Notebook");
      window.open(`/project/${projectId}?tab=notebook`, "_self");
    } catch {
      message.error("Failed to create notebook");
    }
  };

  return (
    <div style={{ height: "calc(100vh - 130px)", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ fontSize: 16, color: "#666" }}>
          {conversationId ? "Continue conversation" : "New conversation"}
        </span>
        {messages.length > 0 && (
          <Button size="small" type="text" icon={<PlusOutlined />} onClick={newConversation} style={{ color: "#888" }}>
            New Chat
          </Button>
        )}
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 0",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {messages.length === 0 && !loading && (
          <div style={{ textAlign: "center", padding: "60px 20px" }}>
            <p style={{ color: "#aaa", fontSize: 17, margin: 0 }}>Ask a question about your data</p>
            <p style={{ color: "#666", fontSize: 16, marginTop: 4 }}>
              Example: "What is the total sales by region?"
            </p>
          </div>
        )}

        {messages.map((msg, i) =>
          msg.role === "user" ? (
            <div key={i} className="chat-message-user">
              {msg.content}
            </div>
          ) : (
            <div key={i} className="chat-message-ai">
              <div className="avatar">N</div>
              <div className="content">
                <ReactMarkdown>{msg.content}</ReactMarkdown>

                {/* Inline ECharts */}
                {msg.charts && msg.charts.length > 0 && msg.charts.map((chart, ci) => (
                  <div key={ci} style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 16, color: "#666", marginBottom: 4, textTransform: "uppercase" }}>
                      {chart.title}
                    </div>
                    <div style={{
                      background: "#0d0d0d",
                      borderRadius: 6,
                      padding: 8,
                      border: "0.5px solid #333",
                    }}>
                      <ReactECharts
                        option={chart.options}
                        style={{ height: 220, width: "100%" }}
                        theme="dark"
                        notMerge
                      />
                    </div>
                  </div>
                ))}

                {msg.sql && (
                  <pre
                    style={{
                      marginTop: 12,
                      background: "#0d0d0d",
                      padding: 10,
                      borderRadius: 6,
                      fontSize: 16,
                      overflow: "auto",
                      color: "#60a5fa",
                    }}
                  >
                    {msg.sql}
                  </pre>
                )}
                {msg.rows && msg.columns && msg.rows.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 16, color: "#888", marginBottom: 6 }}>
                      Results ({msg.rows.length} of {msg.row_count} rows)
                    </div>
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 16 }}>
                        <thead>
                          <tr>
                            {msg.columns.map((col: string) => (
                              <th
                                key={col}
                                style={{
                                  padding: "4px 10px",
                                  borderBottom: "1px solid #333",
                                  textAlign: "left",
                                  color: "#888",
                                  fontWeight: 500,
                                }}
                              >
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {msg.rows.slice(0, 10).map((row: any[], ri: number) => (
                            <tr key={ri}>
                              {row.map((val: any, ci: number) => (
                                <td
                                  key={ci}
                                  style={{
                                    padding: "3px 10px",
                                    borderBottom: "0.5px solid #222",
                                    color: "#ccc",
                                  }}
                                >
                                  {String(val)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                <Button
                  type="text"
                  size="small"
                  icon={<SaveOutlined />}
                  onClick={() => saveInsight(msg)}
                  style={{ marginTop: 8, color: "#888" }}
                >
                  Save Insight
                </Button>
                <Button
                  type="text"
                  size="small"
                  icon={<BookOutlined />}
                  onClick={() => openInNotebook(msg)}
                  style={{ marginTop: 8, color: "#888" }}
                >
                  Open in Notebook
                </Button>
                <Button
                  type="text"
                  size="small"
                  icon={<BranchesOutlined />}
                  onClick={saveAsWorkflow}
                  style={{ marginTop: 8, color: "#888" }}
                >
                  Save as Workflow
                </Button>
                <Button
                  type="text"
                  size="small"
                  icon={<ShareAltOutlined />}
                  onClick={() => navigate(`/project/${projectId}/dashboard`)}
                  style={{ marginTop: 8, color: "#888" }}
                >
                  Dashboard
                </Button>
                {msg.rows && msg.rows.length > 0 && (
                  <Button
                    type="text" size="small" icon={<DownloadOutlined />}
                    onClick={() => {
                      const escapeCsv = (v: string) => `"${String(v).replace(/"/g, '""')}"`;
                      const csv = [msg.columns?.map(escapeCsv).join(",") || "", ...msg.rows!.map((r: any[]) => r.map(escapeCsv).join(","))].join("\n");
                      const blob = new Blob([csv], { type: "text/csv" });
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(blob); a.download = "export.csv"; a.click();
                    }}
                    style={{ marginTop: 8, color: "#888" }}
                  >CSV</Button>
                )}
                {msg.content && (
                  <Button
                    type="text" size="small" icon={<CopyOutlined />}
                    onClick={() => { navigator.clipboard.writeText(msg.content!); message.success("Copied!"); }}
                    style={{ marginTop: 8, color: "#888" }}
                  >Copy</Button>
                )}
                {msg.content && (
                  <Button
                    type="text" size="small" icon={<DownloadOutlined />}
                    onClick={() => {
                      const md = `# Nexa Analysis\n\n${msg.content}\n\n${msg.sql ? "```sql\n" + msg.sql + "\n```" : ""}`;
                      const blob = new Blob([md], { type: "text/markdown" });
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(blob); a.download = "analysis.md"; a.click();
                    }}
                    style={{ marginTop: 8, color: "#888" }}
                  >MD</Button>
                )}
              </div>
            </div>
          )
        )}

        {showProgress && (
          <div className="chat-message-ai">
            <div className="avatar">N</div>
            <div className="chat-progress">
              {stages.map((stage) => (
                <div key={stage.name} className="chat-progress-row">
                  <div
                    className={`chat-progress-dot ${stage.status}${stage.status === "running" ? " pulse-dot" : ""}`}
                  />
                  <span
                    className="chat-progress-label"
                    style={{ color: stage.status === "pending" ? "#484f58" : stage.status === "running" ? "#e6edf3" : "#aaa" }}
                  >
                    {stage.label}
                  </span>
                  <span className="chat-progress-status" style={{ color: statusColors[stage.status] }}>
                    {stage.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {messages.length === 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
          {[
            { label: "Top 5 by sales", text: "各产品分类的销售额排名前5名" },
            { label: "Sales trend", text: "按月展示销售额变化趋势" },
            { label: "YOY comparison", text: "比较去年和今年的利润，做同比分析" },
            { label: "Data overview", text: "给我一份数据集的整体概览" },
            { label: "Correlation", text: "分析数值列之间的相关性" },
            { label: "Top 10 & Bottom 10", text: "找出销售额最高和最低的10个订单" },
          ].map((p) => (
            <Button
              key={p.label}
              size="small"
              type="default"
              style={{ fontSize: 15 }}
              onClick={() => { setInput(p.text); }}
            >
              {p.label}
            </Button>
          ))}
        </div>
      )}

      <div
        style={{
          padding: "12px 0",
          borderTop: "0.5px solid #333",
          display: "flex",
          gap: 8,
        }}
      >
        {datasets.length > 1 && (
          <div style={{ marginBottom: 8 }}>
            <Select
              value={selectedDatasetId}
              onChange={setSelectedDatasetId}
              style={{ minWidth: 200, background: "#1a1a1a" }}
              options={datasets.map((d) => ({ value: d.id, label: d.name }))}
              size="small"
            />
          </div>
        )}
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={handleSend}
          placeholder="Ask a question about your data..."
          disabled={loading}
          size="large"
          style={{ background: "#1a1a1a" }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={loading}
          size="large"
        />
      </div>
    </div>
  );
}
