import React, { createContext, useState, useContext, useCallback } from "react";

const ToastContext = createContext(null);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
};

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(
    (message, type = "info", duration = 5000) => {
      const id = Date.now() + Math.random();
      const toast = { id, message, type, duration };

      setToasts((prev) => [...prev, toast]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }

      return id;
    },
    [removeToast]
  );

  const success = useCallback(
    (message, duration) => {
      return addToast(message, "success", duration);
    },
    [addToast]
  );

  const error = useCallback(
    (message, duration) => {
      return addToast(message, "error", duration);
    },
    [addToast]
  );

  const warning = useCallback(
    (message, duration) => {
      return addToast(message, "warning", duration);
    },
    [addToast]
  );

  const info = useCallback(
    (message, duration) => {
      return addToast(message, "info", duration);
    },
    [addToast]
  );

  return (
    <ToastContext.Provider
      value={{ toasts, addToast, removeToast, success, error, warning, info }}
    >
      {children}
    </ToastContext.Provider>
  );
};
