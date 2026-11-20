import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Row, Col, Spin } from "antd";
import { skillService } from "../services";
import SkillCard from "../components/SkillCard";
import SkillExecutionModal from "../components/SkillExecutionModal";
import type { Skill, Dataset } from "../types";
import api from "../api/client";
import "./SkillsPage.css";

export default function SkillsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    skillService.list()
      .then(({ data }) => setSkills(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));

    if (projectId) {
      api.get(`/api/datasets?project_id=${projectId}`)
        .then(({ data }) => setDatasets(Array.isArray(data) ? data : []))
        .catch(() => {});
    }
  }, [projectId]);

  const handleRun = (skill: Skill) => {
    setSelectedSkill(skill);
    setShowModal(true);
  };

  return (
    <main className="skills-page">
      <header className="skills-page-header">
        <div>
          <h1>技能</h1>
          <p>在当前工作区的数据上运行预置分析流程</p>
        </div>
        {!loading && <span className="skills-count">{skills.length} 个可用技能</span>}
      </header>

      {loading ? (
        <div className="skills-loading"><Spin /></div>
      ) : (
        <Row gutter={[12, 12]} className="skills-grid">
          {skills.map((skill) => (
            <Col key={skill.name} xs={24} md={12}>
              <SkillCard skill={skill} onRun={handleRun} />
            </Col>
          ))}
        </Row>
      )}

      <SkillExecutionModal
        skill={selectedSkill}
        projectId={projectId || ""}
        datasets={datasets.map((d) => ({ id: d.id, name: d.name }))}
        open={showModal}
        onClose={() => setShowModal(false)}
      />
    </main>
  );
}
