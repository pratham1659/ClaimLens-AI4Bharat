// frontend/src/components/claims/ClaimCard.jsx
/**
 * Claim card component for displaying claim summary - compact version.
 */

import { useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Calendar,
  User,
  ArrowRight,
  Trash2,
  AlertTriangle,
  X,
} from "lucide-react";
import { format } from "date-fns";
import { StatusBadge, ApprovalBadge } from "../common/Badge";

export function ClaimCard({ claim, onDelete }) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = () => {
    onDelete(claim.id);
    setShowDeleteModal(false);
  };

  return (
    <>
      <div className="card p-3 sm:p-4 hover:shadow-md transition-shadow">
        {/* Desktop: Single row layout */}
        <div className="hidden sm:flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="w-9 h-9 bg-primary-50 rounded-lg flex items-center justify-center flex-shrink-0">
              <FileText className="w-4 h-4 text-primary-600" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3">
                <h3 className="font-semibold text-gray-900 text-sm truncate">
                  {claim.claim_number}
                </h3>
                <StatusBadge status={claim.status} />
                {claim.analysis_summary && (
                  <ApprovalBadge
                    likelihood={claim.analysis_summary.approval_likelihood}
                  />
                )}
              </div>
              <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <User className="w-3 h-3" />
                  <span className="truncate max-w-[120px]">
                    {claim.patient_name}
                  </span>
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {format(new Date(claim.created_at), "MMM d, yyyy")}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={handleDeleteClick}
              className="p-1.5 text-gray-400 hover:text-danger-500 transition-colors"
              title="Delete claim"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <Link
              to={`/claims/${claim.id}`}
              className="flex items-center gap-1 text-primary-600 hover:text-primary-700 font-medium text-sm"
            >
              View
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* Mobile: Stacked compact layout */}
        <div className="flex sm:hidden flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <div className="w-8 h-8 bg-primary-50 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-4 h-4 text-primary-600" />
              </div>
              <div className="min-w-0">
                <h3 className="font-semibold text-gray-900 text-sm truncate">
                  {claim.claim_number}
                </h3>
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <User className="w-3 h-3" />
                  <span className="truncate">{claim.patient_name}</span>
                </span>
              </div>
            </div>
            <StatusBadge status={claim.status} />
          </div>
          <div className="flex items-center justify-between pl-10">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Calendar className="w-3 h-3" />
                {format(new Date(claim.created_at), "MMM d")}
              </span>
              {claim.analysis_summary && (
                <ApprovalBadge
                  likelihood={claim.analysis_summary.approval_likelihood}
                />
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleDeleteClick}
                className="p-1 text-gray-400 hover:text-danger-500 transition-colors"
                title="Delete claim"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <Link
                to={`/claims/${claim.id}`}
                className="flex items-center gap-0.5 text-primary-600 hover:text-primary-700 font-medium text-xs"
              >
                View
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-5 sm:p-6 relative">
            <button
              onClick={() => setShowDeleteModal(false)}
              className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 touch-manipulation"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-danger-50 mb-4">
                <AlertTriangle className="h-6 w-6 text-danger-500" />
              </div>

              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Delete Claim
              </h3>

              <p className="text-sm text-gray-600 mb-4">
                Are you sure you want to delete claim{" "}
                <span className="font-semibold">{claim.claim_number}</span>?
              </p>

              <p className="text-xs text-gray-500 mb-6">
                This action cannot be undone. All data associated with this
                claim will be permanently removed.
              </p>

              <div className="flex flex-col-reverse sm:flex-row gap-2 sm:gap-3 justify-center">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="btn-secondary w-full sm:w-auto py-2.5 text-sm font-medium touch-manipulation"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  className="bg-danger-500 text-white hover:bg-danger-600 px-4 py-2.5 rounded-lg text-sm font-medium w-full sm:w-auto touch-manipulation transition-colors"
                >
                  Delete Claim
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
