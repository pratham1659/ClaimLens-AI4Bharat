import axios from "axios";
import { getErrorMessage } from "../utils/error";

// Get base URL from environment variable
const baseURL =
  process.env.REACT_APP_API_BASE_URL || "http://localhost:8001/api/v1";

console.log("Axios Base URL:", baseURL); // Debug log

const axiosInstance = axios.create({
  baseURL: baseURL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

// Track if we're already redirecting to prevent loops
let isRedirecting = false;

// Request interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    // Log the full URL being called (for debugging)
    console.log(
      "API Request:",
      config.method?.toUpperCase(),
      config.baseURL + config.url
    );
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Log errors for debugging
    console.error("API Error:", error.response?.status, error.config?.url);

    // Handle network errors (backend not available)
    if (!error.response && error.code === "ERR_NETWORK") {
      // Show user-friendly error message
      const errorMsg =
        "⚠️ Cannot connect to server. Please ensure the backend is running on " +
        baseURL;
      console.error(errorMsg);

      // Create a custom error with user-friendly message
      error.message =
        "Backend server is not available. Please contact your administrator.";
      error.userMessage = errorMsg;
    }

    // Handle timeout errors
    if (error.code === "ECONNABORTED") {
      error.message =
        "Request timeout. The server is taking too long to respond.";
    }

    error.userMessage = getErrorMessage(error, "Request failed");

    // Only handle 401 errors for auth redirect
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname;
      const isLoginPage = currentPath === "/login";
      const isAuthMeEndpoint = error.config?.url?.includes("/auth/me");
      const isLogoutEndpoint = error.config?.url?.includes("/auth/logout");

      // DON'T redirect if:
      // 1. Already on login page
      // 2. It's the /auth/me check (handled by AuthContext)
      // 3. It's a logout request
      // 4. Already redirecting
      if (
        !isLoginPage &&
        !isAuthMeEndpoint &&
        !isLogoutEndpoint &&
        !isRedirecting
      ) {
        isRedirecting = true;

        // Clear any existing auth state
        localStorage.removeItem("user");

        // Redirect to login
        window.location.href = "/login";

        // Reset redirect flag after a delay
        setTimeout(() => {
          isRedirecting = false;
        }, 1000);
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;
