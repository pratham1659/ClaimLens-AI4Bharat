// frontend/src/context/AuthContext.jsx
/**
 * Authentication context provider.
 * Manages user authentication state and provides auth methods.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { authAPI } from "../services/api";
import toast from "react-hot-toast";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check authentication status on mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await authAPI.getMe();
      setUser(response.data.data);
      setIsAuthenticated(true);
    } catch (error) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    } finally {
      setLoading(false);
    }
  };

  const login = useCallback(async (email, password) => {
    try {
      const response = await authAPI.login(email, password);
      const { access_token, refresh_token } = response.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      // Fetch user data
      const userResponse = await authAPI.getMe();
      setUser(userResponse.data.data);
      setIsAuthenticated(true);

      toast.success("Welcome back!");
      return true;
    } catch (error) {
      const message = error.response?.data?.message || "Login failed";
      toast.error(message);
      return false;
    }
  }, []);

  const register = useCallback(async (data) => {
    try {
      await authAPI.register(data);
      toast.success("Registration successful! Please login.");
      return true;
    } catch (error) {
      const message = error.response?.data?.message || "Registration failed";
      toast.error(message);
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      // Ignore logout errors
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
      setIsAuthenticated(false);
      toast.success("Logged out successfully");
    }
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
