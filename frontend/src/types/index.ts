/** Shared type definitions for Nexa frontend. */

// ---- API ----
export interface ApiResponse<T> {
  data: T;
}

export interface ApiError {
  detail: string;
  code?: string;
}

// ---- Project ----
export interface Project {
  id: string;
  name: string;
  created_at: string;
}

export interface SchemaField {
  name: string;
  type: string;
  missing_count?: number;
  missing_pct?: number;
}

export interface PreviewData {
  columns: string[];
  rows: unknown[][];
  row_count: number;
}

export interface Dataset {
  id: string;
  name: string;
  row_count: number;
  column_count: number;
  schema_info: SchemaField[];
  preview?: PreviewData;
  source_type?: string;
  created_at?: string;
}

// ---- Chat ----
export interface ChartAxisConfig {
  x?: string;
  y?: string | string[];
  color?: string;
  label?: string;
}

export interface ChartData {
  labels: string[];
  datasets: { label: string; data: number[]; backgroundColor?: string | string[] }[];
}

export interface ChartConfig {
  type: "bar" | "line" | "pie" | "scatter";
  title: string;
  options: {
    axes?: ChartAxisConfig;
    data?: ChartData;
    stacked?: boolean;
    legend?: boolean;
    colors?: string[];
  };
}

export interface CredibilityMeta {
  rows_queried: number;
  sql_retries: number;
  mode: "sql" | "skill" | "llm";
  data_coverage: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  columns?: string[];
  rows?: unknown[][];
  row_count?: number;
  charts?: ChartConfig[];
  credibility?: CredibilityMeta;
}

export interface ProgressStage {
  name: string;
  label: string;
  status: "done" | "running" | "pending";
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
}

// ---- Insight ----
export interface Insight {
  id: string;
  question: string;
  content: {
    summary?: string;
    sql?: string;
    row_count?: number;
    charts?: ChartConfig[];
    key_findings?: string[];
    tables?: { columns: string[]; rows: unknown[][] }[];
  };
  created_at: string;
}

// ---- Semantic Layer ----
export interface SemanticMetric {
  id: string;
  dataset_id?: string | null;
  name: string;
  expression: string;
  description?: string;
  format?: string;
  created_at?: string;
}

export interface SemanticDimension {
  id: string;
  dataset_id?: string | null;
  name: string;
  column: string;
  description?: string;
  created_at?: string;
}

export interface SemanticLayer {
  metrics: SemanticMetric[];
  dimensions: SemanticDimension[];
}

// ---- Reports ----
export interface AnalysisReportBlock {
  title: string;
  sql: string;
  columns: string[];
  rows: unknown[][];
  row_count: number;
  finding?: string;
  error?: string | null;
}

export interface AnalysisReportSections {
  executive_summary: string[];
  key_metrics: { label: string; value: string; evidence_title: string }[];
  segment_breakdown: {
    title: string;
    top_rows: unknown[][];
    columns: string[];
    evidence_title: string;
  }[];
  data_quality: { column: string; missing_pct: number }[];
  semantic_summary: {
    metric_count: number;
    dimension_count: number;
    sample_metrics: SemanticMetric[];
    sample_dimensions: SemanticDimension[];
  };
  risks: string[];
  opportunities: string[];
  recommended_follow_up_questions: string[];
}

export interface AnalysisReport {
  id: string;
  project_id: string;
  dataset_id?: string | null;
  title: string;
  content: {
    title: string;
    highlights: string[];
    sections: AnalysisReportSections;
    blocks: AnalysisReportBlock[];
    markdown: string;
  };
  created_at: string;
}

// ---- Notebook ----
export interface NotebookCell {
  id: string;
  cell_type: "markdown" | "sql" | "python";
  content: string;
  sort_order: number;
}

// ---- Auth ----
export interface UserInfo {
  id: string;
  email: string;
}

// ---- Skill ----
export interface SkillDefinition {
  steps: SkillStep[];
}

export interface SkillStep {
  type: "sql" | "visualize" | "insight" | "python" | "transform";
  prompt?: string;
  chart?: string;
}

export interface Skill {
  id?: string;
  name: string;
  title: string;
  description: string;
  category: string;
  icon: string;
  definition: SkillDefinition;
  version: string;
  is_builtin: boolean;
}

export interface SkillExecution {
  id: string;
  skill_id: string;
  status: "pending" | "running" | "done" | "failed";
  inputs: Record<string, string | number | boolean>;
  output: Record<string, unknown> | null;
  started_at: string;
  finished_at: string | null;
}
