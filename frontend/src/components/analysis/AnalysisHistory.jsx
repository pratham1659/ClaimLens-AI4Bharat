// frontend/src/components/analysis/AnalysisHistory.jsx
/**
 * Analysis history audit log component.
 * Displays a table of all previous analysis runs for a claim.
 */

import { format } from "date-fns";
import {
  History,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
} from "lucide-react";
import { ApprovalBadge } from "../common/Badge";

export function AnalysisHistory({ history, loading }) {
  if (loading) {
    return (
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <History className="w-5 h-5 text-gray-500" />
          <h3 className="text-lg font-semibold text-gray-900">
            Analysis History
          </h3>
        </div>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-gray-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <History className="w-5 h-5 text-gray-500" />
          <h3 className="text-lg font-semibold text-gray-900">
            Analysis History
          </h3>
        </div>
        <div className="text-center py-8">
          <Clock className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">
            No analysis history available yet.
          </p>
          <p className="text-gray-400 text-xs mt-1">
            Run an analysis to start tracking history.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-4">
        <History className="w-5 h-5 text-gray-500" />
        <h3 className="text-lg font-semibold text-gray-900">
          Analysis History
        </h3>
        <span className="ml-auto text-xs text-gray-400">
          {history.length} {history.length === 1 ? "analysis" : "analyses"}{" "}
          recorded
        </span>
      </div>

      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Timestamp
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Approval Score
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Likelihood
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Risks
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {history.map((item, index) => (
              <tr
                key={item.id || index}
                className={`hover:bg-gray-50 transition-colors ${index === 0 ? "bg-primary-50/50" : ""}`}
              >
                <td className="py-3 px-4">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-gray-900">
                      {format(new Date(item.created_at), "MMM d, yyyy")}
                    </span>
                    <span className="text-xs text-gray-500">
                      {format(new Date(item.created_at), "h:mm:ss a")}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${getScoreBarColor(item.approval_score)}`}
                        style={{ width: `${item.approval_score}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-900">
                      {Math.round(item.approval_score)}%
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <ApprovalBadge likelihood={item.approval_likelihood} />
                </td>
                <td className="py-3 px-4">
                  <span
                    className={`inline-flex items-center gap-1 text-sm ${getRiskCountColor(item.compliance_risks?.length || 0)}`}
                  >
                    {item.compliance_risks?.length > 0 && (
                      <AlertTriangle className="w-3.5 h-3.5" />
                    )}
                    {item.compliance_risks?.length || 0} risk
                    {item.compliance_risks?.length !== 1 ? "s" : ""}
                  </span>
                </td>
                <td className="py-3 px-4">
                  {getStatusBadge(item, index === 0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden space-y-3">
        {history.map((item, index) => (
          <div
            key={item.id || index}
            className={`p-4 rounded-lg border ${index === 0 ? "border-primary-200 bg-primary-50/50" : "border-gray-200 bg-gray-50"}`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex flex-col">
                <span className="text-sm font-medium text-gray-900">
                  {format(new Date(item.created_at), "MMM d, yyyy")}
                </span>
                <span className="text-xs text-gray-500">
                  {format(new Date(item.created_at), "h:mm:ss a")}
                </span>
              </div>
              {getStatusBadge(item, index === 0)}
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <p className="text-xs text-gray-500 mb-1">Score</p>
                <div className="flex items-center gap-1">
                  <span className="text-lg font-bold text-gray-900">
                    {Math.round(item.approval_score)}%
                  </span>
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Likelihood</p>
                <ApprovalBadge likelihood={item.approval_likelihood} />
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Risks</p>
                <span
                  className={`text-sm font-medium ${getRiskCountColor(item.compliance_risks?.length || 0)}`}
                >
                  {item.compliance_risks?.length || 0}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function getScoreBarColor(score) {
  if (score >= 75) return "bg-success-500";
  if (score >= 50) return "bg-warning-500";
  return "bg-danger-500";
}

function getRiskCountColor(count) {
  if (count === 0) return "text-success-600";
  if (count <= 2) return "text-warning-600";
  return "text-danger-600";
}

function getStatusBadge(item, isLatest) {
  if (item.status === "failed") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-danger-100 text-danger-700">
        <XCircle className="w-3 h-3" />
        Failed
      </span>
    );
  }

  if (isLatest) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-success-100 text-success-700">
        <CheckCircle className="w-3 h-3" />
        Latest
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
      <Clock className="w-3 h-3" />
      Historical
    </span>
  );
}
