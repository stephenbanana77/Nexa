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
    load().catch(() => message.error("指标定义加载失败，请刷新页面重试"));
  }, [load]);

  const datasetOptions = datasets.map((d) => ({ label: d.name, value: d.id }));

  const seed = async () => {
    const datasetId = datasets[0]?.id;
    if (!datasetId) {
      message.warning("请先上传数据集");
      return;
    }
    await api.post(`/api/semantic/${projectId}/seed?dataset_id=${datasetId}`);
    message.success("已根据字段结构生成定义建议");
    load();
  };

  const createMetric = async () => {
    const values = await metricForm.validateFields();
    await api.post("/api/semantic/metrics", { ...values, project_id: projectId });
    setMetricOpen(false);
    metricForm.resetFields();
    message.success("指标已创建");
    load();
  };

  const createDimension = async () => {
    const values = await dimensionForm.validateFields();
    await api.post("/api/semantic/dimensions", { ...values, project_id: projectId });
    setDimensionOpen(false);
    dimensionForm.resetFields();
    message.success("维度已创建");
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
    message.success(nextStatus === "approved" ? "定义已审批" : "已撤销审批");
    load();
  };

  return (
    <div style={{ padding: "12px 0" }}>
      <Card
        title="指标定义"
        extra={
          <Space>
            <Button icon={<ThunderboltOutlined />} onClick={seed}>根据字段自动生成</Button>
            <Button icon={<PlusOutlined />} onClick={() => setMetricOpen(true)}>指标</Button>
            <Button icon={<PlusOutlined />} onClick={() => setDimensionOpen(true)}>维度</Button>
          </Space>
        }
      >
        <p style={{ color: "#999", marginTop: 0 }}>
          维护经过治理的业务指标和维度，让 Agent 使用稳定的业务口径，而不是猜测原始字段的含义。
        </p>
        {layer.metrics.length === 0 && layer.dimensions.length === 0 ? (
          <Empty description="还没有指标或维度定义" />
        ) : (
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <Table<SemanticMetric>
              title={() => "业务指标"}
              rowKey="id"
              dataSource={layer.metrics}
              pagination={false}
              columns={[
                { title: "名称", dataIndex: "name" },
                { title: "表达式", dataIndex: "expression", render: (v) => <Tag color="blue">{v}</Tag> },
                { title: "说明", dataIndex: "description" },
                { title: "状态", dataIndex: "status", render: (value: string) => <Tag color={value === "approved" ? "green" : value === "rejected" ? "red" : "gold"}>{value === "approved" ? "已审批" : value === "rejected" ? "已驳回" : "草稿"}</Tag> },
                { title: "操作", render: (_, row) => <Space><Button size="small" type={row.status === "approved" ? "default" : "primary"} icon={<CheckOutlined />} onClick={() => updateStatus("metrics", row.id, row.status)}>{row.status === "approved" ? "撤销审批" : "审批"}</Button><Button danger size="small" icon={<DeleteOutlined />} onClick={() => deleteMetric(row.id)} /></Space> },
              ]}
            />
            <Table<SemanticDimension>
              title={() => "业务维度"}
              rowKey="id"
              dataSource={layer.dimensions}
              pagination={false}
              columns={[
                { title: "名称", dataIndex: "name" },
                { title: "来源字段", dataIndex: "column", render: (v) => <Tag>{v}</Tag> },
                { title: "说明", dataIndex: "description" },
                { title: "状态", dataIndex: "status", render: (value: string) => <Tag color={value === "approved" ? "green" : value === "rejected" ? "red" : "gold"}>{value === "approved" ? "已审批" : value === "rejected" ? "已驳回" : "草稿"}</Tag> },
                { title: "操作", render: (_, row) => <Space><Button size="small" type={row.status === "approved" ? "default" : "primary"} icon={<CheckOutlined />} onClick={() => updateStatus("dimensions", row.id, row.status)}>{row.status === "approved" ? "撤销审批" : "审批"}</Button><Button danger size="small" icon={<DeleteOutlined />} onClick={() => deleteDimension(row.id)} /></Space> },
              ]}
            />
          </Space>
        )}
      </Card>

      <Modal title="新建指标" open={metricOpen} onOk={createMetric} onCancel={() => setMetricOpen(false)}>
        <Form form={metricForm} layout="vertical">
          <Form.Item name="dataset_id" label="数据集"><Select allowClear options={datasetOptions} /></Form.Item>
          <Form.Item name="name" label="指标名称" rules={[{ required: true }]}><Input placeholder="毛利率" /></Form.Item>
          <Form.Item name="expression" label="SQL 表达式" rules={[{ required: true }]}><Input placeholder='SUM("Profit") / NULLIF(SUM("Sales"), 0)' /></Form.Item>
          <Form.Item name="description" label="口径说明"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="新建维度" open={dimensionOpen} onOk={createDimension} onCancel={() => setDimensionOpen(false)}>
        <Form form={dimensionForm} layout="vertical">
          <Form.Item name="dataset_id" label="数据集"><Select allowClear options={datasetOptions} /></Form.Item>
          <Form.Item name="name" label="维度名称" rules={[{ required: true }]}><Input placeholder="区域" /></Form.Item>
          <Form.Item name="column" label="来源字段" rules={[{ required: true }]}><Input placeholder="Region" /></Form.Item>
          <Form.Item name="description" label="口径说明"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
