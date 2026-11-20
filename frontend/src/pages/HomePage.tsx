import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Input, Modal, Select, message } from "antd";
import {
  ArrowRightOutlined,
  CalendarOutlined,
  DatabaseOutlined,
  FileDoneOutlined,
  LogoutOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";
import api from "../api/client";
import "./HomePage.css";

interface Project {
  id: string;
  name: string;
  created_at: string;
}

const taskExamples = [
  {
    title: "Weekly business review",
    text: "Every week, compare sales and profit with the previous period, explain the largest changes, and prepare a report for the business owner.",
  },
  {
    title: "Data quality watch",
    text: "Check each new file for missing values, duplicate orders, schema changes, and suspicious negative amounts. Tell me what blocks publication.",
  },
  {
    title: "Campaign performance",
    text: "Review campaign spend, conversions, and ROI by channel. Find underperforming campaigns and show the evidence behind each recommendation.",
  },
];

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [taskBrief, setTaskBrief] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string>();
  const [searchQuery, setSearchQuery] = useState("");
  const { logout } = useAuthStore();
  const navigate = useNavigate();

  const fetchProjects = async () => {
    try {
      const { data } = await api.get("/api/projects");
      const list = data.items || data;
      setProjects(list);
      if (list.length > 0) setSelectedProjectId((current) => current || list[0].id);
    } catch {
      message.error("Projects could not be loaded");
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const visibleProjects = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return projects;
    return projects.filter((project) => project.name.toLowerCase().includes(query));
  }, [projects, searchQuery]);

  const openTask = (brief = taskBrief) => {
    if (!brief.trim()) {
      message.info("Describe the data work you want the agent to take over");
      return;
    }
    if (!selectedProjectId) {
      setModalOpen(true);
      return;
    }
    navigate(`/project/${selectedProjectId}?tab=chat&question=${encodeURIComponent(brief.trim())}`);
  };

  const createProject = async () => {
    if (!newName.trim()) return;
    setLoading(true);
    try {
      const { data } = await api.post("/api/projects", { name: newName.trim() });
      setProjects((prev) => [data, ...prev]);
      setSelectedProjectId(data.id);
      setModalOpen(false);
      setNewName("");
      if (taskBrief.trim()) {
        navigate(`/project/${data.id}?tab=chat&question=${encodeURIComponent(taskBrief.trim())}`);
      } else {
        navigate(`/project/${data.id}?tab=data`);
      }
    } catch {
      message.error("Project could not be created");
    } finally {
      setLoading(false);
    }
  };

  const createSampleProject = async () => {
    setLoading(true);
    try {
      const existing = projects.find((project) => project.name === "Sample - Superstore Demo");
      if (existing) {
        setSelectedProjectId(existing.id);
        navigate(`/project/${existing.id}?tab=chat`);
        return;
      }
      const { data } = await api.post("/api/demo/superstore");
      const projectId = data.project?.id || data.project_id;
      message.success("Demo workspace is ready");
      navigate(`/project/${projectId}?tab=chat`);
    } catch {
      message.error("Demo workspace could not be created");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="home-shell">
      <header className="home-header">
        <button className="wordmark" type="button" onClick={() => navigate("/")}>
          <span className="wordmark-signal" />
          Nexa
        </button>
        <div className="home-header-actions">
          <Button icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>New workspace</Button>
          <Button type="text" icon={<LogoutOutlined />} onClick={logout} aria-label="Log out" />
        </div>
      </header>

      <section className="task-composer" aria-labelledby="task-heading">
        <div className="task-composer-copy">
          <h1 id="task-heading">What data work should Nexa take over?</h1>
          <p>Describe the recurring decision, not the chart. Nexa runs the analysis, keeps the evidence, and turns it into a reusable task.</p>
        </div>

        <div className="task-input-frame">
          <Input.TextArea
            value={taskBrief}
            onChange={(event) => setTaskBrief(event.target.value)}
            placeholder="Example: Every Monday, compare sales and profit with last week. Explain material changes and prepare a report for the regional leads."
            autoSize={{ minRows: 4, maxRows: 8 }}
            onPressEnter={(event) => {
              if ((event.metaKey || event.ctrlKey) && taskBrief.trim()) openTask();
            }}
          />
          <div className="task-input-toolbar">
            <Select
              value={selectedProjectId}
              onChange={setSelectedProjectId}
              placeholder="Choose workspace"
              options={projects.map((project) => ({ value: project.id, label: project.name }))}
              className="workspace-select"
            />
            <Button
              type="primary"
              icon={<ArrowRightOutlined />}
              iconPosition="end"
              onClick={() => openTask()}
              disabled={!taskBrief.trim()}
            >
              Work with agent
            </Button>
          </div>
        </div>

        <div className="task-examples" aria-label="Example data tasks">
          {taskExamples.map((example) => (
            <button
              type="button"
              key={example.title}
              className="task-example"
              onClick={() => {
                setTaskBrief(example.text);
                openTask(example.text);
              }}
            >
              <strong>{example.title}</strong>
              <span>{example.text}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="workspace-section">
        <div className="workspace-section-heading">
          <div>
            <h2>Workspaces</h2>
            <p>Data, recurring tasks, evidence, and deliverables stay together.</p>
          </div>
          <Input
            prefix={<SearchOutlined />}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Find a workspace"
            allowClear
            className="workspace-search"
          />
        </div>

        {visibleProjects.length === 0 ? (
          <div className="workspace-empty">
            <DatabaseOutlined />
            <div>
              <strong>No workspace yet</strong>
              <span>Create one for your own data or open a working demo.</span>
            </div>
            <Button type="primary" onClick={() => setModalOpen(true)}>Create workspace</Button>
            <Button onClick={createSampleProject} loading={loading}>Open demo</Button>
          </div>
        ) : (
          <div className="workspace-list">
            {visibleProjects.map((project) => (
              <button
                type="button"
                className="workspace-row"
                key={project.id}
                onClick={() => navigate(`/project/${project.id}?tab=chat`)}
              >
                <span className="workspace-icon"><DatabaseOutlined /></span>
                <span className="workspace-name">
                  <strong>{project.name}</strong>
                  <small>Created {new Date(project.created_at).toLocaleDateString()}</small>
                </span>
                <span className="workspace-capability"><CalendarOutlined /> Repeatable tasks</span>
                <span className="workspace-capability"><FileDoneOutlined /> Evidence-backed reports</span>
                <ArrowRightOutlined className="workspace-arrow" />
              </button>
            ))}
          </div>
        )}
      </section>

      <Modal
        title="Create workspace"
        open={modalOpen}
        onOk={createProject}
        onCancel={() => setModalOpen(false)}
        confirmLoading={loading}
        okText="Create"
      >
        <p className="modal-helper">Use one workspace for data sources, analysis tasks, and reports that share the same business context.</p>
        <Input
          placeholder="Workspace name"
          value={newName}
          onChange={(event) => setNewName(event.target.value)}
          onPressEnter={createProject}
          autoFocus
        />
      </Modal>
    </main>
  );
}
