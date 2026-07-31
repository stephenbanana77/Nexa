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
export interface ChartConfig {
  type: "bar" | "line" | "pie" | "scatter";
  title: string;
  options: Record<string, unknown>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  columns?: string[];
  rows?: unknown[][];
  row_count?: number;
  charts?: ChartConfig[];
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
