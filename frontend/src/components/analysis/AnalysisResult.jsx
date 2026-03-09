/**
 * Analysis result display component.
 */

import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  FileText,
  Lightbulb,
  AlertCircle,
} from "lucide-react";
import { ApprovalBadge } from "../common/Badge";

export function AnalysisResult({ analysis }) {
  if (!analysis) {
    return (
      <div className="card p-8 text-center">
        <AlertCircle className="w-12 h-12 text-gray-400 mx-auto" />
        <p className="mt-4 text-gray-600">No analysis available yet.</p>
        <p className="text-sm text-gray-500">
          Upload all required documents and run analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Score Overview */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Approval Assessment
        </h3>
        <div className="flex items-center gap-6">
          <div className="flex-1">
            <div className="flex items-center gap-4">
              <div className="relative w-24 h-24">
                <svg className="w-24 h-24 transform -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="#e5e7eb"
                    strokeWidth="8"
                    fill="none"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke={getScoreColor(analysis.approval_score)}
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={`${(analysis.approval_score / 100) * 251.2} 251.2`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold">
                    {Math.round(analysis.approval_score)}
                  </span>
                </div>
              </div>
              <div>
                <ApprovalBadge likelihood={analysis.approval_likelihood} />
                <p className="mt-2 text-sm text-gray-600">
                  Based on policy compliance analysis
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Debug Info - Right after Approval Assessment */}
      {analysis.debug_info && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Analysis Debug Info
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-gray-500 text-xs">Reasoning Mode</p>
              <p className="font-medium text-gray-900">
                {analysis.debug_info.reasoning_mode === "grounded_rules" ? "Grounded Rules" : "LLM"}
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-gray-500 text-xs">Retrieved Clauses</p>
              <p className="font-medium text-gray-900">
                {analysis.debug_info.retrieved_clause_count ?? 0}
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-gray-500 text-xs">Matched Terms</p>
              <p className="font-medium text-gray-900">
                {analysis.debug_info.matched_claim_terms ?? 0} /{" "}
                {analysis.debug_info.total_claim_terms ?? 0}
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-gray-500 text-xs">Match Ratio</p>
              <p className="font-medium text-gray-900">
                {Math.round((analysis.debug_info.match_ratio ?? 0) * 100)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Compliance Risks */}
      {analysis.compliance_risks?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-warning-500" />
            Compliance Risks
          </h3>
          <div className="space-y-3">
            {analysis.compliance_risks.map((risk, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${getSeverityStyles(risk.severity)}`}
              >
                <div className="flex items-start gap-3">
                  {getSeverityIcon(risk.severity)}
                  <div>
                    <p className="font-medium">{risk.description}</p>
                    {risk.affected_clause && (
                      <p className="text-sm text-gray-500 mt-1">
                        Clause: {risk.affected_clause}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Missing Documentation */}
      {analysis.missing_documentation?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-danger-500" />
            Missing Documentation
          </h3>
          <ul className="space-y-2">
            {analysis.missing_documentation.map((doc, index) => (
              <li key={index} className="flex items-center gap-2 text-gray-700">
                <XCircle className="w-4 h-4 text-danger-500" />
                {doc}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {analysis.recommendations?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-primary-500" />
            Recommendations
          </h3>
          <div className="space-y-3">
            {analysis.recommendations.map((rec, index) => (
              <div key={index} className="p-4 bg-primary-50 rounded-lg">
                <div className="flex items-start gap-3">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${getPriorityStyles(rec.priority)}`}
                  >
                    {rec.priority.toUpperCase()}
                  </span>
                  <div>
                    <p className="font-medium text-gray-900">{rec.action}</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {rec.rationale}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reasoning */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Analysis Reasoning
        </h3>
        <p className="text-gray-700 whitespace-pre-wrap">
          {analysis.reasoning}
        </p>
      </div>

      {/* Clause References - At the bottom */}
      {analysis.clause_references?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Referenced Policy Clauses
          </h3>
          <div className="space-y-3">
            {analysis.clause_references.map((clause, index) => (
              <div key={index} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-500">
                    Policy Clause {index + 1}
                  </span>
                  <span className="text-xs text-gray-400">
                    Relevance: {Math.round(clause.relevance_score * 100)}%
                  </span>
                </div>
                <p className="text-sm text-gray-700">{clause.clause_text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function getScoreColor(score) {
  if (score >= 75) return "#22c55e";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

function formatClauseSourceLabel(source) {
  const normalized = String(source || "")
    .trim()
    .toLowerCase();

  if (!normalized) return "Policy Clause";
  if (normalized === "embedding_fallback") return "Policy Clause Match";
  if (normalized === "policy_document") return "Policy Document";

  return String(source);
}

function getSeverityStyles(severity) {
  switch (severity) {
    case "high":
      return "bg-danger-50 border-danger-200";
    case "medium":
      return "bg-warning-50 border-warning-200";
    case "low":
      return "bg-gray-50 border-gray-200";
    default:
      return "bg-gray-50 border-gray-200";
  }
}

function getSeverityIcon(severity) {
  switch (severity) {
    case "high":
      return <XCircle className="w-5 h-5 text-danger-500 flex-shrink-0" />;
    case "medium":
      return (
        <AlertTriangle className="w-5 h-5 text-warning-500 flex-shrink-0" />
      );
    default:
      return <AlertCircle className="w-5 h-5 text-gray-500 flex-shrink-0" />;
  }
}

function getPriorityStyles(priority) {
  switch (priority) {
    case "high":
      return "bg-danger-100 text-danger-700";
    case "medium":
      return "bg-warning-100 text-warning-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}
