import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Table, Tag, Spin, Empty, Typography } from "antd";
import { api } from "../services";
import { tokens } from "../theme";

const { Text } = Typography;

interface ResourceItem {
  id: string;
  uri: string;
  name: string;
  resource_type: string;
  description: string;
  created_at: string;
}

const typeColors: Record<string, string> = {
  dataset: "blue", chart: "green", insight: "orange",
  notebook: "purple", workflow: "cyan", connection: "magenta",
};

export default function ResourcesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    api.get(`/api/resources/${projectId}`)
      .then(({ data }) => setResources(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%" }}>
      <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>Resources</h2>
      <p style={{ color: tokens.color.text.muted, marginTop: 4, marginBottom: tokens.spacing.lg }}>
        All datasets, charts, insights, and more — unified resource registry.
      </p>
      {resources.length === 0 ? (
        <Empty description="No resources yet. Upload data or run an analysis." />
      ) : (
        <Table
          dataSource={resources}
          rowKey="id"
          columns={[
            {
              title: "Type", dataIndex: "resource_type", key: "type",
              render: (t: string) => <Tag color={typeColors[t] || "default"}>{t}</Tag>,
              width: 120,
            },
            { title: "Name", dataIndex: "name", key: "name", ellipsis: true },
            {
              title: "URI", dataIndex: "uri", key: "uri",
              render: (u: string) => <Text code style={{ fontSize: 14 }}>{u}</Text>,
            },
            { title: "Description", dataIndex: "description", key: "desc", ellipsis: true },
            {
              title: "Created", dataIndex: "created_at", key: "created",
              render: (t: string) => t ? new Date(t).toLocaleString() : "-",
              width: 180,
            },
          ]}
          size="small"
          pagination={{ pageSize: 20 }}
          style={{ background: tokens.color.bg.card }}
        />
      )}
    </div>
  );
}
