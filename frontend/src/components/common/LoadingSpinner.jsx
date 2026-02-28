// frontend/src/components/common/LoadingSpinner.jsx
/**
 * Loading spinner component.
 */

import { clsx } from "clsx";

export function LoadingSpinner({ size = "md", className }) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };

  return (
    <div className={clsx("flex items-center justify-center", className)}>
      <div
        className={clsx(
          "animate-spin rounded-full border-2 border-gray-300 border-t-primary-600",
          sizeClasses[size],
        )}
      />
    </div>
  );
}
