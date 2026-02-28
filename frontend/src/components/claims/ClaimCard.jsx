// frontend/src/components/claims/ClaimCard.jsx
/**
 * Claim card component for displaying claim summary.
 */

import { Link } from "react-router-dom";
import { FileText, Calendar, User, ArrowRight, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { StatusBadge, ApprovalBadge } from "../common/Badge";

export function ClaimCard({ claim, onDelete }) {
  return (
    <div className="card p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-primary-50 rounded-lg flex items-center justify-center">
            <FileText className="w-6 h-6 text-primary-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">
              {claim.claim_number}
            </h3>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <User className="w-4 h-4" />
                {claim.patient_name}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {format(new Date(claim.created_at), "MMM d, yyyy")}
              </span>
            </div>
          </div>
        </div>
        <StatusBadge status={claim.status} />
      </div>

      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {claim.analysis_summary && (
            <ApprovalBadge
              likelihood={claim.analysis_summary.approval_likelihood}
            />
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onDelete(claim.id)}
            className="p-2 text-gray-400 hover:text-danger-500 transition-colors"
          >
            <Trash2 className="w-5 h-5" />
          </button>
          <Link
            to={`/claims/${claim.id}`}
            className="flex items-center gap-1 text-primary-600 hover:text-primary-700 font-medium"
          >
            View Details
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
