import { Button, Tag } from "antd";
import {
  BarChartOutlined, DotChartOutlined, TrophyOutlined,
  LineChartOutlined, ExperimentOutlined, PlayCircleOutlined,
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

const categoryLabels: Record<string, string> = {
  statistics: "统计分析",
  analysis: "业务分析",
  forecast: "趋势预测",
  visualization: "数据可视化",
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
        borderRadius: tokens.radius.md,
        border: `1px solid ${tokens.color.border.light}`,
        padding: 18,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        height: "100%",
        minHeight: 156,
        transition: "border-color 0.15s ease, background-color 0.15s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = tokens.color.border.default;
        e.currentTarget.style.backgroundColor = tokens.color.bg.elevated;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = tokens.color.border.light;
        e.currentTarget.style.backgroundColor = tokens.color.bg.card;
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
        <div style={{
          width: 34,
          height: 34,
          borderRadius: tokens.radius.md,
          display: "grid",
          placeItems: "center",
          flex: "0 0 auto",
          fontSize: 18,
          color: catColor,
          background: `${catColor}14`,
          border: `1px solid ${catColor}30`,
        }}>
          {iconMap[skill.icon] || <ExperimentOutlined />}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 16, lineHeight: 1.35, fontWeight: 600, color: tokens.color.text.primary }}>
            {skill.title}
          </div>
          <Tag
            color={catColor}
            style={{ margin: "4px 0 0", fontSize: 11, lineHeight: "18px", paddingInline: 6 }}
          >
            {categoryLabels[skill.category] || skill.category}
          </Tag>
        </div>
        <Button
          type="text"
          size="small"
          icon={<PlayCircleOutlined />}
          onClick={() => onRun(skill)}
          style={{ flex: "0 0 auto", color: tokens.color.text.secondary }}
        >
          运行
        </Button>
      </div>
      <div style={{
        fontSize: 14,
        color: tokens.color.text.tertiary,
        lineHeight: 1.6,
        display: "-webkit-box",
        WebkitBoxOrient: "vertical",
        WebkitLineClamp: 2,
        overflow: "hidden",
      }}>
        {skill.description}
      </div>
    </div>
  );
}
