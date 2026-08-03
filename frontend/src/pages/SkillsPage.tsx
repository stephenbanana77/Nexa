import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Row, Col, Spin } from "antd";
import { skillService } from "../services";
import SkillCard from "../components/SkillCard";
import SkillExecutionModal from "../components/SkillExecutionModal";
import { tokens } from "../theme";
import type { Skill, Dataset } from "../types";
import api from "../api/client";

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
    <div style={{ padding: `${tokens.spacing.xxl}px 0`, maxWidth: 900 }}>
      <h2 style={{ color: tokens.color.text.primary, margin: 0, fontSize: tokens.fontSize.xl }}>
        Skills
      </h2>
      <p style={{ color: tokens.color.text.muted, fontSize: tokens.fontSize.base, marginTop: 4 }}>
        Pre-built analysis pipelines — select one and run on your data
      </p>

      {loading ? (
        <div style={{ textAlign: "center", padding: 40 }}><Spin /></div>
      ) : (
        <Row gutter={[16, 16]} style={{ marginTop: tokens.spacing.lg }}>
          {skills.map((skill) => (
            <Col key={skill.name} xs={24} sm={12} md={8}>
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
    </div>
  );
}
