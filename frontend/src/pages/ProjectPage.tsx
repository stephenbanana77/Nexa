import { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Tabs, Upload, Button, Table, message, Spin } from "antd";
import { UploadOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import api from "../api/client";
import ChatPage from "./ChatPage";
import InsightsPage from "./InsightsPage";
import NotebookPage from "./NotebookPage";

interface SchemaField {
  name: string;
  type: string;
  missing_pct: number;
}

interface PreviewData {
  columns: string[];
  rows: any[][];
  row_count: number;
}

interface Dataset {
  id: string;
  name: string;
  row_count: number;
  column_count: number;
  schema_info: SchemaField[];
  preview?: PreviewData;
  created_at: string;
}

interface ProjectInfo {
  id: string;
  name: string;
}

export default function ProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [uploading, setUploading] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);

  useEffect(() => {
    api.get(`/api/projects/${projectId}`).then(({ data }) => setProject(data)).catch(() => navigate("/"));
  }, [projectId]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const { data } = await api.post(`/api/datasets/upload?project_id=${projectId}`, formData);
      setDatasets((prev) => [data, ...prev]);
      if (data.preview) setPreviewData(data.preview);
      message.success(`Uploaded: ${file.name}`);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
    return false;
  };

  const loadPreview = async (datasetId: string) => {
    try {
      const { data } = await api.get(`/api/datasets/${datasetId}/preview?limit=1000`);
      setPreviewData(data);
    } catch {
      message.error("Failed to load preview");
    }
  };

  const schemaColumns = [
    { title: "Column", dataIndex: "name", key: "name" },
    { title: "Type", dataIndex: "type", key: "type",
      render: (t: string) => <span style={{ color: "#60a5fa" }}>{t}</span> },
    { title: "Missing", dataIndex: "missing_pct", key: "missing_pct",
      render: (p: number) => <span style={{ color: p > 10 ? "#ef4444" : "#888" }}>{p}%</span> },
  ];

  const gridColumns = useMemo(
    () => previewData?.columns.map((col) => ({ field: col, headerName: col })) || [],
    [previewData]
  );

  const gridRows = useMemo(
    () => previewData?.rows.map((row) => {
      const obj: Record<string, any> = {};
      previewData.columns.forEach((col, i) => { obj[col] = row[i]; });
      return obj;
    }) || [],
    [previewData]
  );

  if (!project) {
    return (
      <div style={{ minHeight: "100vh", background: "#0d0d0d", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  const latestDataset = datasets[0];

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      <div style={{ background: "#1a1a1a", padding: "12px 24px", display: "flex", alignItems: "center", gap: 16, borderBottom: "1px solid #333" }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate("/")} style={{ color: "#888" }} />
        <span style={{ color: "#fff", fontWeight: 500, fontSize: 15 }}>{project.name}</span>
      </div>
      <Tabs defaultActiveKey="chat" style={{ padding: "0 24px" }} tabBarStyle={{ borderBottom: "1px solid #333" }}
        items={[
          { key: "chat", label: <span style={{ color: "#60a5fa" }}>Chat</span>,
            children: <div style={{ padding: "12px 0", maxWidth: 800 }}><ChatPage projectId={projectId!} /></div> },
          { key: "data", label: <span>Data</span>,
            children: <div style={{ padding: "24px 0", maxWidth: 900 }}>
              <Upload beforeUpload={handleUpload as any} showUploadList={false} accept=".csv,.xlsx,.xls">
                <Button icon={<UploadOutlined />} loading={uploading} size="large" style={{ marginBottom: 20 }}>Upload CSV / Excel</Button>
              </Upload>
              {latestDataset && <>
                <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
                  {[{ label: "Dataset", value: latestDataset.name }, { label: "Rows", value: latestDataset.row_count.toLocaleString() }, { label: "Columns", value: latestDataset.column_count }].map((m) => (
                    <div key={m.label} style={{ background: "#1f1f1f", borderRadius: 8, padding: "12px 18px", flex: 1 }}>
                      <div style={{ fontSize: 11, color: "#666" }}>{m.label}</div>
                      <div style={{ fontSize: 15, fontWeight: 500, color: "#ddd" }}>{m.value}</div>
                    </div>))}
                </div>
                {latestDataset.schema_info && <>
                  <div style={{ color: "#aaa", fontSize: 13, marginBottom: 8 }}>Schema</div>
                  <Table columns={schemaColumns} dataSource={latestDataset.schema_info.map((s, i) => ({ ...s, key: i }))} pagination={false} size="small" />
                </>}
                {previewData && <>
                  <div style={{ color: "#aaa", fontSize: 13, margin: "20px 0 8px" }}>Preview (first 1,000 of {latestDataset.row_count.toLocaleString()} rows)</div>
                  <div className="ag-theme-alpine-dark" style={{ height: 400, width: "100%", borderRadius: 8, overflow: "hidden", border: "1px solid #333" }}>
                    <AgGridReact columnDefs={gridColumns} rowData={gridRows} rowHeight={32} headerHeight={36} suppressCellFocus />
                  </div>
                </>}
                {!previewData && latestDataset.schema_info && <Button onClick={() => loadPreview(latestDataset.id)} style={{ marginTop: 12 }}>Load Data Preview</Button>}
              </>}
            </div> },
          { key: "insights", label: <span>Insights</span>,
            children: <div style={{ padding: "12px 0", maxWidth: 700 }}><InsightsPage projectId={projectId!} /></div> },
          { key: "notebook", label: <span>Notebook</span>,
            children: <div style={{ padding: "12px 0", maxWidth: 800 }}><NotebookPage projectId={projectId!} /></div> },
        ]}
      />
    </div>
  );
}
