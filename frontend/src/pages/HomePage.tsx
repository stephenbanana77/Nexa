import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Modal, Input, message } from "antd";
import { PlusOutlined, LogoutOutlined } from "@ant-design/icons";
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

  const fetchProjects = async () => {
    try {
      const { data } = await api.get("/api/projects");
      setProjects(data);
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
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
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

        <h2 style={{ color: "#aaa", fontSize: 14, fontWeight: 500, marginBottom: 16 }}>Recent Projects</h2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
          {projects.map((p) => (
            <Card
              key={p.id}
              hoverable
              onClick={() => navigate(`/project/${p.id}`)}
              style={{ background: "#1a1a1a", border: "1px solid #333", cursor: "pointer" }}
              styles={{ body: { padding: 20 } }}
            >
              <div style={{ fontWeight: 500, fontSize: 15, color: "#ddd", marginBottom: 4 }}>{p.name}</div>
              <div style={{ fontSize: 12, color: "#888" }}>
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
            <div style={{ color: "#666", marginTop: 8, fontSize: 13 }}>Create Project</div>
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
