import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Popconfirm, Select, message } from "antd";
import { PlusOutlined, CaretRightOutlined, DeleteOutlined, BranchesOutlined } from "@ant-design/icons";
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
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<{ id: string; name: string; row_count: number }[]>([]);
  const [cells, setCells] = useState<Cell[]>([]);
  const [sqlResults, setSqlResults] = useState<Record<string, any>>({});
  const [pythonResults, setPythonResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState<Record<string, boolean>>({});
  const navigate = useNavigate();

  useEffect(() => {
    api.get(`/api/datasets?project_id=${projectId}`).then(({ data }) => {
      setDatasets(Array.isArray(data) ? data : []);
    });
    api.get(`/api/notebooks/project/${projectId}`).then(({ data }) => {
      if (data.length > 0) {
        loadNotebook(data[0].id);
      }
    });
  }, [projectId]);

  const loadNotebook = async (id: string) => {
    const { data } = await api.get(`/api/notebooks/${id}`);
    setNotebookId(id);
    setDatasetId(data.dataset_id || null);
    setCells(data.cells);
  };

  const createNotebook = async () => {
    const { data } = await api.post("/api/notebooks/", { project_id: projectId, dataset_id: datasetId });
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
      message.error("单元格删除失败，请稍后重试");
    }
  };

  const updateCell = async (cellId: string, content: string) => {
    await api.put(`/api/notebooks/cells/${cellId}`, { content });
  };

  const runSql = async (cellId: string, sql: string) => {
    setLoading((p) => ({ ...p, [cellId]: true }));
    try {
      await updateCell(cellId, sql);
      const { data } = await api.post(`/api/notebooks/cells/${cellId}/execute`);
      setSqlResults((p) => ({ ...p, [cellId]: data }));
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "查询失败";
      message.error(msg || "查询失败");
    } finally {
      setLoading((p) => ({ ...p, [cellId]: false }));
    }
  };

  const runPython = async (cellId: string, code: string) => {
    setLoading((p) => ({ ...p, [cellId]: true }));
    try {
      await updateCell(cellId, code);
      const { data } = await api.post(`/api/notebooks/cells/${cellId}/execute`);
      setPythonResults((p) => ({ ...p, [cellId]: data }));
      if (data.error) message.error(data.error);
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Python 执行失败";
      message.error(msg || "Python 执行失败");
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
        <p style={{ color: "#888", marginBottom: 16 }}>还没有分析笔记</p>
        <Button onClick={createNotebook} type="primary">创建分析笔记</Button>
      </div>
    );
  }

  return (
    <div style={{ padding: "12px 0" }}>
      <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
        <Select
          value={datasetId}
          placeholder="选择分析数据集"
          style={{ minWidth: 260 }}
          options={datasets.map((dataset) => ({ value: dataset.id, label: `${dataset.name}（${dataset.row_count.toLocaleString()} 行）` }))}
          onChange={async (value) => {
            setDatasetId(value);
            if (notebookId) await api.put(`/api/notebooks/${notebookId}`, { dataset_id: value });
            setSqlResults({});
            setPythonResults({});
          }}
        />
        <Button size="small" onClick={() => addCell("markdown")} icon={<PlusOutlined />}>Markdown</Button>
        <Button size="small" onClick={() => addCell("sql")} icon={<PlusOutlined />}>SQL</Button>
        <Button size="small" onClick={() => addCell("python")} icon={<PlusOutlined />}>Python</Button>
        {notebookId && (
          <Button size="small" icon={<BranchesOutlined />} style={{ marginLeft: "auto" }}
            onClick={async () => {
              try {
                if (!datasetId) {
                  message.warning("请先选择数据集");
                  return;
                }
                const sqlCells = cells.filter((cell) => cell.cell_type === "sql" && cell.content.trim());
                if (!sqlCells.length) {
                  message.warning("没有可转换的 SQL 单元格");
                  return;
                }
                if (cells.some((cell) => cell.cell_type === "python" && cell.content.trim())) {
                  message.warning("Python 单元格不能无损转换为工作流，请先移除或改写为 SQL");
                  return;
                }
                const wf = await api.post("/api/workflows", {
                  name: "由分析笔记转换",
                  project_id: projectId,
                  inputs: { dataset_ids: [datasetId] },
                  steps: sqlCells.map((cell, index) => ({
                    type: "sql",
                    sort_order: index,
                    config: { sql_template: cell.content },
                    description: "来自分析笔记",
                  })),
                });
                message.success("已转换为工作流");
                navigate(`/project/${projectId}/workflow/${wf.data.id}`);
              } catch { message.error("转换失败，请稍后重试"); }
            }}
          >保存为工作流</Button>
        )}
      </div>

      {!datasetId && (
        <Alert
          type="warning"
          showIcon
          message="请选择数据集后再运行单元格"
          description="SQL 中的 data 表和 Python 中的 columns、rows 都会固定来自这里选择的数据集。"
          style={{ marginBottom: 12 }}
        />
      )}

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
                    {isEditing ? "预览" : "编辑"}
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
                    disabled={!datasetId}
                  >
                    运行
                  </Button>
                )}
                {cell.cell_type === "python" && (
                  <Button
                    size="small"
                    icon={<CaretRightOutlined />}
                    onClick={() => runPython(cell.id, cell.content)}
                    loading={loading[cell.id]}
                    disabled={!datasetId}
                  >
                    运行
                  </Button>
                )}
                <Popconfirm
                  title="删除这个单元格？"
                  onConfirm={() => deleteCell(cell.id)}
                  okText="删除"
                  cancelText="取消"
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            </div>

            {/* Content: edit mode or preview */}
            {cell.cell_type === "markdown" && !isEditing ? (
              <div style={{ color: "#ccc", fontSize: 16, lineHeight: 1.6, padding: "4px 0" }}>
                <ReactMarkdown>{cell.content || "*空单元格*"}</ReactMarkdown>
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
                    ? "输入 Markdown..."
                    : cell.cell_type === "sql"
                    ? "SELECT * FROM ..."
                    : "# Python 代码..."
                }
              />
            )}

            {/* SQL Results */}
            {sqlResults[cell.id] && (
              <div style={{ marginTop: 8, overflowX: "auto" }}>
                <div style={{ fontSize: 16, color: "#666", marginBottom: 4 }}>
                  {sqlResults[cell.id].row_count != null ? `${sqlResults[cell.id].row_count} 行` : ""}
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
                    {(sqlResults[cell.id].rows || []).slice(0, 50).map((row: unknown[], ri: number) => (
                      <tr key={ri}>
                        {row.map((val: unknown, ci: number) => (
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
                  {pythonResults[cell.id].error
                    ? pythonResults[cell.id].error
                    : typeof pythonResults[cell.id].output === "string"
                    ? pythonResults[cell.id].output || "运行完成，无输出"
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
