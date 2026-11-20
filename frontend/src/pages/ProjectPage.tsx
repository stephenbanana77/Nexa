import { lazy, Suspense, useEffect, useState, useMemo } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Tabs, Upload, Button, Input, Table, Select, Tag, message, Spin, Modal, Dropdown, Popconfirm } from "antd";
import { UploadOutlined, ArrowLeftOutlined, DatabaseOutlined, SafetyCertificateOutlined, MoreOutlined, DeleteOutlined } from "@ant-design/icons";
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
  source_type?: string;
}

interface ProjectInfo {
  id: string;
  name: string;
}

export default function ProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [uploadPreview, setUploadPreview] = useState<any>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [mysqlModalOpen, setMysqlModalOpen] = useState(false);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [qualityData, setQualityData] = useState<any>(null);
  const [querySql, setQuerySql] = useState("SELECT * FROM data LIMIT 100");
  const [queryResult, setQueryResult] = useState<PreviewData | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);

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
      message.error(err.response?.data?.detail || "文件预览失败，请检查格式后重试");
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
      message.success(`已上传：${pendingFile.name}`);
      setPendingFile(null);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "上传失败，请稍后重试");
    } finally {
      setUploading(false);
    }
  };

  const loadPreview = async (datasetId: string) => {
    try {
      const { data } = await api.get(`/api/datasets/by-id/${datasetId}/preview?limit=1000`);
      setPreviewData(data);
    } catch {
      message.error("数据预览加载失败，请稍后重试");
    }
  };

  const runQualityCheck = async (datasetId: string) => {
    setQualityLoading(true);
    try {
      const { data } = await api.get(`/api/datasets/by-id/${datasetId}/quality`);
      setQualityData(data);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "数据质量检查失败，请稍后重试");
    } finally {
      setQualityLoading(false);
    }
  };

  const deleteDataset = async (datasetId: string) => {
    try {
      await api.delete(`/api/datasets/by-id/${datasetId}`);
      const next = datasets.filter((dataset) => dataset.id !== datasetId);
      setDatasets(next);
      setSelectedDatasetId(next[0]?.id || null);
      setPreviewData(null);
      setQualityData(null);
      message.success("数据集已删除");
    } catch (err: any) {
      message.error(err.response?.data?.detail || "数据集删除失败");
    }
  };

  const runDirectQuery = async (datasetId: string) => {
    if (!querySql.trim()) return;
    setQueryLoading(true);
    try {
      const { data } = await api.post(`/api/datasets/by-id/${datasetId}/query`, { sql: querySql });
      setQueryResult(data);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "SQL 查询失败");
    } finally {
      setQueryLoading(false);
    }
  };

  const schemaColumns = [
    { title: "字段", dataIndex: "name", key: "name" },
    { title: "类型", dataIndex: "type", key: "type",
      render: (t: string) => <span style={{ color: "#60a5fa" }}>{t}</span> },
    { title: "缺失率", dataIndex: "missing_pct", key: "missing_pct",
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
  const activeTab = searchParams.get("tab") || "chat";
  const advancedTabLabels: Record<string, string> = {
    insights: "已保存洞察",
    semantic: "指标定义",
    notebook: "分析笔记",
    settings: "模型设置",
  };

  const openTab = (key: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", key);
    if (key !== "chat") next.delete("question");
    setSearchParams(next);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d" }}>
      <div style={{ background: "#171a17", padding: "12px 24px", display: "flex", alignItems: "center", gap: 16, borderBottom: "1px solid #333" }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate("/")} style={{ color: "#888" }} aria-label="返回首页" title="返回首页" />
        <span style={{ color: "#fff", fontWeight: 500, fontSize: 17 }}>{project.name === "Sample - Superstore Demo" ? "示例 - Superstore 演示" : project.name}</span>
        <Dropdown
          trigger={["click"]}
          menu={{
            items: [
              { key: "semantic", label: "指标定义" },
              { key: "insights", label: "已保存洞察" },
              { key: "notebook", label: "分析笔记" },
              { key: "skills", label: "技能" },
              { key: "settings", label: "模型设置" },
            ],
            onClick: ({ key }) => key === "skills" ? navigate(`/project/${projectId}/skills`) : openTab(key),
          }}
        >
          <Button type="text" icon={<MoreOutlined />} style={{ marginLeft: "auto", color: "#999" }}>高级工具</Button>
        </Dropdown>
      </div>
      <Tabs
        activeKey={activeTab}
        onChange={openTab}
        style={{ padding: "0 24px" }}
        tabBarStyle={{ borderBottom: "1px solid #333" }}
        items={[
          { key: "chat", label: <span style={{ color: "#f08a67" }}>Agent</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><ChatPage projectId={projectId!} /></Suspense></div> },
          { key: "data", label: <span>数据</span>,
            children: <div style={{ padding: "24px 0", width: "100%" }}>
              <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
                <Upload beforeUpload={handleUpload as any} showUploadList={false} accept=".csv,.xlsx,.xls">
                  <Button icon={<UploadOutlined />} loading={uploading} size="large">上传 CSV / Excel</Button>
                </Upload>
                <Button icon={<DatabaseOutlined />} size="large" onClick={() => setMysqlModalOpen(true)}>连接 MySQL</Button>
                {selectedDatasetId && <Button icon={<SafetyCertificateOutlined />} loading={qualityLoading} onClick={() => runQualityCheck(selectedDatasetId)}>检查数据质量</Button>}
                {selectedDatasetId && (
                  <Popconfirm title="删除这个数据集？" description="原始上传文件也会删除，此操作不可撤销。" onConfirm={() => deleteDataset(selectedDatasetId)}>
                    <Button danger icon={<DeleteOutlined />} aria-label="删除数据集" title="删除数据集" />
                  </Popconfirm>
                )}
              </div>
              {datasets.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <span style={{ color: "#888", fontSize: 16, marginRight: 8 }}>数据集：</span>
                  <Select
                    value={selectedDatasetId}
                    onChange={(val) => {
                      setSelectedDatasetId(val);
                      setPreviewData(null);
                      setQualityData(null);
                      setQueryResult(null);
                    }}
                    style={{ minWidth: 240, width: "100%" }}
                    options={datasets.map((d) => ({ label: `${d.name}（${d.row_count.toLocaleString()} 行）`, value: d.id }))}
                  />
                </div>
              )}
              {selectedDataset && <>
                <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
                  {[{ label: "数据集", value: selectedDataset.name }, { label: "行数", value: selectedDataset.row_count.toLocaleString() }, { label: "字段数", value: selectedDataset.column_count }].map((m) => (
                    <div key={m.label} style={{ background: "#1f1f1f", borderRadius: 8, padding: "12px 18px", flex: 1 }}>
                      <div style={{ fontSize: 16, color: "#666" }}>{m.label}</div>
                      <div style={{ fontSize: 17, fontWeight: 500, color: "#ddd" }}>{m.value}</div>
                    </div>))}
                </div>
                {selectedDataset.schema_info && <>
                  <div style={{ color: "#aaa", fontSize: 16, marginBottom: 8 }}>字段结构</div>
                  <Table columns={schemaColumns} dataSource={selectedDataset.schema_info.map((s, i) => ({ ...s, key: i }))} pagination={false} size="small" />
                </>}
                {qualityData && qualityData.status && (
                  <div style={{ marginTop: 20, background: "#1f1f1f", borderRadius: 8, padding: 16 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <span style={{ color: "#aaa", fontSize: 16 }}>数据质量门禁</span>
                      <Tag color={qualityData.status === "pass" ? "green" : qualityData.status === "warn" ? "gold" : "red"}>{qualityData.status === "pass" ? "通过" : qualityData.status === "warn" ? "有警告" : "未通过"}</Tag>
                    </div>
                    <div style={{ color: "#888", marginBottom: 10 }}>{qualityData.summary}</div>
                    {(qualityData.issues || []).map((issue: any, index: number) => (
                      <div key={`${issue.name}-${index}`} style={{ color: issue.severity === "error" ? "#ef4444" : "#f59e0b", marginTop: 4 }}>
                        {issue.column ? `${issue.column}: ` : ""}{issue.details}
                      </div>
                    ))}
                  </div>
                )}
                {previewData && <>
                  <div style={{ color: "#aaa", fontSize: 16, margin: "20px 0 8px" }}>数据预览（共 {selectedDataset.row_count.toLocaleString()} 行，最多显示前 1,000 行）</div>
                  <div className="ag-theme-alpine-dark" style={{ height: 400, width: "100%", borderRadius: 8, overflow: "hidden", border: "1px solid #333" }}>
                    <AgGridReact columnDefs={gridColumns} rowData={gridRows} rowHeight={32} headerHeight={36} suppressCellFocus />
                  </div>
                </>}
                {!previewData && <Button onClick={() => loadPreview(selectedDataset.id)} style={{ marginTop: 12 }}>加载数据预览</Button>}
                <div style={{ marginTop: 24 }}>
                  <div style={{ color: "#aaa", fontSize: 16, marginBottom: 8 }}>直接 SQL 查询</div>
                  {selectedDataset.source_type === "mysql" && (
                    <div style={{ color: "#f59e0b", marginBottom: 8 }}>MySQL 为会话连接，服务重启后需要重新连接；Agent、报告和自动化暂不支持该外部表。</div>
                  )}
                  <Input.TextArea
                    value={querySql}
                    onChange={(event) => setQuerySql(event.target.value)}
                    autoSize={{ minRows: 2, maxRows: 8 }}
                    style={{ fontFamily: "monospace" }}
                  />
                  <Button type="primary" loading={queryLoading} onClick={() => runDirectQuery(selectedDataset.id)} style={{ marginTop: 8 }}>运行查询</Button>
                  {queryResult && (
                    <Table
                      style={{ marginTop: 12 }}
                      size="small"
                      scroll={{ x: "max-content" }}
                      pagination={{ pageSize: 20 }}
                      rowKey={(_, index) => String(index)}
                      columns={queryResult.columns.map((column, index) => ({ title: column, dataIndex: String(index), key: `${column}-${index}` }))}
                      dataSource={queryResult.rows.map((row) => Object.fromEntries(row.map((value, index) => [String(index), value])))}
                    />
                  )}
                </div>
              </>}
            </div> },
          { key: "reports", label: <span>交付物</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><ReportsPage projectId={projectId!} /></Suspense></div> },
          { key: "workflows", label: <span>自动化</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><WorkflowPage /></Suspense></div> },
          { key: "history", label: <span>审计</span>,
            children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><RunHistoryPage /></Suspense></div> },
          ...(activeTab === "insights" ? [{ key: "insights", label: <span>{advancedTabLabels.insights}</span>, children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><InsightsPage projectId={projectId!} /></Suspense></div> }] : []),
          ...(activeTab === "semantic" ? [{ key: "semantic", label: <span>{advancedTabLabels.semantic}</span>, children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><SemanticLayerPage projectId={projectId!} /></Suspense></div> }] : []),
          ...(activeTab === "notebook" ? [{ key: "notebook", label: <span>{advancedTabLabels.notebook}</span>, children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><NotebookPage projectId={projectId!} /></Suspense></div> }] : []),
          ...(activeTab === "settings" ? [{ key: "settings", label: <span>{advancedTabLabels.settings}</span>, children: <div style={{ padding: "12px 0", width: "100%" }}><Suspense fallback={<TabFallback />}><SettingsPage /></Suspense></div> }] : []),
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
            column_count: data.column_count || 0,
            schema_info: data.schema_info || [],
            created_at: new Date().toISOString(),
            source_type: data.source_type,
          }, ...prev]);
          setSelectedDatasetId(data.id);
        }}
      />

      <Modal
        title="确认上传"
        open={previewModalOpen}
        onCancel={() => { setPreviewModalOpen(false); setPendingFile(null); }}
        onOk={confirmUpload}
        okText="上传"
        width={700}
        styles={{ body: { padding: 16, background: "#1a1a1a" } }}
      >
        {uploadPreview && (
          <div>
            <p style={{ color: "#888", marginBottom: 12 }}>
              {uploadPreview.file_name} ({Math.round(uploadPreview.file_size / 1024)} KB)
              &nbsp;· 编码：{uploadPreview.encoding}
              &nbsp;· {uploadPreview.columns?.length || 0} 个字段，样本包含 {uploadPreview.total_rows_in_sample}+ 行
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
