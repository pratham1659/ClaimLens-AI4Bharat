// frontend/src/components/common/ConfirmDialog.jsx
/**
 * Confirmation dialog component.
 */

import { AlertTriangle } from "lucide-react";
import { Modal } from "./Modal";

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title = "Confirm Action",
  message = "Are you sure you want to proceed?",
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "danger",
}) {
  const variantStyles = {
    danger: "btn-danger",
    warning: "bg-warning-500 text-white hover:bg-warning-600",
    primary: "btn-primary",
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <div className="text-center">
        <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-danger-50 mb-4">
          <AlertTriangle className="h-6 w-6 text-danger-500" />
        </div>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex gap-3 justify-center">
          <button onClick={onClose} className="btn-secondary">
            {cancelText}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={variantStyles[variant]}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </Modal>
  );
}
