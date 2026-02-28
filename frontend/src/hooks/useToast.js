import { useState, useCallback } from "react";

export const useToast = () => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(
    (message, type = "info", duration = 5000) => {
      const id = Date.now();
      setToasts((prev) => [...prev, { id, message, type }]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  const success = useCallback(
    (message, duration) => {
      addToast(message, "success", duration);
    },
    [addToast]
  );

  const error = useCallback(
    (message, duration) => {
      addToast(message, "error", duration);
    },
    [addToast]
  );

  const warning = useCallback(
    (message, duration) => {
      addToast(message, "warning", duration);
    },
    [addToast]
  );

  const info = useCallback(
    (message, duration) => {
      addToast(message, "info", duration);
    },
    [addToast]
  );

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };
};
