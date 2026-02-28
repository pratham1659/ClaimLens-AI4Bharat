// frontend/src/components/common/Badge.jsx
/**
 * Badge component for status indicators.
 */

import { clsx } from "clsx";

const variants = {
  success: "badge-success",
  warning: "badge-warning",
  danger: "badge-danger",
  info: "badge-info",
  default: "bg-gray-100 text-gray-700",
};

export function Badge({ children, variant = "default", className }) {
  return (
    <span className={clsx("badge", variants[variant], className)}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }) {
  const statusConfig = {
    pending: { variant: "warning", label: "Pending" },
    processing: { variant: "info", label: "Processing" },
    analyzed: { variant: "success", label: "Analyzed" },
    failed: { variant: "danger", label: "Failed" },
    uploaded: { variant: "info", label: "Uploaded" },
    processed: { variant: "success", label: "Processed" },
  };

  const config = statusConfig[status] || { variant: "default", label: status };

  return <Badge variant={config.variant}>{config.label}</Badge>;
}

export function ApprovalBadge({ likelihood }) {
  const config = {
    high: { variant: "success", label: "High Approval" },
    medium: { variant: "warning", label: "Medium Approval" },
    low: { variant: "danger", label: "Low Approval" },
    very_low: { variant: "danger", label: "Very Low Approval" },
  };

  const { variant, label } = config[likelihood] || config.low;

  return <Badge variant={variant}>{label}</Badge>;
}
