import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Table, Tag, Spin, Empty, Typography, Card, Button } from "antd";
import { LinkOutlined, NodeIndexOutlined, CloseOutlined } from "@ant-design/icons";
import { api } from "../services";
import { tokens } from "../theme";

const { Text } = Typography;

interface ResourceItem {
  id: string;
  uri: string;
  type?: string;
  resource_type?: string;
  name: string;
  description: string;
  created_at: string;
  project_id?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

interface LineageDetail {
  resource: ResourceItem;
  references: (ResourceItem & { relation?: string })[];
  referrers: (ResourceItem & { relation?: string })[];
}

const typeColors: Record<string, string> = {
  dataset: "blue", chart: "green", insight: "orange",
  notebook: "purple", workflow: "cyan", connection: "magenta",
};

const typeIcons: Record<string, string> = {
  dataset: "\ud83d\udcca", chart: "\ud83d\udcc8", insight: "\ud83d\udca1",
  notebook: "\ud83d\udcd3", workflow: "\u2699\ufe0f", connection: "\ud83d\udd17",
};

function rtype(r: ResourceItem) {
  return r.type || r.resource_type || "unknown";
}

export default function ResourcesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [lineage, setLineage] = useState<LineageDetail | null>(null);
  const [lineageLoading, setLineageLoading] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    api.get(`/api/resources/${projectId}`)
      .then(({ data }) => setResources(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  const showLineage = async (uri: string) => {
    setSelected(uri);
    setLineageLoading(true);
    try {
      const { data } = await api.get(`/api/resources/detail/${encodeURIComponent(uri)}`);
      setLineage(data);
    } catch {
      setLineage(null);
    } finally {
      setLineageLoading(false);
    }
  };

  const closeLineage = () => { setSelected(null); setLineage(null); };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>;

  return (
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, width: "100%" }}>
      <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>Resources</h2>
      <p style={{ color: tokens.color.text.muted, marginTop: 4, marginBottom: tokens.spacing.lg }}>
        Click a resource to explore its lineage — upstream data sources and downstream consumers.
      </p>

      {resources.length === 0 ? (
        <Empty description="No resources yet. Upload data or run an analysis." />
      ) : (
        <Table
          dataSource={resources}
          rowKey="uri"  // use uri as unique key
          onRow={(r) => ({
            onClick: () => showLineage(r.uri),
            style: {
              cursor: "pointer",
              background: selected === r.uri ? "#1b2635" : undefined,
            },
          })}
          columns={[
            {
              title: "Type", dataIndex: "resource_type", key: "type",
              render: (t: string) => <Tag color={typeColors[t] || "default"}>{t}</Tag>,
              width: 100,
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
              width: 160,
            },
          ]}
          size="small"
          pagination={{ pageSize: 20 }}
          style={{ background: tokens.color.bg.card }}
        />
      )}

      {/* Lineage panel */}
      {selected && (
        <Card
          title={
            <span>
              <NodeIndexOutlined style={{ marginRight: 8 }} />
              Lineage — {lineage?.resource?.name || selected}
            </span>
          }
          extra={<Button type="text" icon={<CloseOutlined />} onClick={closeLineage} />}
          style={{
            marginTop: 24, background: tokens.color.bg.card,
            border: `0.5px solid ${tokens.color.border.default}`,
            borderRadius: tokens.radius.md,
          }}
        >
          {lineageLoading ? (
            <Spin />
          ) : lineage ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              {/* Upstream — references */}
              <div>
                <div style={{ fontSize: 14, color: "#60a5fa", marginBottom: 8, fontWeight: 600 }}>
                  <LinkOutlined style={{ marginRight: 6 }} />
                  References (this depends on)
                </div>
                {lineage.references.length === 0 ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>No upstream dependencies</Text>
                ) : (
                  lineage.references.map((r) => (
                    <div
                      key={r.uri}
                      onClick={(e) => { e.stopPropagation(); showLineage(r.uri); }}
                      style={{
                        padding: "6px 10px", marginBottom: 4, cursor: "pointer",
                        background: "#0d1520", borderRadius: 4, border: "0.5px solid #1e2d3d",
                        display: "flex", alignItems: "center", gap: 8,
                      }}
                    >
                      <span style={{ fontSize: 14 }}>{typeIcons[rtype(r)] || "\ud83d\udcc4"}</span>
                      <span style={{ color: "#e6edf3", fontSize: 13, flex: 1 }}>{r.name}</span>
                      <Tag style={{ margin: 0, fontSize: 11 }} color={typeColors[rtype(r)] || "default"}>
                        {rtype(r)} {r.relation ? `· ${r.relation}` : ""}
                      </Tag>
                    </div>
                  ))
                )}
              </div>
              {/* Downstream — referrers */}
              <div>
                <div style={{ fontSize: 14, color: "#22c55e", marginBottom: 8, fontWeight: 600 }}>
                  <LinkOutlined style={{ marginRight: 6 }} />
                  Referrers (depends on this)
                </div>
                {lineage.referrers.length === 0 ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>No downstream consumers</Text>
                ) : (
                  lineage.referrers.map((r) => (
                    <div
                      key={r.uri}
                      onClick={(e) => { e.stopPropagation(); showLineage(r.uri); }}
                      style={{
                        padding: "6px 10px", marginBottom: 4, cursor: "pointer",
                        background: "#0d1520", borderRadius: 4, border: "0.5px solid #1e2d3d",
                        display: "flex", alignItems: "center", gap: 8,
                      }}
                    >
                      <span style={{ fontSize: 14 }}>{typeIcons[rtype(r)] || "\ud83d\udcc4"}</span>
                      <span style={{ color: "#e6edf3", fontSize: 13, flex: 1 }}>{r.name}</span>
                      <Tag style={{ margin: 0, fontSize: 11 }} color={typeColors[rtype(r)] || "default"}>
                        {rtype(r)} {r.relation ? `· ${r.relation}` : ""}
                      </Tag>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <Text type="secondary">Could not load lineage information.</Text>
          )}
        </Card>
      )}
    </div>
  );
}
