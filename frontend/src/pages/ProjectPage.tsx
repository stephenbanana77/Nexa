import { lazy, Suspense, useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Tabs, Upload, Button, Table, Select, message, Spin, Modal } from "antd";
import { UploadOutlined, ArrowLeftOutlined, DatabaseOutlined } from "@ant-design/icons";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import api from "../api/client";
import MySQLConnectModal from "../components/MySQLConnectModal";

const ChatPage = lazy(() => import("./ChatPage"));
const InsightsPage = lazy(() => import("./InsightsPage"));
const NotebookPage = lazy(() => import("./NotebookPage"));
const RunHistoryPage = lazy(() => import("./RunHistoryPage"));
const WorkflowPage = lazy(() => import("./WorkflowPage"));
const SemanticLayerPage = lazy(() => import("./SemanticLayerPage"));
const ReportsPage = lazy(() => import("./ReportsPage"));
const SettingsPage = lazy(() => import("./SettingsPage"));

function TabFallback() {
  return (
    <div style={{ minHeight: 240, display: "grid", placeItems: "center" }}>
      <Spin />
    </div>
  );
}

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
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [uploadPreview, setUploadPreview] = useState<any>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [mysqlModalOpen, setMysqlModalOpen] = useState(false);

  useEffect(() => {
    api.get(`/api/projects/${projectId}`).then(({ data }) => setProject(data)).catch(() => navigate("/"));
    // Load existing datasets
    api.get(`/api/datasets?project_id=${projectId}`).then(({ data }) => {
      const list = data.items || data;
      if (list.length > 0) {
        setDatasets(list);
        setSelectedDatasetId(list[0].id);
      }
    }).catch(() => {});
  }, [navigate, projectId]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      // Preview first
      const previewRes = await api.post("/api/datasets/preview", formData);
      setUploadPreview(previewRes.data);
      setPendingFile(file);
      setPreviewModalOpen(true);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Preview failed");
    } finally {
      setUploading(false);
    }
    return false;
  };

  const confirmUpload = async () => {
    if (!pendingFile) return;
    setPreviewModalOpen(false);
    setUploading(true);
    const formData = new FormData();
    formData.append("file", pendingFile);
    try {
      const { data } = await api.post(`/api/datasets/upload?project_id=${projectId}`, formData);
      setDatasets((prev) => [data, ...prev]);
      setSelectedDatasetId(data.id);
      if (data.preview) setPreviewData(data.preview);
      message.success(`Uploaded: ${pendingFile.name}`);
      setPendingFile(null);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const loadPreview = async (datasetId: string) => {
    try {
      const { data } = await api.get(`/api/datasets/by-id/${datasetId}/preview?limit=1000`);
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

  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId);

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      <div style={{ background: "#1a1a1a", padding: "12px 24px", display: "flex", alignItems: "center", gap: 16, borderBottom: "1px solid #333" }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate("/")} style={{ color: "#888" }} />
        <span style={{ color: "#fff", fontWeight: 500, fontSize: 17 }}>{project.name}</span>
      </div>
      <Tabs defaultActiveKey="chat" style={{ padding: "0 24px" }} tabBarStyle={{ borderBottom: "1px solid #333" }}
        items={[
          { key: "chat", label: <span style={{ color: "#60a5fa" }}>Chat</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><ChatPage projectId={projectId!} /></Suspense></div> },
          { key: "data", label: <span>Data</span>,
            children: <div style={{ padding: "24px 0", width: "100%" }}>
              <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
                <Upload beforeUpload={handleUpload as any} showUploadList={false} accept=".csv,.xlsx,.xls">
                  <Button icon={<UploadOutlined />} loading={uploading} size="large">Upload CSV / Excel</Button>
                </Upload>
                <Button icon={<DatabaseOutlined />} size="large" onClick={() => setMysqlModalOpen(true)}>Connect MySQL</Button>
              </div>
              {datasets.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <span style={{ color: "#888", fontSize: 16, marginRight: 8 }}>Dataset:</span>
                  <Select
                    value={selectedDatasetId}
                    onChange={(val) => {
                      setSelectedDatasetId(val);
                      setPreviewData(null);
                    }}
                    style={{ minWidth: 240, width: "100%" }}
                    options={datasets.map((d) => ({ label: d.name, value: d.id }))}
                  />
                </div>
              )}
              {selectedDataset && <>
                <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
                  {[{ label: "Dataset", value: selectedDataset.name }, { label: "Rows", value: selectedDataset.row_count.toLocaleString() }, { label: "Columns", value: selectedDataset.column_count }].map((m) => (
                    <div key={m.label} style={{ background: "#1f1f1f", borderRadius: 8, padding: "12px 18px", flex: 1 }}>
                      <div style={{ fontSize: 16, color: "#666" }}>{m.label}</div>
                      <div style={{ fontSize: 17, fontWeight: 500, color: "#ddd" }}>{m.value}</div>
                    </div>))}
                </div>
                {selectedDataset.schema_info && <>
                  <div style={{ color: "#aaa", fontSize: 16, marginBottom: 8 }}>Schema</div>
                  <Table columns={schemaColumns} dataSource={selectedDataset.schema_info.map((s, i) => ({ ...s, key: i }))} pagination={false} size="small" />
                </>}
                {previewData && <>
                  <div style={{ color: "#aaa", fontSize: 16, margin: "20px 0 8px" }}>Preview (first 1,000 of {selectedDataset.row_count.toLocaleString()} rows)</div>
                  <div className="ag-theme-alpine-dark" style={{ height: 400, width: "100%", borderRadius: 8, overflow: "hidden", border: "1px solid #333" }}>
                    <AgGridReact columnDefs={gridColumns} rowData={gridRows} rowHeight={32} headerHeight={36} suppressCellFocus />
                  </div>
                </>}
                {!previewData && selectedDataset.schema_info && <Button onClick={() => loadPreview(selectedDataset.id)} style={{ marginTop: 12 }}>Load Data Preview</Button>}
              </>}
            </div> },
          { key: "insights", label: <span>Insights</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><InsightsPage projectId={projectId!} /></Suspense></div> },
          { key: "semantic", label: <span>Semantic Layer</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><SemanticLayerPage projectId={projectId!} /></Suspense></div> },
          { key: "reports", label: <span>Reports</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><ReportsPage projectId={projectId!} /></Suspense></div> },
          { key: "notebook", label: <span>Notebook</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><NotebookPage projectId={projectId!} /></Suspense></div> },
          { key: "history", label: <span>History</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><RunHistoryPage /></Suspense></div> },
          { key: "workflows", label: <span>Workflows</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><WorkflowPage /></Suspense></div> },
          { key: "settings", label: <span>Settings</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><SettingsPage /></Suspense></div> },
        ]}
      />
      <MySQLConnectModal
        projectId={projectId!}
        open={mysqlModalOpen}
        onClose={() => setMysqlModalOpen(false)}
        onConnected={(data) => {
          setDatasets((prev) => [{
            id: data.id,
            name: data.name,
            row_count: data.row_count,
            column_count: 0,
            schema_info: [],
            created_at: new Date().toISOString(),
          }, ...prev]);
          setSelectedDatasetId(data.id);
        }}
      />

      <Modal
        title="Confirm Upload"
        open={previewModalOpen}
        onCancel={() => { setPreviewModalOpen(false); setPendingFile(null); }}
        onOk={confirmUpload}
        okText="Upload"
        width={700}
        styles={{ body: { padding: 16, background: "#1a1a1a" } }}
      >
        {uploadPreview && (
          <div>
            <p style={{ color: "#888", marginBottom: 12 }}>
              {uploadPreview.file_name} ({Math.round(uploadPreview.file_size / 1024)} KB)
              &nbsp;· Encoding: {uploadPreview.encoding}
              &nbsp;· {uploadPreview.columns?.length || 0} columns, {uploadPreview.total_rows_in_sample}+ rows
            </p>
            <Table
              dataSource={uploadPreview.preview_rows?.slice(0, 10).map((r: any[], i: number) => {
                const row: Record<string, any> = { _key: i };
                uploadPreview.columns.forEach((c: any, j: number) => { row[c.name] = String(r[j] ?? "").slice(0, 50); });
                return row;
              }) || []}
              columns={(uploadPreview.columns || []).map((c: any) => ({ title: c.name, dataIndex: c.name, key: c.name, ellipsis: true }))}
              size="small"
              pagination={false}
              scroll={{ x: "max-content" }}
              rowKey="_key"
            />
          </div>
        )}
      </Modal>
    </div>
  );
}
