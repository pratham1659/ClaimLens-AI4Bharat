// frontend/src/services/api.js
/**
 * API service for backend communication.
 * Handles authentication, request/response interceptors, and error handling.
 */

import axios from "axios";
import { getErrorMessage } from "../utils/error";

const API_BASE_URL = process.env.REACT_APP_API_URL || "/api/v1";

const normalizeBrowserAccessibleUrl = (url) => {
  if (!url) return url;

  try {
    const parsed = new URL(url);
    if (parsed.hostname === "localstack") {
      parsed.hostname = window.location.hostname || "localhost";
    }
    return parsed.toString();
  } catch {
    return url;
  }
};

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Request interceptor for adding auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor for handling errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", refresh_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    error.userMessage = getErrorMessage(error, "Request failed");

    return Promise.reject(error);
  },
);

// Auth API
export const authAPI = {
  login: (email, password) => api.post("/auth/login", { email, password }),

  register: (data) => api.post("/auth/register", data),

  logout: () => api.post("/auth/logout"),

  getMe: () => api.get("/auth/me"),

  refreshToken: (refreshToken) =>
    api.post("/auth/refresh", { refresh_token: refreshToken }),
};

// Claims API
export const claimsAPI = {
  list: (params = {}) => api.get("/claims", { params }),

  get: (claimId) => api.get(`/claims/${claimId}`),

  create: (data) => api.post("/claims", data),

  update: (claimId, data) => api.patch(`/claims/${claimId}`, data),

  delete: (claimId) => api.delete(`/claims/${claimId}`),
};

// Documents API
export const documentsAPI = {
  uploadDirect: (claimId, documentType, file) => {
    const formData = new FormData();
    formData.append("claim_id", claimId);
    formData.append("document_type", documentType);
    formData.append("file", file);

    return api.post("/documents/upload-direct", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      timeout: 120000,
    });
  },

  getUploadUrl: (data) => api.post("/documents/upload-url", data),

  uploadToS3: async (uploadUrl, file, contentType) => {
    const browserUrl = normalizeBrowserAccessibleUrl(uploadUrl);
    return axios.put(browserUrl, file, {
      headers: {
        "Content-Type": contentType,
      },
    });
  },

  process: (documentId) =>
    api.post(`/documents/${documentId}/process`, null, {
      timeout: 300000,
    }),

  get: (documentId) => api.get(`/documents/${documentId}`),

  getText: (documentId) => api.get(`/documents/${documentId}/text`),

  getDownloadUrl: (documentId) =>
    api.get(`/documents/${documentId}/download-url`),

  delete: (documentId) => api.delete(`/documents/${documentId}`),

  listByClaimId: (claimId) => api.get(`/documents/claim/${claimId}`),
};

// Analysis API
export const analysisAPI = {
  analyze: (claimId) => api.post("/analysis/analyze", { claim_id: claimId }),

  get: (claimId) => api.get(`/analysis/claim/${claimId}`),

  getHistory: (claimId) => api.get(`/analysis/claim/${claimId}/history`),
};

// Policies API
export const policiesAPI = {
  list: () => api.get("/policies"),

  readiness: () => api.get("/policies/search/readiness"),

  getClauses: (documentId, params = {}) =>
    api.get(`/policies/${documentId}/clauses`, { params }),

  search: (query, documentIds = null, limit = 10) =>
    api.post("/policies/search", { query, document_ids: documentIds, limit }),
};

export default api;
