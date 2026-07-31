import { useEffect, useState } from "react";
import { Button, Input, message } from "antd";
import { PlusOutlined, CaretRightOutlined } from "@ant-design/icons";
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
  const [loading, setLoading] = useState<Record<string, boolean>>({});

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
    setCells((prev) => [...prev, { ...data, sort_order: data.sort_order ?? prev.length }]);
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
      const { data } = await api.post(`/api/datasets/${(datasets.data as any[])[0].id}/query`, { sql });
      setSqlResults((p) => ({ ...p, [cellId]: data }));
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Query failed");
    } finally {
      setLoading((p) => ({ ...p, [cellId]: false }));
    }
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

      {cells.map((cell) => (
        <div key={cell.id} style={{ marginBottom: 12, background: "#1a1a1a", borderRadius: 8, border: "1px solid #333", padding: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 11, color: "#666", textTransform: "uppercase" }}>{cell.cell_type}</span>
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
          </div>
          <Input.TextArea
            value={cell.content}
            onChange={(e) => {
              setCells((prev) => prev.map((c) => (c.id === cell.id ? { ...c, content: e.target.value } : c)));
            }}
            onBlur={() => updateCell(cell.id, cell.content)}
            autoSize={{ minRows: 2, maxRows: 12 }}
            style={{
              background: "#0d0d0d",
              color: cell.cell_type === "sql" ? "#60a5fa" : "#ddd",
              border: "none",
              fontFamily: cell.cell_type === "markdown" ? "inherit" : "monospace",
              fontSize: 13,
            }}
          />
          {sqlResults[cell.id] && (
            <div style={{ marginTop: 8, overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
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
                  {(sqlResults[cell.id].rows || []).slice(0, 20).map((row: any[], ri: number) => (
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
        </div>
      ))}
    </div>
  );
}
