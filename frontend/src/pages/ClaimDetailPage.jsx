// frontend/src/pages/ClaimDetailPage.jsx


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
      <div className="min-h-[50vh] flex flex-col items-center justify-center">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm sm:text-base text-gray-500">
          Loading claim details...
        </p>
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="text-center py-8 sm:py-12">
        <p className="text-gray-600">Claim not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header - Responsive */}
      <div className="flex flex-col gap-4">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-3 sm:mb-4 touch-manipulation p-1 -ml-1"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="text-sm sm:text-base">Back to Claims</span>
          </button>
          <div className="flex flex-wrap items-center gap-2 sm:gap-4">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 break-all">
              {claim.claim_number}
            </h1>
            <StatusBadge status={claim.status} />
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={analyzing || claim.status === "processing"}
          className="btn-primary w-full sm:w-auto justify-center touch-manipulation"
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

      {/* Claim Info - Responsive */}
      <div className="card p-4 sm:p-6">
        <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4">
          Claim Information
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <div>
            <p className="text-xs sm:text-sm text-gray-500 flex items-center gap-1">
              <User className="w-4 h-4" />
              Patient
            </p>
            <p className="font-medium mt-1 text-sm sm:text-base truncate">
              {claim.patient_name}
            </p>
          </div>
          <div>
            <p className="text-xs sm:text-sm text-gray-500 flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              Created
            </p>
            <p className="font-medium mt-1 text-sm sm:text-base">
              {format(new Date(claim.created_at), "MMM d, yyyy")}
            </p>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <p className="text-xs sm:text-sm text-gray-500">Status</p>
            <div className="mt-1">
              <StatusBadge status={claim.status} />
            </div>
          </div>
        </div>
      </div>

      {/* Documents - Responsive */}
      <div className="card p-4 sm:p-6">
        <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4">
          Documents
        </h2>
        <div className="space-y-2 sm:space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3 sm:p-4 bg-gray-50 rounded-lg"
            >
              <div className="flex items-start sm:items-center gap-3 min-w-0">
                <FileText className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5 sm:mt-0" />
                <div className="min-w-0">
                  <p className="font-medium text-gray-900 text-sm sm:text-base truncate">
                    {doc.filename}
                  </p>
                  <p className="text-xs sm:text-sm text-gray-500">
                    {doc.document_type.replace("_", " ")} •{" "}
                    {(doc.file_size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 justify-end">
                <StatusBadge status={doc.status} />
                <button
                  onClick={() => handleDownload(doc.id)}
                  className="p-2 text-gray-400 hover:text-gray-600 touch-manipulation"
                  aria-label="Download document"
                >
                  <Download className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}

          {documents.length === 0 && (
            <p className="text-gray-500 text-center py-4 text-sm sm:text-base">
              No documents uploaded yet
            </p>
          )}
        </div>
      </div>

      {/* Analysis Results - Responsive */}
      <div>
        <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4">
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
