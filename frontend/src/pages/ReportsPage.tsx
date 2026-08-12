import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Collapse, Empty, List, Select, Space, Spin, Statistic, Table, Tag, Typography, message } from "antd";
import { FileSearchOutlined, FileTextOutlined, QuestionCircleOutlined, ReloadOutlined } from "@ant-design/icons";
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
  const navigate = useNavigate();
  const [reports, setReports] = useState<AnalysisReport[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | undefined>();
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [investigating, setInvestigating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [{ data: reportData }, { data: datasetResp }] = await Promise.all([
        api.get(`/api/reports/project/${projectId}`),
        api.get(`/api/datasets?project_id=${projectId}`),
      ]);
      const list = Array.isArray(reportData) ? reportData : [];
      const ds = datasetResp.items || datasetResp || [];
      setReports(list);
      setSelectedReport((prev) => prev || list[0] || null);
      setDatasets(ds);
      setSelectedDatasetId((prev) => prev || ds[0]?.id);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load().catch(() => message.error("Failed to load reports"));
  }, [load]);

  const createReport = async (mode: "report" | "investigation") => {
    const isInvestigation = mode === "investigation";
    if (isInvestigation) setInvestigating(true);
    else setGenerating(true);
    try {
      const { data } = await api.post(isInvestigation ? "/api/reports/investigate" : "/api/reports", {
        project_id: projectId,
        dataset_id: selectedDatasetId,
      });
      setReports((prev) => [data, ...prev]);
      setSelectedReport(data);
      message.success(isInvestigation ? "Auto Investigation completed" : "Insight Report generated");
    } catch (err: any) {
      message.error(err.response?.data?.detail || (isInvestigation ? "Investigation failed" : "Report generation failed"));
    } finally {
      setInvestigating(false);
      setGenerating(false);
    }
  };

  const askFollowUp = (question: string) => {
    const params = new URLSearchParams({ tab: "chat", question });
    navigate(`/project/${projectId}?${params.toString()}`);
  };

  const sections = selectedReport?.content.sections;
  const investigationCards = selectedReport?.content.investigation_cards || [];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px minmax(0, 1fr)", gap: 16, padding: "12px 0" }}>
      <Card title="Data Detective" extra={<Button icon={<ReloadOutlined />} onClick={load} />} style={{ minHeight: 520 }}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Select
            placeholder="Dataset"
            value={selectedDatasetId}
            onChange={setSelectedDatasetId}
            options={datasets.map((d) => ({ label: d.name, value: d.id }))}
            style={{ width: "100%" }}
          />
          <Button type="primary" icon={<FileSearchOutlined />} loading={investigating} onClick={() => createReport("investigation")} block>
            Start Auto Investigation
          </Button>
          <Button icon={<FileTextOutlined />} loading={generating} onClick={() => createReport("report")} block>
            Generate classic report
          </Button>
        </Space>
        {loading ? <Spin style={{ marginTop: 24 }} /> : (
          <List
            style={{ marginTop: 20 }}
            dataSource={reports}
            locale={{ emptyText: <Empty description="No investigations yet" /> }}
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
          <Empty description="Start Auto Investigation to see SQL-backed findings" />
        ) : (
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <div>
              <Typography.Title level={3} style={{ marginTop: 0 }}>{selectedReport.title}</Typography.Title>
              <Space wrap>
                <Tag color="blue">{selectedReport.content.blocks.length} evidence blocks</Tag>
                <Tag color="orange">{investigationCards.length} investigation cards</Tag>
                <Tag color="purple">{sections?.diagnostic_insights?.length || 0} diagnostics</Tag>
                <Tag color="cyan">{sections?.recommended_follow_up_questions?.length || 0} follow-ups</Tag>
              </Space>
            </div>

            {investigationCards.length > 0 && (
              <Card type="inner" title="Auto Investigation" extra={<Typography.Text type="secondary">Finding → Impact → Evidence → Next question</Typography.Text>}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
                  {investigationCards.map((card, idx) => (
                    <Card
                      key={`${card.type}-${idx}`}
                      size="small"
                      title={<Space wrap><Tag color={card.severity === "high" ? "red" : card.severity === "medium" ? "gold" : "blue"}>{card.severity}</Tag><span>{card.type}</span></Space>}
                      extra={<Tag color={card.confidence === "high" ? "green" : "default"}>{card.confidence} confidence</Tag>}
                    >
                      <Typography.Paragraph style={{ marginBottom: 8 }}>{card.finding}</Typography.Paragraph>
                      <Typography.Text type="secondary">{card.impact}</Typography.Text>
                      <div style={{ marginTop: 12 }}><Tag>evidence: {card.evidence_title}</Tag></div>
                      {card.sql && (
                        <Collapse
                          size="small"
                          style={{ marginTop: 12 }}
                          items={[{
                            key: "evidence",
                            label: "Show SQL evidence",
                            children: (
                              <>
                                <pre style={{ whiteSpace: "pre-wrap", background: "#111", padding: 12, borderRadius: 8 }}>{card.sql}</pre>
                                {card.evidence_preview?.length > 0 && (
                                  <Table
                                    size="small"
                                    pagination={false}
                                    columns={["value_1", "value_2", "value_3"].map((col) => ({ title: col, dataIndex: col, key: col }))}
                                    dataSource={card.evidence_preview.map((row, rowIdx) => ({
                                      key: rowIdx,
                                      value_1: row[0],
                                      value_2: row[1],
                                      value_3: row[2],
                                    }))}
                                  />
                                )}
                              </>
                            ),
                          }]}
                        />
                      )}
                      {(card.hypotheses?.length || 0) > 0 && (
                        <Collapse
                          size="small"
                          style={{ marginTop: 12 }}
                          items={[{
                            key: "hypotheses",
                            label: `Hypothesis Engine (${card.hypotheses!.length})`,
                            children: (
                              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                                {card.hypotheses!.map((hypothesis, hypIdx) => (
                                  <Card key={`${card.type}-hypothesis-${hypIdx}`} size="small">
                                    <Space wrap style={{ marginBottom: 8 }}>
                                      <Tag color="geekblue">H{hypIdx + 1}</Tag>
                                      <Tag>{hypothesis.status}</Tag>
                                      <Tag>evidence: {hypothesis.evidence_title}</Tag>
                                    </Space>
                                    <Typography.Paragraph strong style={{ marginBottom: 6 }}>
                                      {hypothesis.hypothesis}
                                    </Typography.Paragraph>
                                    <Typography.Paragraph type="secondary" style={{ marginBottom: 6 }}>
                                      Assessment: {hypothesis.current_assessment}
                                    </Typography.Paragraph>
                                    <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
                                      Validation: {hypothesis.validation}
                                    </Typography.Paragraph>
                                    <Button size="small" onClick={() => askFollowUp(hypothesis.next_question)}>
                                      Validate this hypothesis
                                    </Button>
                                  </Card>
                                ))}
                              </Space>
                            ),
                          }]}
                        />
                      )}
                      <Button icon={<QuestionCircleOutlined />} style={{ marginTop: 12 }} onClick={() => askFollowUp(card.next_question)} block>
                        Ask follow-up
                      </Button>
                    </Card>
                  ))}
                </div>
              </Card>
            )}

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
              {(sections?.recommended_follow_up_questions || []).map((item) => (
                <p key={item}>• {item} <Button size="small" type="link" onClick={() => askFollowUp(item)}>Ask</Button></p>
              ))}
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
