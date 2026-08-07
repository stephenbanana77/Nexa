import { useEffect, useState } from "react";
import { Button, Popconfirm, message } from "antd";
import { PlusOutlined, CaretRightOutlined, DeleteOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import api from "../api/client";

interface Cell {
  id: string;
  cell_type: "markdown" | "sql" | "python";
  content: string;
  sort_order: number;
}

export default function NotebookPage({ projectId }: { projectId: string }) {
  const [notebookId, setNotebookId] = useState<string | null>(null);
  const [cells, setCells] = useState<Cell[]>([]);
  const [sqlResults, setSqlResults] = useState<Record<string, any>>({});
  const [pythonResults, setPythonResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api.get(`/api/notebooks/project/${projectId}`).then(({ data }) => {
      if (data.length > 0) {
        loadNotebook(data[0].id);
      }
    });
  }, [projectId]);

  const loadNotebook = async (id: string) => {
    const { data } = await api.get(`/api/notebooks/${id}`);
    setNotebookId(id);
    setCells(data.cells);
  };

  const createNotebook = async () => {
    const { data } = await api.post("/api/notebooks/", { project_id: projectId });
    loadNotebook(data.id);
  };

  const addCell = async (type: string) => {
    if (!notebookId) return;
    const { data } = await api.post(`/api/notebooks/${notebookId}/cells`, {
      cell_type: type, content: "", sort_order: cells.length,
    });
    const newCell = { ...data, sort_order: data.sort_order ?? cells.length };
    setCells((prev) => [...prev, newCell]);
    setEditing((prev) => ({ ...prev, [newCell.id]: true }));
  };

  const deleteCell = async (cellId: string) => {
    try {
      await api.delete(`/api/notebooks/cells/${cellId}`);
      setCells((prev) => prev.filter((c) => c.id !== cellId));
      setEditing((prev) => {
        const next = { ...prev };
        delete next[cellId];
        return next;
      });
    } catch {
      message.error("Failed to delete cell");
    }
  };

  const updateCell = async (cellId: string, content: string) => {
    await api.put(`/api/notebooks/cells/${cellId}`, { content });
  };

  const runSql = async (cellId: string, sql: string) => {
    setLoading((p) => ({ ...p, [cellId]: true }));
    try {
      const datasets = await api.get(`/api/datasets?project_id=${projectId}`);
      if ((datasets.data as any[]).length === 0) {
        message.error("No dataset found");
        return;
      }
      const { data } = await api.post(`/api/datasets/by-id/${(datasets.data as any[])[0].id}/query`, { sql });
      setSqlResults((p) => ({ ...p, [cellId]: data }));
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Query failed");
    } finally {
      setLoading((p) => ({ ...p, [cellId]: false }));
    }
  };

  const runPython = async (cellId: string, code: string) => {
    setLoading((p) => ({ ...p, [cellId]: true }));
    try {
      const { data } = await api.post(`/api/notebooks/cells/${cellId}/execute`, { code });
      setPythonResults((p) => ({ ...p, [cellId]: data }));
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Python execution failed");
    } finally {
      setLoading((p) => ({ ...p, [cellId]: false }));
    }
  };

  const toggleEdit = (cellId: string) => {
    setEditing((prev) => ({ ...prev, [cellId]: !prev[cellId] }));
  };

  if (!notebookId) {
    return (
      <div style={{ padding: "40px 0", textAlign: "center" }}>
        <p style={{ color: "#888", marginBottom: 16 }}>No notebooks yet</p>
        <Button onClick={createNotebook} type="primary">Create Notebook</Button>
      </div>
    );
  }

  return (
    <div style={{ padding: "12px 0" }}>
      <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
        <Button size="small" onClick={() => addCell("markdown")} icon={<PlusOutlined />}>Markdown</Button>
        <Button size="small" onClick={() => addCell("sql")} icon={<PlusOutlined />}>SQL</Button>
        <Button size="small" onClick={() => addCell("python")} icon={<PlusOutlined />}>Python</Button>
      </div>

      {cells.map((cell) => {
        const isEditing = editing[cell.id] !== false; // default: editing=true for new cells
        return (
          <div key={cell.id} style={{ marginBottom: 12, background: "#1a1a1a", borderRadius: 8, border: "1px solid #333", padding: 12 }}>
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{
                  fontSize: 16,
                  color: "#888",
                  background: "#252525",
                  padding: "1px 6px",
                  borderRadius: 4,
                  textTransform: "uppercase",
                  fontWeight: 500,
                }}>
                  {cell.cell_type}
                </span>
                {cell.cell_type === "markdown" && (
                  <Button size="small" type="text" onClick={() => toggleEdit(cell.id)} style={{ color: "#888", fontSize: 16 }}>
                    {isEditing ? "Preview" : "Edit"}
                  </Button>
                )}
              </div>
              <div style={{ display: "flex", gap: 4 }}>
                {cell.cell_type === "sql" && (
                  <Button
                    size="small"
                    icon={<CaretRightOutlined />}
                    onClick={() => runSql(cell.id, cell.content)}
                    loading={loading[cell.id]}
                  >
                    Run
                  </Button>
                )}
                {cell.cell_type === "python" && (
                  <Button
                    size="small"
                    icon={<CaretRightOutlined />}
                    onClick={() => runPython(cell.id, cell.content)}
                    loading={loading[cell.id]}
                  >
                    Run
                  </Button>
                )}
                <Popconfirm
                  title="Delete this cell?"
                  onConfirm={() => deleteCell(cell.id)}
                  okText="Delete"
                  cancelText="Cancel"
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            </div>

            {/* Content: edit mode or preview */}
            {cell.cell_type === "markdown" && !isEditing ? (
              <div style={{ color: "#ccc", fontSize: 16, lineHeight: 1.6, padding: "4px 0" }}>
                <ReactMarkdown>{cell.content || "*Empty cell*"}</ReactMarkdown>
              </div>
            ) : (
              <textarea
                value={cell.content}
                onChange={(e) => {
                  setCells((prev) => prev.map((c) => (c.id === cell.id ? { ...c, content: e.target.value } : c)));
                }}
                onBlur={() => updateCell(cell.id, cell.content)}
                rows={cell.content ? Math.min(cell.content.split("\n").length + 1, 12) : 2}
                style={{
                  width: "100%",
                  background: "#0d0d0d",
                  color: cell.cell_type === "sql" ? "#60a5fa" : cell.cell_type === "python" ? "#a78bfa" : "#ddd",
                  border: "none",
                  borderRadius: 4,
                  padding: 8,
                  fontFamily: cell.cell_type === "markdown" ? "inherit" : "monospace",
                  fontSize: 16,
                  resize: "vertical",
                  lineHeight: 1.6,
                }}
                placeholder={
                  cell.cell_type === "markdown"
                    ? "Write Markdown..."
                    : cell.cell_type === "sql"
                    ? "SELECT * FROM ..."
                    : "# Python code..."
                }
              />
            )}

            {/* SQL Results */}
            {sqlResults[cell.id] && (
              <div style={{ marginTop: 8, overflowX: "auto" }}>
                <div style={{ fontSize: 16, color: "#666", marginBottom: 4 }}>
                  {sqlResults[cell.id].row_count != null ? `${sqlResults[cell.id].row_count} rows` : ""}
                </div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 16 }}>
                  <thead>
                    <tr>
                      {(sqlResults[cell.id].columns || []).map((col: string) => (
                        <th key={col} style={{ padding: "4px 10px", borderBottom: "1px solid #333", textAlign: "left", color: "#888" }}>
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(sqlResults[cell.id].rows || []).slice(0, 50).map((row: any[], ri: number) => (
                      <tr key={ri}>
                        {row.map((val: any, ci: number) => (
                          <td key={ci} style={{ padding: "3px 10px", borderBottom: "0.5px solid #222", color: "#ccc" }}>
                            {String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Python Results */}
            {pythonResults[cell.id] && (
              <div style={{ marginTop: 8 }}>
                <pre style={{
                  background: "#0d0d0d",
                  padding: 10,
                  borderRadius: 6,
                  fontSize: 16,
                  color: "#a78bfa",
                  overflow: "auto",
                  maxHeight: 300,
                }}>
                  {typeof pythonResults[cell.id].output === "string"
                    ? pythonResults[cell.id].output
                    : JSON.stringify(pythonResults[cell.id], null, 2)}
                </pre>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
