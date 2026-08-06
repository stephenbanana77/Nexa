import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Modal, Input, message, Tag } from "antd";
import { PlusOutlined, LogoutOutlined, SearchOutlined } from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";
import api from "../api/client";

interface Project {
  id: string;
  name: string;
  created_at: string;
}

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const { logout } = useAuthStore();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);

  const createSampleProject = async () => {
    setLoading(true);
    try {
      // Check if sample project already exists
      const existing = projects.find((p: Project) => p.name === "Sample - Superstore");
      if (existing) {
        navigate(`/project/${existing.id}`);
        return;
      }
      const proj = await api.post("/api/projects", { name: "Sample - Superstore" });
      const pid = proj.data.id;
      // Use a small built-in CSV for demo
      const csv = "Category,Sales,Profit\nFurniture,10000,2000\nOffice Supplies,15000,3500\nTechnology,25000,8000";
      const blob = new Blob([csv], { type: "text/csv" });
      const form = new FormData();
      form.append("file", blob, "superstore_sample.csv");
      await api.post(`/api/datasets/upload?project_id=${pid}`, form);
      message.success("Sample project created! Try asking: 'Show sales by category'");
      navigate(`/project/${pid}`);
    } catch { message.error("Failed to create sample project"); }
    finally { setLoading(false); }
  };

  const doSearch = async (q: string) => {
    if (!q.trim()) { setSearchResults([]); return; }
    try {
      const { data } = await api.get(`/api/search?q=${encodeURIComponent(q)}`);
      setSearchResults(data.results || []);
    } catch { setSearchResults([]); }
  };

  const fetchProjects = async () => {
    try {
      const { data } = await api.get("/api/projects");
      setProjects(data.items || data);
    } catch {
      message.error("Failed to load projects");
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const createProject = async () => {
    if (!newName.trim()) return;
    setLoading(true);
    try {
      const { data } = await api.post("/api/projects", { name: newName });
      setProjects((prev) => [data, ...prev]);
      setModalOpen(false);
      setNewName("");
    } catch {
      message.error("Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d0d", padding: 40 }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 600, color: "#fff", margin: 0 }}>Nexa</h1>
            <p style={{ color: "#888", margin: "4px 0 0" }}>Your AI Data Analyst</p>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
              New Project
            </Button>
            <Button icon={<LogoutOutlined />} onClick={logout}>
              Logout
            </Button>
          </div>
        </div>

        <div style={{ marginBottom: 24 }}>
          <Input
            prefix={<SearchOutlined style={{ color: "#888" }} />}
            placeholder="Search projects, insights, datasets..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); doSearch(e.target.value); }}
            allowClear
            size="large"
            style={{ background: "#1a1a1a", fontSize: 18 }}
          />
          {searchResults.length > 0 && (
            <div style={{ marginTop: 12, background: "#1a1a1a", border: "0.5px solid #333", borderRadius: 8, padding: 8 }}>
              {searchResults.map((r: any, i: number) => (
                <div
                  key={i}
                  onClick={() => navigate(r.link)}
                  style={{
                    padding: "8px 12px", cursor: "pointer", borderRadius: 6,
                    display: "flex", alignItems: "center", gap: 8,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#252525")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <Tag color={r.type === "project" ? "blue" : r.type === "insight" ? "green" : r.type === "workflow" ? "orange" : "default"} style={{ margin: 0 }}>
                    {r.type}
                  </Tag>
                  <span style={{ color: "#ddd", fontSize: 17 }}>{r.title}</span>
                  {r.subtitle && <span style={{ color: "#888", fontSize: 15 }}>{r.subtitle}</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {projects.length === 0 && (
          <div style={{ textAlign: "center", padding: "60px 0" }}>
            <h2 style={{ color: "#ddd", fontSize: 22, marginBottom: 8 }}>Welcome to Nexa</h2>
            <p style={{ color: "#888", fontSize: 16, marginBottom: 24 }}>
              Upload a CSV or Excel file and ask questions in plain English.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <Button type="primary" size="large" onClick={() => setModalOpen(true)}>Upload Your Data</Button>
              <Button size="large" onClick={createSampleProject} loading={loading}>Try Sample Data</Button>
            </div>
          </div>
        )}

        {projects.length > 0 && <h2 style={{ color: "#aaa", fontSize: 16, fontWeight: 500, marginBottom: 16 }}>Recent Projects</h2>}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
          {projects.map((p) => (
            <Card
              key={p.id}
              hoverable
              onClick={() => navigate(`/project/${p.id}`)}
              style={{ background: "#1a1a1a", border: "1px solid #333", cursor: "pointer" }}
              styles={{ body: { padding: 20 } }}
            >
              <div style={{ fontWeight: 500, fontSize: 17, color: "#ddd", marginBottom: 4 }}>{p.name}</div>
              <div style={{ fontSize: 16, color: "#888" }}>
                Created {new Date(p.created_at).toLocaleDateString()}
              </div>
            </Card>
          ))}
          <Card
            hoverable
            onClick={() => setModalOpen(true)}
            style={{
              background: "#1a1a1a",
              border: "1px dashed #444",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 100,
            }}
            styles={{ body: { padding: 20, width: "100%", textAlign: "center" } }}
          >
            <PlusOutlined style={{ fontSize: 24, color: "#555" }} />
            <div style={{ color: "#666", marginTop: 8, fontSize: 16 }}>Create Project</div>
          </Card>
        </div>
      </div>

      <Modal
        title="New Project"
        open={modalOpen}
        onOk={createProject}
        onCancel={() => setModalOpen(false)}
        confirmLoading={loading}
      >
        <Input
          placeholder="Project name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onPressEnter={createProject}
          size="large"
        />
      </Modal>
    </div>
  );
}
