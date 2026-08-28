import { useCallback, useEffect, useState } from "react";
import { Button, Card, Empty, Form, Input, Modal, Select, Space, Table, Tag, message } from "antd";
import { CheckOutlined, DeleteOutlined, PlusOutlined, ThunderboltOutlined } from "@ant-design/icons";
import api from "../api/client";
import type { Dataset, SemanticDimension, SemanticLayer, SemanticMetric } from "../types";

interface Props {
  projectId: string;
}

export default function SemanticLayerPage({ projectId }: Props) {
  const [layer, setLayer] = useState<SemanticLayer>({ metrics: [], dimensions: [] });
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [metricOpen, setMetricOpen] = useState(false);
  const [dimensionOpen, setDimensionOpen] = useState(false);
  const [metricForm] = Form.useForm();
  const [dimensionForm] = Form.useForm();

  const load = useCallback(async () => {
    const [{ data: semantic }, { data: datasetResp }] = await Promise.all([
      api.get(`/api/semantic/${projectId}`),
      api.get(`/api/datasets?project_id=${projectId}`),
    ]);
    setLayer(semantic);
    setDatasets(datasetResp.items || datasetResp || []);
  }, [projectId]);

  useEffect(() => {
    load().catch(() => message.error("Failed to load semantic layer"));
  }, [load]);

  const datasetOptions = datasets.map((d) => ({ label: d.name, value: d.id }));

  const seed = async () => {
    const datasetId = datasets[0]?.id;
    if (!datasetId) {
      message.warning("Upload a dataset first");
      return;
    }
    await api.post(`/api/semantic/${projectId}/seed?dataset_id=${datasetId}`);
    message.success("Semantic suggestions generated");
    load();
  };

  const createMetric = async () => {
    const values = await metricForm.validateFields();
    await api.post("/api/semantic/metrics", { ...values, project_id: projectId });
    setMetricOpen(false);
    metricForm.resetFields();
    message.success("Metric created");
    load();
  };

  const createDimension = async () => {
    const values = await dimensionForm.validateFields();
    await api.post("/api/semantic/dimensions", { ...values, project_id: projectId });
    setDimensionOpen(false);
    dimensionForm.resetFields();
    message.success("Dimension created");
    load();
  };

  const deleteMetric = async (id: string) => {
    await api.delete(`/api/semantic/metrics/${id}`);
    load();
  };

  const deleteDimension = async (id: string) => {
    await api.delete(`/api/semantic/dimensions/${id}`);
    load();
  };

  const updateStatus = async (type: "metrics" | "dimensions", id: string, current?: string) => {
    const nextStatus = current === "approved" ? "draft" : "approved";
    await api.patch(`/api/semantic/${type}/${id}/status`, { status: nextStatus });
    message.success(nextStatus === "approved" ? "Definition approved" : "Approval revoked");
    load();
  };

  return (
    <div style={{ padding: "12px 0" }}>
      <Card
        title="Semantic Layer"
        extra={
          <Space>
            <Button icon={<ThunderboltOutlined />} onClick={seed}>Auto seed from schema</Button>
            <Button icon={<PlusOutlined />} onClick={() => setMetricOpen(true)}>Metric</Button>
            <Button icon={<PlusOutlined />} onClick={() => setDimensionOpen(true)}>Dimension</Button>
          </Space>
        }
      >
        <p style={{ color: "#999", marginTop: 0 }}>
          Define governed business metrics and dimensions so the AI agent reasons with stable business terms instead of guessing raw columns.
        </p>
        {layer.metrics.length === 0 && layer.dimensions.length === 0 ? (
          <Empty description="No semantic definitions yet" />
        ) : (
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <Table<SemanticMetric>
              title={() => "Business Metrics"}
              rowKey="id"
              dataSource={layer.metrics}
              pagination={false}
              columns={[
                { title: "Name", dataIndex: "name" },
                { title: "Expression", dataIndex: "expression", render: (v) => <Tag color="blue">{v}</Tag> },
                { title: "Description", dataIndex: "description" },
                { title: "Status", dataIndex: "status", render: (value: string) => <Tag color={value === "approved" ? "green" : value === "rejected" ? "red" : "gold"}>{value || "draft"}</Tag> },
                { title: "Actions", render: (_, row) => <Space><Button size="small" type={row.status === "approved" ? "default" : "primary"} icon={<CheckOutlined />} onClick={() => updateStatus("metrics", row.id, row.status)}>{row.status === "approved" ? "Revoke" : "Approve"}</Button><Button danger size="small" icon={<DeleteOutlined />} onClick={() => deleteMetric(row.id)} /></Space> },
              ]}
            />
            <Table<SemanticDimension>
              title={() => "Business Dimensions"}
              rowKey="id"
              dataSource={layer.dimensions}
              pagination={false}
              columns={[
                { title: "Name", dataIndex: "name" },
                { title: "Column", dataIndex: "column", render: (v) => <Tag>{v}</Tag> },
                { title: "Description", dataIndex: "description" },
                { title: "Status", dataIndex: "status", render: (value: string) => <Tag color={value === "approved" ? "green" : value === "rejected" ? "red" : "gold"}>{value || "draft"}</Tag> },
                { title: "Actions", render: (_, row) => <Space><Button size="small" type={row.status === "approved" ? "default" : "primary"} icon={<CheckOutlined />} onClick={() => updateStatus("dimensions", row.id, row.status)}>{row.status === "approved" ? "Revoke" : "Approve"}</Button><Button danger size="small" icon={<DeleteOutlined />} onClick={() => deleteDimension(row.id)} /></Space> },
              ]}
            />
          </Space>
        )}
      </Card>

      <Modal title="New metric" open={metricOpen} onOk={createMetric} onCancel={() => setMetricOpen(false)}>
        <Form form={metricForm} layout="vertical">
          <Form.Item name="dataset_id" label="Dataset"><Select allowClear options={datasetOptions} /></Form.Item>
          <Form.Item name="name" label="Metric name" rules={[{ required: true }]}><Input placeholder="Gross Margin" /></Form.Item>
          <Form.Item name="expression" label="SQL expression" rules={[{ required: true }]}><Input placeholder='SUM("Profit") / NULLIF(SUM("Sales"), 0)' /></Form.Item>
          <Form.Item name="description" label="Definition"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="New dimension" open={dimensionOpen} onOk={createDimension} onCancel={() => setDimensionOpen(false)}>
        <Form form={dimensionForm} layout="vertical">
          <Form.Item name="dataset_id" label="Dataset"><Select allowClear options={datasetOptions} /></Form.Item>
          <Form.Item name="name" label="Dimension name" rules={[{ required: true }]}><Input placeholder="Region" /></Form.Item>
          <Form.Item name="column" label="Source column" rules={[{ required: true }]}><Input placeholder="Region" /></Form.Item>
          <Form.Item name="description" label="Definition"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
