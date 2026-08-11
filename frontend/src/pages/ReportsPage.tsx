import { useCallback, useEffect, useState } from "react";
import { Button, Card, Empty, List, Select, Space, Spin, Statistic, Table, Tag, Typography, message } from "antd";
import { FileTextOutlined, ReloadOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import api from "../api/client";
import type { AnalysisReport, Dataset } from "../types";

interface Props {
  projectId: string;
}

function rowsToRecords(columns: string[], rows: unknown[][]) {
  return rows.map((row, idx) => {
    const record: Record<string, unknown> = { key: idx };
    columns.forEach((col, colIdx) => { record[col] = row[colIdx]; });
    return record;
  });
}

export default function ReportsPage({ projectId }: Props) {
  const [reports, setReports] = useState<AnalysisReport[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | undefined>();
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [{ data: reportData }, { data: datasetResp }] = await Promise.all([
        api.get(`/api/reports/project/${projectId}`),
        api.get(`/api/datasets?project_id=${projectId}`),
      ]);
      const list = Array.isArray(reportData) ? reportData : [];
      setReports(list);
      setSelectedReport((prev) => prev || list[0] || null);
      const ds = datasetResp.items || datasetResp || [];
      setDatasets(ds);
      setSelectedDatasetId((prev) => prev || ds[0]?.id);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load().catch(() => message.error("Failed to load reports"));
  }, [load]);

  const generate = async () => {
    setGenerating(true);
    try {
      const { data } = await api.post("/api/reports", {
        project_id: projectId,
        dataset_id: selectedDatasetId,
      });
      setReports((prev) => [data, ...prev]);
      setSelectedReport(data);
      message.success("Insight Report generated");
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Report generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const sections = selectedReport?.content.sections;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px minmax(0, 1fr)", gap: 16, padding: "12px 0" }}>
      <Card
        title="Insight Reports"
        extra={<Button icon={<ReloadOutlined />} onClick={load} />}
        style={{ minHeight: 520 }}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Select
            placeholder="Dataset"
            value={selectedDatasetId}
            onChange={setSelectedDatasetId}
            options={datasets.map((d) => ({ label: d.name, value: d.id }))}
            style={{ width: "100%" }}
          />
          <Button type="primary" icon={<FileTextOutlined />} loading={generating} onClick={generate} block>
            Generate report
          </Button>
        </Space>
        {loading ? <Spin style={{ marginTop: 24 }} /> : (
          <List
            style={{ marginTop: 20 }}
            dataSource={reports}
            locale={{ emptyText: <Empty description="No reports yet" /> }}
            renderItem={(item) => (
              <List.Item
                onClick={() => setSelectedReport(item)}
                style={{
                  cursor: "pointer",
                  border: selectedReport?.id === item.id ? "1px solid #2563EB" : "1px solid #333",
                  borderRadius: 8,
                  padding: 12,
                  marginBottom: 8,
                }}
              >
                <List.Item.Meta
                  title={<span style={{ color: "#ddd" }}>{item.title}</span>}
                  description={<span>{new Date(item.created_at).toLocaleString()}</span>}
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      <Card>
        {!selectedReport ? (
          <Empty description="Generate a report to see SQL-backed findings" />
        ) : (
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <div>
              <Typography.Title level={3} style={{ marginTop: 0 }}>{selectedReport.title}</Typography.Title>
              <Space wrap>
                <Tag color="blue">{selectedReport.content.blocks.length} evidence blocks</Tag>
                <Tag color="green">{selectedReport.content.highlights.length} highlights</Tag>
                <Tag color="purple">{sections?.recommended_follow_up_questions?.length || 0} follow-ups</Tag>
              </Space>
            </div>

            <Card type="inner" title="Executive Summary">
              {(sections?.executive_summary || selectedReport.content.highlights || []).map((item) => (
                <p key={item} style={{ margin: "6px 0" }}>• {item}</p>
              ))}
            </Card>

            {(sections?.key_metrics?.length || 0) > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                {sections!.key_metrics.map((metric) => (
                  <Card type="inner" key={metric.label}>
                    <Statistic title={metric.label} value={metric.value} />
                    <Tag style={{ marginTop: 8 }}>evidence: {metric.evidence_title}</Tag>
                  </Card>
                ))}
              </div>
            )}

            {(sections?.segment_breakdown?.length || 0) > 0 && (
              <Card type="inner" title="Segment Breakdown">
                {sections!.segment_breakdown.map((segment) => (
                  <div key={segment.title} style={{ marginBottom: 18 }}>
                    <Typography.Text strong>{segment.title}</Typography.Text>
                    <Table
                      style={{ marginTop: 8 }}
                      size="small"
                      pagination={false}
                      columns={segment.columns.map((col) => ({ title: col, dataIndex: col, key: col }))}
                      dataSource={rowsToRecords(segment.columns, segment.top_rows)}
                    />
                  </div>
                ))}
              </Card>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
              <Card type="inner" title="Risks">
                {(sections?.risks || []).map((item) => <p key={item}>• {item}</p>)}
              </Card>
              <Card type="inner" title="Opportunities">
                {(sections?.opportunities || []).map((item) => <p key={item}>• {item}</p>)}
              </Card>
            </div>

            <Card type="inner" title="Recommended Follow-up Questions">
              {(sections?.recommended_follow_up_questions || []).map((item) => <p key={item}>• {item}</p>)}
            </Card>

            <Card type="inner" title="Report Markdown">
              <div style={{ fontSize: 16, lineHeight: 1.7 }}>
                <ReactMarkdown>{selectedReport.content.markdown}</ReactMarkdown>
              </div>
            </Card>

            {selectedReport.content.blocks.map((block) => (
              <Card type="inner" key={block.title} title={block.title}>
                <pre style={{ whiteSpace: "pre-wrap", background: "#111", padding: 12, borderRadius: 8 }}>{block.sql}</pre>
                <p style={{ color: block.error ? "#ef4444" : "#aaa" }}>{block.error || block.finding}</p>
                {block.rows?.length > 0 && (
                  <Table
                    size="small"
                    pagination={false}
                    columns={block.columns.map((col) => ({ title: col, dataIndex: col, key: col }))}
                    dataSource={rowsToRecords(block.columns, block.rows)}
                  />
                )}
              </Card>
            ))}
          </Space>
        )}
      </Card>
    </div>
  );
}
