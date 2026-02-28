// frontend/src/components/common/EmptyState.jsx
/**
 * Empty state component.
 */

import { clsx } from "clsx";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}) {
  return (
    <div className={clsx("text-center py-12", className)}>
      {Icon && (
        <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-gray-400" />
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900">{title}</h3>
      {description && (
        <p className="mt-2 text-gray-500 max-w-md mx-auto">{description}</p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
