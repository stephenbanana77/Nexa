import axios from "axios";

const api = axios.create({
  baseURL: "/",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nexa_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const isLoginPage = window.location.pathname === "/login";
      if (!isLoginPage) {
        localStorage.removeItem("nexa_token");
        localStorage.setItem("nexa_redirect", window.location.pathname);
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
