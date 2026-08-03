/** API service layer — typed, centralized HTTP calls. */
import api from "../api/client";
import type {
  Project,
  Dataset,
  Conversation,
  Insight,
  NotebookCell,
  UserInfo,
  PreviewData,
} from "../types";

// ---- Auth ----
export const authService = {
  register: (email: string, password: string) =>
    api.post("/api/auth/register", { email, password }),

  login: (email: string, password: string) =>
    api.post("/api/auth/login", { email, password }),

  getMe: () => api.get<UserInfo>("/api/auth/me"),
};

// ---- Projects ----
export const projectService = {
  list: () => api.get<Project[]>("/api/projects"),

  get: (id: string) => api.get<Project>(`/api/projects/${id}`),

  create: (name: string) => api.post<Project>("/api/projects", { name }),
};

// ---- Datasets ----
export const datasetService = {
  list: (projectId: string) =>
    api.get<Dataset[]>(`/api/datasets?project_id=${projectId}`),

  upload: (projectId: string, formData: FormData) =>
    api.post<Dataset>(`/api/datasets/upload?project_id=${projectId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  getPreview: (datasetId: string, limit = 1000) =>
    api.get<PreviewData>(`/api/datasets/${datasetId}/preview?limit=${limit}`),

  query: (datasetId: string, sql: string) =>
    api.post(`/api/datasets/${datasetId}/query`, { sql }),

  connectMySQL: (config: { project_id: string; host: string; port: number; user: string; password: string; database: string }) =>
    api.post("/api/datasets/connect-mysql", config),
};

// ---- Chat ----
export const chatService = {
  listConversations: (projectId: string) =>
    api.get<Conversation[]>(`/api/chat/conversations/${projectId}`),
};

// ---- Insights ----
export const insightService = {
  listByProject: (projectId: string) =>
    api.get<Insight[]>(`/api/insights/project/${projectId}`),

  create: (data: { project_id: string; question: string; content: Record<string, unknown> }) =>
    api.post("/api/insights/", data),

  delete: (id: string) => api.delete(`/api/insights/${id}`),
};

// ---- Notebooks ----
export const notebookService = {
  listByProject: (projectId: string) =>
    api.get(`/api/notebooks/project/${projectId}`),

  get: (id: string) => api.get(`/api/notebooks/${id}`),

  create: (data: { project_id: string; cells?: Partial<NotebookCell>[] }) =>
    api.post("/api/notebooks/", data),

  addCell: (notebookId: string, data: { cell_type: string; content: string; sort_order: number }) =>
    api.post(`/api/notebooks/${notebookId}/cells`, data),

  updateCell: (cellId: string, data: { content: string }) =>
    api.put(`/api/notebooks/cells/${cellId}`, data),

  deleteCell: (cellId: string) =>
    api.delete(`/api/notebooks/cells/${cellId}`),
};

// ---- Skills ----
export const skillService = {
  list: (category?: string) =>
    api.get(`/api/skills${category ? `?category=${category}` : ""}`),

  get: (id: string) => api.get(`/api/skills/${id}`),

  getCategories: () => api.get("/api/skills/categories"),

  install: (data: {
    name: string; title: string; description?: string;
    category?: string; icon?: string; definition: Record<string, unknown>;
    version?: string;
  }) => api.post("/api/skills/install", data),

  delete: (id: string) => api.delete(`/api/skills/${id}`),

  getExecutions: (projectId: string) =>
    api.get(`/api/skills/executions/${projectId}`),
};

export { api };
