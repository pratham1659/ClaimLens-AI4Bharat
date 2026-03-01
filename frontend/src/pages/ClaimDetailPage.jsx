// frontend/src/pages/ClaimDetailPage.jsx
/**
 * Claim detail page with analysis.
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Download,
  Play,
  RefreshCw,
  Calendar,
  User,
} from "lucide-react";
import { format } from "date-fns";
import { useClaims } from "../hooks/useClaims";
import { useDocuments } from "../hooks/useDocuments";
import { useAnalysis } from "../hooks/useAnalysis";
import { StatusBadge } from "../components/common/Badge";
import { AnalysisResult } from "../components/analysis/AnalysisResult";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { CardSkeleton } from "../components/common/Skeleton";

export function ClaimDetailPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();

  const { getClaim } = useClaims();
  const { documents, fetchDocuments, getDownloadUrl } = useDocuments();
  const {
    analysis,
    analyzing,
    loading: analysisLoading,
    analyzeClaim,
    fetchAnalysis,
  } = useAnalysis();

  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadClaimData();
  }, [claimId]);

  const loadClaimData = async () => {
    setLoading(true);
    try {
      const [claimData] = await Promise.all([
        getClaim(claimId),
        fetchDocuments(claimId),
        fetchAnalysis(claimId),
      ]);
      setClaim(claimData);
    } catch (error) {
      navigate("/claims");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (documentId) => {
    const url = await getDownloadUrl(documentId);
    window.open(url, "_blank");
  };

  const handleAnalyze = async () => {
    try {
      await analyzeClaim(claimId);
    } catch {
      // Error toast is handled in the hook
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Claim not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Claims
          </button>
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-gray-900">
              {claim.claim_number}
            </h1>
            <StatusBadge status={claim.status} />
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={analyzing || claim.status === "processing"}
          className="btn-primary"
        >
          {analyzing ? (
            <>
              <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Play className="w-5 h-5 mr-2" />
              {analysis ? "Re-analyze" : "Run Analysis"}
            </>
          )}
        </button>
      </div>

      {/* Claim Info */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Claim Information
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-gray-500 flex items-center gap-1">
              <User className="w-4 h-4" />
              Patient
            </p>
            <p className="font-medium mt-1">{claim.patient_name}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              Created
            </p>
            <p className="font-medium mt-1">
              {format(new Date(claim.created_at), "MMM d, yyyy")}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Status</p>
            <div className="mt-1">
              <StatusBadge status={claim.status} />
            </div>
          </div>
        </div>
      </div>

      {/* Documents */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Documents</h2>
        <div className="space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="font-medium text-gray-900">{doc.filename}</p>
                  <p className="text-sm text-gray-500">
                    {doc.document_type.replace("_", " ")} •{" "}
                    {(doc.file_size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={doc.status} />
                <button
                  onClick={() => handleDownload(doc.id)}
                  className="p-2 text-gray-400 hover:text-gray-600"
                >
                  // frontend/src/pages/ClaimDetailPage.jsx (continued)
                  <Download className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}

          {documents.length === 0 && (
            <p className="text-gray-500 text-center py-4">
              No documents uploaded yet
            </p>
          )}
        </div>
      </div>

      {/* Analysis Results */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Compliance Analysis
        </h2>
        {analysisLoading ? (
          <CardSkeleton />
        ) : (
          <AnalysisResult analysis={analysis} />
        )}
      </div>
    </div>
  );
}
