import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Collapse, Empty, List, Select, Space, Spin, Statistic, Table, Tag, Typography, message } from "antd";
import { CheckCircleOutlined, FileSearchOutlined, FileTextOutlined, QuestionCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import api from "../api/client";
import type { AnalysisReport, Dataset } from "../types";
import "./ReportsPage.css";

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

const REPORT_TYPE_LABELS: Record<string, string> = {
  dataset: "数据集",
  semantic_layer: "语义层",
  metric_contracts: "指标契约",
  finding: "发现",
  evidence: "证据",
  hypothesis: "假设",
  decision_brief: "决策摘要",
  risk: "风险",
  opportunity: "机会",
  concentration: "集中度",
  underperformer: "低表现分组",
  outlier: "异常值",
};

function reportTypeLabel(value?: string) {
  if (!value) return "未知";
  return REPORT_TYPE_LABELS[value] || value;
}

function humanizeReportError(detail: unknown, fallback: string) {
  const messageText = typeof detail === "string"
    ? detail
    : detail && typeof detail === "object" && "message" in detail
      ? String((detail as { message?: unknown }).message || "")
      : "";
  const normalized = messageText.toLowerCase();
  if (normalized.includes("data quality") || normalized.includes("quality warnings")) {
    return "发布前仍有数据质量阻断项。请先到「数据」页运行质量检查并处理问题。";
  }
  if (normalized.includes("approved metric") || normalized.includes("metric contract")) {
    return "请先在「高级工具 > 指标定义」完成指标审批，然后重新生成报告。";
  }
  if (normalized.includes("mysql")) return "MySQL 数据需要先导入快照，才能生成报告。";
  return (messageText || fallback).replace(/\s*\(request_id:[^)]+\)/gi, "").slice(0, 220);
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
  const [publishing, setPublishing] = useState(false);

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
      setSelectedReport((prev) => (
        prev ? list.find((report: AnalysisReport) => report.id === prev.id) || list[0] || null : list[0] || null
      ));
      setDatasets(ds);
      setSelectedDatasetId((prev) => prev || ds[0]?.id);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load().catch(() => message.error("报告加载失败，请刷新页面重试"));
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
      message.success(isInvestigation ? "自动调查已完成" : "洞察报告已生成");
    } catch (err: any) {
      message.error(humanizeReportError(
        err.response?.data?.detail,
        isInvestigation ? "自动调查失败，请稍后重试" : "报告生成失败，请稍后重试",
      ));
    } finally {
      setInvestigating(false);
      setGenerating(false);
    }
  };

  const askFollowUp = (question: string) => {
    const params = new URLSearchParams({ tab: "chat", question });
    navigate(`/project/${projectId}?${params.toString()}`);
  };

  const publishReport = async () => {
    if (!selectedReport) return;
    setPublishing(true);
    try {
      const { data } = await api.post(`/api/reports/${selectedReport.id}/publish`);
      setReports((prev) => prev.map((report) => report.id === data.id ? data : report));
      setSelectedReport(data);
      message.success("报告已发布");
    } catch (err: any) {
      message.error(humanizeReportError(err.response?.data?.detail, "报告发布失败，请稍后重试"));
    } finally {
      setPublishing(false);
    }
  };

  const sections = selectedReport?.content.sections;
  const investigationCards = selectedReport?.content.investigation_cards || [];
  const decisionBrief = selectedReport?.content.decision_brief;
  const analysisGraph = selectedReport?.content.analysis_graph;
  const metricContracts = selectedReport?.content.metric_contracts;
  const graphNodesById = new Map((analysisGraph?.nodes || []).map((node) => [node.id, node]));

  return (
    <div className="reports-layout">
      <Card className="reports-sidebar" title="数据调查" extra={<Button icon={<ReloadOutlined />} onClick={load} title="刷新" />}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Select
            placeholder="选择数据集"
            value={selectedDatasetId}
            onChange={setSelectedDatasetId}
            options={datasets.map((d) => ({ label: d.name, value: d.id }))}
            style={{ width: "100%" }}
          />
          <Button type="primary" icon={<FileSearchOutlined />} loading={investigating} onClick={() => createReport("investigation")} block>
            开始自动调查
          </Button>
          <Button icon={<FileTextOutlined />} loading={generating} onClick={() => createReport("report")} block>
            生成标准报告
          </Button>
        </Space>
        {loading ? <Spin style={{ marginTop: 24 }} /> : (
          <List
            style={{ marginTop: 20 }}
            dataSource={reports}
            locale={{ emptyText: <Empty description="还没有调查报告" /> }}
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

      <Card className="reports-detail">
        {!selectedReport ? (
          <Empty description="开始自动调查后，即可查看由 SQL 证据支持的发现" />
        ) : (
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <div>
              <Space align="center" wrap>
                <Typography.Title level={3} style={{ marginTop: 0, marginBottom: 0 }}>{selectedReport.title}</Typography.Title>
                <Tag color={selectedReport.status === "published" ? "green" : "gold"}>{selectedReport.status === "published" ? "已发布" : "草稿"}</Tag>
                {selectedReport.status !== "published" && <Button type="primary" icon={<CheckCircleOutlined />} loading={publishing} onClick={publishReport}>发布报告</Button>}
              </Space>
              <Space wrap>
                <Tag color="blue">{selectedReport.content.blocks.length} 个证据块</Tag>
                <Tag color="orange">{investigationCards.length} 张调查卡片</Tag>
                <Tag color="magenta">{decisionBrief ? "包含决策摘要" : "无决策摘要"}</Tag>
                <Tag color="lime">{analysisGraph ? `${analysisGraph.nodes.length} 个分析节点` : "无分析图谱"}</Tag>
                <Tag color={metricContracts?.status === "pass" ? "green" : "gold"}>
                  {metricContracts ? `指标契约${metricContracts.status === "pass" ? "通过" : "有警告"}` : "无指标契约"}
                </Tag>
                <Tag color="purple">{sections?.diagnostic_insights?.length || 0} 条诊断</Tag>
                <Tag color="cyan">{sections?.recommended_follow_up_questions?.length || 0} 个追问</Tag>
              </Space>
            </div>

            {decisionBrief && (
              <Card
                type="inner"
                title="决策摘要"
                extra={<Tag color={decisionBrief.confidence === "high" ? "green" : "gold"}>置信度：{decisionBrief.confidence === "high" ? "高" : decisionBrief.confidence === "medium" ? "中" : "低"}</Tag>}
              >
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Typography.Text type="secondary">面向对象：{decisionBrief.audience}</Typography.Text>
                  <Typography.Paragraph><strong>现状：</strong> {decisionBrief.situation}</Typography.Paragraph>
                  <Typography.Paragraph><strong>诊断：</strong> {decisionBrief.diagnosis}</Typography.Paragraph>
                  <Typography.Paragraph><strong>建议：</strong> {decisionBrief.recommendation}</Typography.Paragraph>
                  <Typography.Paragraph><strong>风险：</strong> {decisionBrief.risk}</Typography.Paragraph>
                  <Space wrap>
                    {decisionBrief.evidence.map((item) => <Tag key={item}>证据：{item}</Tag>)}
                  </Space>
                  <div>
                    <Typography.Text strong>建议行动</Typography.Text>
                    {decisionBrief.recommended_actions.map((item) => (
                      <p key={item} style={{ margin: "6px 0" }}>• {item}</p>
                    ))}
                  </div>
                  <Space wrap>
                    <Typography.Text strong>下一步关注指标：</Typography.Text>
                    {decisionBrief.next_metric_to_monitor.map((item) => <Tag color="blue" key={item}>{item}</Tag>)}
                  </Space>
                </Space>
              </Card>
            )}

            {metricContracts && (
              <Card
                type="inner"
                title="指标契约检查"
                extra={<Tag color={metricContracts.release_gate.can_answer ? "green" : "red"}>{metricContracts.release_gate.can_answer ? "可回答" : "已阻断"}</Tag>}
              >
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Typography.Paragraph>{metricContracts.summary}</Typography.Paragraph>
                  <Typography.Text type={metricContracts.release_gate.requires_review ? "warning" : "success"}>
                    {metricContracts.release_gate.reason}
                  </Typography.Text>
                  <Table
                    size="small"
                    pagination={false}
                    rowKey={(record) => `${record.type}-${record.name}`}
                    columns={[
                      { title: "类型", dataIndex: "type", key: "type", render: (value: string) => <Tag>{value === "metric" ? "指标" : value === "dimension" ? "维度" : value}</Tag> },
                      { title: "名称", dataIndex: "name", key: "name" },
                      { title: "状态", dataIndex: "status", key: "status", render: (value: string) => <Tag color={value === "pass" ? "green" : "gold"}>{value === "pass" ? "通过" : "有警告"}</Tag> },
                      { title: "引用字段", dataIndex: "referenced_columns", key: "referenced_columns", render: (cols: string[]) => cols.join(", ") || "无" },
                      { title: "问题", dataIndex: "issues", key: "issues", render: (issues: string[]) => issues.length ? issues.join("；") : "无问题" },
                    ]}
                    dataSource={metricContracts.contracts}
                  />
                </Space>
              </Card>
            )}

            {analysisGraph && (
              <Card
                type="inner"
                title="分析图谱"
                extra={<Typography.Text type="secondary">数据集 → 发现 → 假设 → 证据 → 决策摘要</Typography.Text>}
              >
                <Space direction="vertical" size={10} style={{ width: "100%" }}>
                  {analysisGraph.edges.slice(0, 14).map((edge, idx) => {
                    const source = graphNodesById.get(edge.source);
                    const target = graphNodesById.get(edge.target);
                    return (
                      <div
                        className="report-graph-edge"
                        key={`${edge.source}-${edge.target}-${idx}`}
                        style={{
                          padding: 10,
                          border: "1px solid #333",
                          borderRadius: 8,
                          background: "#111",
                        }}
                      >
                        <div>
                          <Tag color="blue">{reportTypeLabel(source?.type || edge.source)}</Tag>
                          <Typography.Text>{source?.type === "finding" ? reportTypeLabel(source.label) : source?.label || edge.source}</Typography.Text>
                        </div>
                        <Typography.Text type="secondary" style={{ textAlign: "center" }}>→ {edge.label} →</Typography.Text>
                        <div>
                          <Tag color={target?.type === "decision_brief" ? "magenta" : target?.type === "hypothesis" ? "geekblue" : "gold"}>
                            {reportTypeLabel(target?.type || edge.target)}
                          </Tag>
                          <Typography.Text>{target?.type === "finding" ? reportTypeLabel(target.label) : target?.label || edge.target}</Typography.Text>
                        </div>
                      </div>
                    );
                  })}
                </Space>
              </Card>
            )}

            {investigationCards.length > 0 && (
              <Card type="inner" title="自动调查" extra={<Typography.Text type="secondary">发现 → 影响 → 证据 → 下一步问题</Typography.Text>}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
                  {investigationCards.map((card, idx) => (
                    <Card
                      key={`${card.type}-${idx}`}
                      size="small"
                      title={<Space wrap><Tag color={card.severity === "high" ? "red" : card.severity === "medium" ? "gold" : "blue"}>{card.severity === "high" ? "高" : card.severity === "medium" ? "中" : "低"}</Tag><span>{reportTypeLabel(card.type)}</span></Space>}
                      extra={<Tag color={card.confidence === "high" ? "green" : "default"}>置信度：{card.confidence === "high" ? "高" : card.confidence === "medium" ? "中" : "低"}</Tag>}
                    >
                      <Typography.Paragraph style={{ marginBottom: 8 }}>{card.finding}</Typography.Paragraph>
                      <Typography.Text type="secondary">{card.impact}</Typography.Text>
                      <div style={{ marginTop: 12 }}><Tag>证据：{card.evidence_title}</Tag></div>
                      {card.sql && (
                        <Collapse
                          size="small"
                          style={{ marginTop: 12 }}
                          items={[{
                            key: "evidence",
                            label: "查看 SQL 证据",
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
                            label: `假设验证（${card.hypotheses!.length}）`,
                            children: (
                              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                                {card.hypotheses!.map((hypothesis, hypIdx) => (
                                  <Card key={`${card.type}-hypothesis-${hypIdx}`} size="small">
                                    <Space wrap style={{ marginBottom: 8 }}>
                                      <Tag color="geekblue">H{hypIdx + 1}</Tag>
                                      <Tag>{hypothesis.status === "supported" ? "已支持" : hypothesis.status === "rejected" ? "已否定" : hypothesis.status === "needs_validation" ? "待验证" : "已提出"}</Tag>
                                      <Tag>证据：{hypothesis.evidence_title}</Tag>
                                    </Space>
                                    <Typography.Paragraph strong style={{ marginBottom: 6 }}>
                                      {hypothesis.hypothesis}
                                    </Typography.Paragraph>
                                    <Typography.Paragraph type="secondary" style={{ marginBottom: 6 }}>
                                      当前判断：{hypothesis.current_assessment}
                                    </Typography.Paragraph>
                                    <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
                                      验证方法：{hypothesis.validation}
                                    </Typography.Paragraph>
                                    <Button size="small" onClick={() => askFollowUp(hypothesis.next_question)}>
                                      验证这个假设
                                    </Button>
                                  </Card>
                                ))}
                              </Space>
                            ),
                          }]}
                        />
                      )}
                      <Button icon={<QuestionCircleOutlined />} style={{ marginTop: 12 }} onClick={() => askFollowUp(card.next_question)} block>
                        继续追问
                      </Button>
                    </Card>
                  ))}
                </div>
              </Card>
            )}

            {!decisionBrief && (
              <Card type="inner" title="执行摘要">
                {(sections?.executive_summary || selectedReport.content.highlights || []).map((item) => (
                  <p key={item} style={{ margin: "6px 0" }}>• {item}</p>
                ))}
              </Card>
            )}

            {(sections?.key_metrics?.length || 0) > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                {sections!.key_metrics.map((metric) => (
                  <Card type="inner" key={metric.label}>
                    <Statistic title={metric.label} value={metric.value} />
                    <Tag style={{ marginTop: 8 }}>证据：{metric.evidence_title}</Tag>
                  </Card>
                ))}
              </div>
            )}

            {(sections?.segment_breakdown?.length || 0) > 0 && (
              <Card type="inner" title="细分分析">
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
              <Card type="inner" title="风险">
                {(sections?.risks || []).map((item) => <p key={item}>• {item}</p>)}
              </Card>
              <Card type="inner" title="机会">
                {(sections?.opportunities || []).map((item) => <p key={item}>• {item}</p>)}
              </Card>
            </div>

            <Card type="inner" title="建议追问">
              {(sections?.recommended_follow_up_questions || []).map((item) => (
                <p key={item}>• {item} <Button size="small" type="link" onClick={() => askFollowUp(item)}>追问</Button></p>
              ))}
            </Card>

            <Collapse
              items={[{
                key: "audit-detail",
                label: `审计细节（报告原文 + ${selectedReport.content.blocks.length} 个证据块）`,
                children: (
                  <Space direction="vertical" size={12} style={{ width: "100%" }}>
                    <div className="report-markdown">
                      <ReactMarkdown>{selectedReport.content.markdown}</ReactMarkdown>
                    </div>
                    {selectedReport.content.blocks.map((block) => (
                      <Card type="inner" key={block.title} title={block.title}>
                        <pre className="report-sql">{block.sql}</pre>
                        <p style={{ color: block.error ? "#ef4444" : "#aaa" }}>{block.error || block.finding}</p>
                        {block.rows?.length > 0 && (
                          <Table
                            size="small"
                            pagination={false}
                            scroll={{ x: true }}
                            columns={block.columns.map((col) => ({ title: col, dataIndex: col, key: col }))}
                            dataSource={rowsToRecords(block.columns, block.rows)}
                          />
                        )}
                      </Card>
                    ))}
                  </Space>
                ),
              }]}
            />
          </Space>
        )}
      </Card>
    </div>
  );
}
