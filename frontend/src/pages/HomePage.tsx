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
  UploadOutlined,
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
    title: "每周经营复盘",
    text: "每周对比销售额和利润与上一周期的变化，解释波动最大的部分，并为业务负责人准备一份报告。",
  },
  {
    title: "数据质量监控",
    text: "检查每个新文件中的缺失值、重复订单、字段变化和异常负数，并告诉我哪些问题会阻止报告发布。",
  },
  {
    title: "营销活动分析",
    text: "按渠道分析活动花费、转化和 ROI，找出表现不佳的活动，并展示每项建议背后的数据证据。",
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
      message.error("工作区加载失败，请刷新页面重试");
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
      message.info("请先描述希望 Agent 接管的数据工作");
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
      message.error("工作区创建失败，请稍后重试");
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
      message.success("演示工作区已准备好");
      navigate(`/project/${projectId}?tab=chat`);
    } catch {
      message.error("演示工作区创建失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const startDataWorkspace = () => {
    if (selectedProjectId) {
      navigate(`/project/${selectedProjectId}?tab=data`);
      return;
    }
    setModalOpen(true);
  };

  return (
    <main className="home-shell">
      <header className="home-header">
        <button className="wordmark" type="button" onClick={() => navigate("/")}>
          <span className="wordmark-signal" />
          Nexa
        </button>
        <div className="home-header-actions">
          <Button icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建工作区</Button>
          <Button type="text" icon={<LogoutOutlined />} onClick={logout} aria-label="退出登录" title="退出登录" />
        </div>
      </header>

      <section className="task-composer" aria-labelledby="task-heading">
        <div className="task-composer-copy">
          <h1 id="task-heading">想让 Nexa 接管什么数据工作？</h1>
          <p>描述需要反复完成的业务判断，不必指定图表。Nexa 会执行分析、保留证据，并把它沉淀为可重复任务。</p>
        </div>

        <div className="task-input-frame">
          <Input.TextArea
            value={taskBrief}
            onChange={(event) => setTaskBrief(event.target.value)}
            placeholder="例如：每周一对比销售额和利润与上周的变化，解释重要波动，并为各区域负责人准备报告。"
            autoSize={{ minRows: 4, maxRows: 8 }}
            onPressEnter={(event) => {
              if ((event.metaKey || event.ctrlKey) && taskBrief.trim()) openTask();
            }}
          />
          {projects.length === 0 ? (
            <div className="task-input-first-run">
              <span>先创建工作区并放入数据，之后就能把任务交给 Agent。</span>
              <div>
                <Button type="primary" icon={<UploadOutlined />} onClick={startDataWorkspace}>
                  新建工作区并上传
                </Button>
                <Button onClick={createSampleProject} loading={loading}>打开示例</Button>
              </div>
            </div>
          ) : (
            <div className="task-input-toolbar">
              <Select
                value={selectedProjectId}
                onChange={setSelectedProjectId}
                placeholder="选择工作区"
                options={projects.map((project) => ({ value: project.id, label: project.name === "Sample - Superstore Demo" ? "示例 - Superstore 演示" : project.name }))}
                className="workspace-select"
              />
              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                iconPosition="end"
                onClick={() => openTask()}
                disabled={!taskBrief.trim()}
              >
                交给 Agent
              </Button>
            </div>
          )}
        </div>

        <div className="task-examples" aria-label="数据任务示例">
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
            <h2>工作区</h2>
            <p>把数据、重复任务、证据和交付物放在同一个业务上下文中。</p>
          </div>
          <Input
            prefix={<SearchOutlined />}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="搜索工作区"
            allowClear
            className="workspace-search"
          />
        </div>

        {visibleProjects.length === 0 ? (
          <div className="workspace-empty">
            <DatabaseOutlined />
            <div className="workspace-empty-copy">
              <strong>从一份数据开始</strong>
              <span>上传 CSV / Excel 就能开始分析，不需要先连接 MySQL。</span>
            </div>
            <div className="workspace-empty-actions">
              <Button type="primary" icon={<UploadOutlined />} onClick={startDataWorkspace}>
                新建工作区并上传
              </Button>
              <Button onClick={createSampleProject} loading={loading}>打开示例</Button>
            </div>
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
                  <strong>{project.name === "Sample - Superstore Demo" ? "示例 - Superstore 演示" : project.name}</strong>
                  <small>创建于 {new Date(project.created_at).toLocaleDateString("zh-CN")}</small>
                </span>
                <span className="workspace-capability"><CalendarOutlined /> 可重复任务</span>
                <span className="workspace-capability"><FileDoneOutlined /> 有证据的报告</span>
                <ArrowRightOutlined className="workspace-arrow" />
              </button>
            ))}
          </div>
        )}
      </section>

      <Modal
        title="创建工作区"
        open={modalOpen}
        onOk={createProject}
        onCancel={() => setModalOpen(false)}
        confirmLoading={loading}
        okText="创建"
      >
        <p className="modal-helper">创建后可以直接上传 CSV / Excel；不需要先连接 MySQL。</p>
        <Input
          placeholder="工作区名称"
          value={newName}
          onChange={(event) => setNewName(event.target.value)}
          onPressEnter={createProject}
          autoFocus
        />
      </Modal>
    </main>
  );
}
