import { Button, Tag } from "antd";
import {
  BarChartOutlined, DotChartOutlined, TrophyOutlined,
  LineChartOutlined, ExperimentOutlined,
} from "@ant-design/icons";
import { tokens } from "../theme";
import type { Skill } from "../types";

const iconMap: Record<string, React.ReactNode> = {
  BarChartOutlined: <BarChartOutlined />,
  DotChartOutlined: <DotChartOutlined />,
  TrophyOutlined: <TrophyOutlined />,
  LineChartOutlined: <LineChartOutlined />,
  ExperimentOutlined: <ExperimentOutlined />,
};

const categoryColors: Record<string, string> = {
  statistics: "#2563EB",
  analysis: "#a78bfa",
  forecast: "#22c55e",
  visualization: "#d29922",
};

interface Props {
  skill: Skill;
  onRun: (skill: Skill) => void;
}

export default function SkillCard({ skill, onRun }: Props) {
  const catColor = categoryColors[skill.category] || tokens.color.text.tertiary;

  return (
    <div
      style={{
        background: tokens.color.bg.card,
        borderRadius: tokens.radius.lg,
        border: `0.5px solid ${tokens.color.border.default}`,
        padding: tokens.spacing.xxl,
        display: "flex",
        flexDirection: "column",
        gap: tokens.spacing.md,
        transition: "border-color 0.2s",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = catColor)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = tokens.color.border.default)}
    >
      <div style={{ fontSize: 28, color: catColor }}>
        {iconMap[skill.icon] || <ExperimentOutlined />}
      </div>
      <div>
        <div style={{ fontSize: tokens.fontSize.lg, fontWeight: 600, color: tokens.color.text.primary }}>
          {skill.title}
        </div>
        <Tag color={catColor} style={{ marginTop: 4, fontSize: 16 }}>
          {skill.category}
        </Tag>
      </div>
      <div style={{ fontSize: tokens.fontSize.sm, color: tokens.color.text.muted, lineHeight: 1.5, flex: 1 }}>
        {skill.description}
      </div>
      <Button
        type="primary"
        size="small"
        onClick={() => onRun(skill)}
        style={{ alignSelf: "flex-start" }}
      >
        Run
      </Button>
    </div>
  );
}
