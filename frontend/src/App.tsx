import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, Spin, theme } from "antd";
import { useAuthStore } from "./stores/auth";
import ErrorBoundary from "./components/ErrorBoundary";

const LoginPage = lazy(() => import("./pages/LoginPage"));
const HomePage = lazy(() => import("./pages/HomePage"));
const ProjectPage = lazy(() => import("./pages/ProjectPage"));
const SkillsPage = lazy(() => import("./pages/SkillsPage"));
const WorkflowEditPage = lazy(() => import("./pages/WorkflowEditPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ResourcesPage = lazy(() => import("./pages/ResourcesPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

function PageFallback() {
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#0d0d0d" }}>
      <Spin size="large" />
    </div>
  );
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: "#f06436",
          colorPrimaryHover: "#fb7b52",
          colorPrimaryBg: "#211b18",
          colorBgContainer: "#1a1d1a",
          colorBgElevated: "#202420",
          colorText: "#e3e7e2",
          colorTextSecondary: "#8e968e",
          colorBorder: "#3a3f3a",
          borderRadius: 6,
          fontSize: 14,
          fontFamily: "'IBM Plex Sans', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        },
      }}
    >
      <BrowserRouter>
        <ErrorBoundary>
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <HomePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/project/:projectId"
                element={
                  <ProtectedRoute>
                    <ProjectPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/project/:projectId/skills"
                element={
                  <ProtectedRoute>
                    <SkillsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/project/:projectId/workflow/:workflowId"
                element={
                  <ProtectedRoute>
                    <WorkflowEditPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/project/:projectId/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/project/:projectId/resources"
                element={
                  <ProtectedRoute>
                    <ResourcesPage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
