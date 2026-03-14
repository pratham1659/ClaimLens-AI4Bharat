// frontend/src/pages/ClaimDetailPage.jsx

import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Download,
  Play,
  RefreshCw,
  Calendar,
  User,
  Trash2,
  Upload,
  X,
  AlertTriangle,
  Clock,
  Check,
  XCircle,
} from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { useClaims } from "../hooks/useClaims";
import { useDocuments } from "../hooks/useDocuments";
import { useAnalysis } from "../hooks/useAnalysis";
import { StatusBadge } from "../components/common/Badge";
import { AnalysisResult } from "../components/analysis/AnalysisResult";
import { AnalysisHistory } from "../components/analysis/AnalysisHistory";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { CardSkeleton } from "../components/common/Skeleton";
import { documentsAPI } from "../services/api";

// Maximum file size: 5 MB in bytes
const MAX_FILE_SIZE = 5 * 1024 * 1024;

export function ClaimDetailPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();

  const { getClaim } = useClaims();
  const {
    documents,
    fetchDocuments,
    getDownloadUrl,
    deleteDocument,
    uploadDocument,
    uploading,
  } = useDocuments();
  const {
    analysis,
    analyzing,
    loading: analysisLoading,
    analyzeClaim,
    fetchAnalysis,
    fetchHistory,
  } = useAnalysis();

  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [missingDocWarning, setMissingDocWarning] = useState(null);
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [analysisFailed, setAnalysisFailed] = useState(false);
  const fileInputRef = useRef(null);
  const [uploadingType, setUploadingType] = useState(null);
  const [allUserPolicies, setAllUserPolicies] = useState([]);
  const [selectingPolicy, setSelectingPolicy] = useState(false);
  const pollingIntervalRef = useRef(null);

  // Get all documents by type (support multiple files of same type)
  const dischargeSummaries = documents.filter(
    (doc) => doc.document_type === "discharge_summary",
  );
  const insurancePolicies = documents.filter(
    (doc) => doc.document_type === "insurance_policy",
  );
  // Keep these for compatibility with analysis checks
  const dischargeSummary = dischargeSummaries[0];
  const insurancePolicy = insurancePolicies[0];

  useEffect(() => {
    loadClaimData();
  }, [claimId]);

  // Poll for document processing status
  const startDocumentPolling = () => {
    // Clear any existing interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const docs = await fetchDocuments(claimId);
        // Check if all documents are in terminal state (processed or failed)
        const allDone = docs.every(
          (doc) => doc.status === "processed" || doc.status === "failed",
        );
        if (allDone) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } catch (error) {
        console.error("Error polling documents:", error);
      }
    }, 3000); // Poll every 3 seconds

    // Stop polling after 5 minutes
    setTimeout(() => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }, 300000);
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Fetch all user's insurance policies for selection
  useEffect(() => {
    const fetchAllPolicies = async () => {
      try {
        const response = await documentsAPI.listUserInsurancePolicies();
        // Show all policies (don't filter out current claim)
        setAllUserPolicies(response.data || []);
      } catch (error) {
        console.error("Error fetching user policies:", error);
      }
    };
    fetchAllPolicies();
  }, [claimId, documents]);

  const loadClaimData = async () => {
    setLoading(true);
    setHistoryLoading(true);
    try {
      const [claimData, docs] = await Promise.all([
        getClaim(claimId),
        fetchDocuments(claimId),
        fetchAnalysis(claimId),
      ]);
      setClaim(claimData);

      // If there are any documents still processing, start polling
      const hasProcessingDocs = docs?.some(
        (doc) => doc.status !== "processed" && doc.status !== "failed",
      );
      if (hasProcessingDocs) {
        startDocumentPolling();
      }

      // Fetch analysis history
      try {
        const history = await fetchHistory(claimId);
        setAnalysisHistory(history || []);
      } catch {
        // History fetch error is non-critical
        setAnalysisHistory([]);
      }
    } catch (error) {
      navigate("/claims");
    } finally {
      setLoading(false);
      setHistoryLoading(false);
    }
  };

  const handleDownload = async (documentId) => {
    const url = await getDownloadUrl(documentId);
    window.open(url, "_blank");
  };

  const handleAnalyze = async () => {
    // Check for missing documents
    const missingDocs = [];
    if (!dischargeSummary) missingDocs.push("Discharge Summary");
    if (!insurancePolicy) missingDocs.push("Insurance Policy");

    if (missingDocs.length > 0) {
      setMissingDocWarning(missingDocs);
      return;
    }

    setShowAnalysisModal(true);
    setAnalysisProgress(0);
    setAnalysisFailed(false);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setAnalysisProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + Math.random() * 15;
      });
    }, 500);

    try {
      await analyzeClaim(claimId);
      setAnalysisProgress(100);
      setAnalysisFailed(false);

      // Refresh claim data to get updated status
      const updatedClaim = await getClaim(claimId);
      setClaim(updatedClaim);

      // Refresh analysis history after successful analysis
      try {
        const history = await fetchHistory(claimId);
        setAnalysisHistory(history || []);
      } catch {}

      setTimeout(() => {
        setShowAnalysisModal(false);
        setAnalysisProgress(0);
      }, 500);
    } catch {
      // Error toast is handled in the hook
      // Mark analysis as failed
      setAnalysisFailed(true);

      // Also refresh claim to get failed status
      try {
        const updatedClaim = await getClaim(claimId);
        setClaim(updatedClaim);
      } catch {}

      // Refresh history even on failure (may contain partial/failed records)
      try {
        const history = await fetchHistory(claimId);
        setAnalysisHistory(history || []);
      } catch {}

      setShowAnalysisModal(false);
    } finally {
      clearInterval(progressInterval);
    }
  };

  const handleDeleteDocument = async (docId) => {
    try {
      await deleteDocument(docId);
      setDeleteConfirm(null);
      // Refresh documents list
      await fetchDocuments(claimId);
    } catch {
      // Error handled in hook
    }
  };

  const handleUploadClick = (documentType) => {
    setUploadingType(documentType);
    fileInputRef.current?.click();
  };

  const handleSelectPolicy = async (policy) => {
    setSelectingPolicy(true);
    try {
      toast.loading("Replacing existing policy...", { id: "replace-policy" });

      // Fetch fresh documents list to ensure we have current state
      const currentDocs = await fetchDocuments(claimId);
      const currentPolicies = currentDocs.filter(
        (doc) => doc.document_type === "insurance_policy",
      );

      // Check for duplicate - if file with same name already exists in this claim
      const existingPolicyWithSameName = currentPolicies.find(
        (doc) => doc.filename.toLowerCase() === policy.filename.toLowerCase(),
      );
      if (existingPolicyWithSameName) {
        toast.error(`"${policy.filename}" already exists in this claim.`, {
          id: "replace-policy",
        });
        setSelectingPolicy(false);
        return;
      }

      // Delete ALL existing insurance policies first (only one allowed per claim)
      for (const existingPolicy of currentPolicies) {
        console.log(
          "Deleting existing policy:",
          existingPolicy.id,
          existingPolicy.filename,
        );
        await deleteDocument(existingPolicy.id);
      }

      // Use copy API to copy the already-processed document without re-processing
      // This preserves the processed status and embeddings
      console.log("Copying policy:", policy.id, "to claim:", claimId);
      await documentsAPI.copyToClaim(policy.id, claimId);

      // Fetch documents again to update the UI
      await fetchDocuments(claimId);

      // Refresh user policies list
      try {
        const response = await documentsAPI.listUserInsurancePolicies();
        setAllUserPolicies(response.data || []);
      } catch {}

      // No need to poll - document is already processed
      toast.success(`Selected: ${policy.filename}`, { id: "replace-policy" });
    } catch (error) {
      console.error("Error selecting policy:", error);
      toast.error("Failed to select policy. Please try again.", {
        id: "replace-policy",
      });
    } finally {
      setSelectingPolicy(false);
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !uploadingType) return;

    // Check file size limit (5 MB)
    if (file.size > MAX_FILE_SIZE) {
      toast.error("File is too large. Maximum size is 5 MB.");
      setUploadingType(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    try {
      // For insurance_policy uploads, we need special handling
      if (uploadingType === "insurance_policy") {
        toast.loading("Processing insurance policy...", {
          id: "upload-replace",
        });

        // Fetch fresh documents list to ensure we have current state
        const currentDocs = await fetchDocuments(claimId);
        const currentPolicies = currentDocs.filter(
          (doc) => doc.document_type === "insurance_policy",
        );

        // Check for duplicate filename
        const existingPolicy = currentPolicies.find(
          (doc) => doc.filename.toLowerCase() === file.name.toLowerCase(),
        );
        if (existingPolicy) {
          toast.error(`"${file.name}" already exists in this claim.`, {
            id: "upload-replace",
          });
          setUploadingType(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = "";
          }
          return;
        }

        // Delete ALL existing insurance policies (only one allowed per claim)
        for (const policy of currentPolicies) {
          console.log(
            "Deleting existing policy before upload:",
            policy.id,
            policy.filename,
          );
          await deleteDocument(policy.id);
        }
        toast.dismiss("upload-replace");
      }

      await uploadDocument(claimId, file, uploadingType);
      await fetchDocuments(claimId);

      // Refresh user policies list if we uploaded an insurance policy
      if (uploadingType === "insurance_policy") {
        try {
          const response = await documentsAPI.listUserInsurancePolicies();
          setAllUserPolicies(response.data || []);
        } catch {}
      }

      // Start polling to detect when document processing completes
      startDocumentPolling();
    } catch {
      // Error handled in hook
    } finally {
      setUploadingType(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
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
      <div>
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-3 sm:mb-4 touch-manipulation p-1 -ml-1"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="text-sm sm:text-base">Back to Claims</span>
        </button>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 break-all">
              {claim.claim_number}
            </h1>
            <StatusBadge status={claim.status} />
          </div>

          <button
            onClick={handleAnalyze}
            disabled={analyzing || claim.status === "processing"}
            className={`inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-all touch-manipulation ${
              analyzing
                ? "bg-primary-100 text-primary-700 cursor-wait"
                : "bg-primary-600 text-white hover:bg-primary-700 shadow-sm hover:shadow"
            } disabled:opacity-60 disabled:cursor-not-allowed`}
          >
            {analyzing ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                <span className="hidden sm:inline">Analyzing...</span>
                <span className="sm:hidden">...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-1.5" />
                {analysis ? "Re-analyze" : "Analyze"}
              </>
            )}
          </button>
        </div>
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
      <div className="card p-4 sm:p-6 relative">
        <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-4">
          Documents
        </h2>

        {/* Hidden file input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
          className="hidden"
        />

        {/* Upload Loader Overlay */}
        {uploading && (
          <div className="absolute inset-4 sm:inset-6 bg-white/80 backdrop-blur-sm rounded-lg flex items-center justify-center z-50">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="mt-4 text-sm font-medium text-gray-900">
                Uploading document...
              </p>
              <p className="mt-1 text-xs text-gray-600">
                Please wait while we process your file
              </p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {/* Discharge Summary Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-700">
                Discharge Summary
              </h3>
              <button
                onClick={() => handleUploadClick("discharge_summary")}
                disabled={uploading}
                className="text-xs px-2 py-1 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors disabled:opacity-50"
              >
                <Upload className="w-3 h-3 inline mr-1" />
                {"Upload New"}
              </button>
            </div>
            {dischargeSummaries.length > 0 ? (
              <div className="space-y-2">
                {dischargeSummaries.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <FileText className="w-5 h-5 text-blue-500 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900 text-sm truncate">
                          {doc.filename}
                        </p>
                        <p className="text-xs text-gray-500">
                          {(doc.file_size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 justify-end">
                      {doc.status !== "processed" ? (
                        <>
                          <div className="flex items-center gap-1 text-primary-600">
                            <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
                            <span className="text-xs font-medium">
                              Processing...
                            </span>
                          </div>
                        </>
                      ) : (
                        <>
                          <StatusBadge status={doc.status} />
                          <button
                            onClick={() => handleDownload(doc.id)}
                            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg touch-manipulation transition-colors"
                            title="Download"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(doc)}
                            className="p-1.5 text-white bg-danger-500 hover:bg-danger-700 rounded-lg touch-manipulation transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 border-2 border-dashed border-gray-200 rounded-lg text-center">
                <FileText className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">
                  No discharge summary uploaded
                </p>
              </div>
            )}
          </div>

          {/* Insurance Policy Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-700">
                Insurance Policy
              </h3>
              <button
                onClick={() => handleUploadClick("insurance_policy")}
                disabled={uploading}
                className="text-xs px-2 py-1 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors disabled:opacity-50"
              >
                <Upload className="w-3 h-3 inline mr-1" />
                {"Upload New"}
              </button>
            </div>
            {insurancePolicies.length > 0 ? (
              <div className="space-y-2">
                {insurancePolicies.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <FileText className="w-5 h-5 text-green-500 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900 text-sm truncate">
                          {doc.filename}
                        </p>
                        <p className="text-xs text-gray-500">
                          {(doc.file_size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 justify-end">
                      {doc.status !== "processed" ? (
                        <>
                          <div className="flex items-center gap-1 text-primary-600">
                            <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
                            <span className="text-xs font-medium">
                              Processing...
                            </span>
                          </div>
                        </>
                      ) : (
                        <>
                          <StatusBadge status={doc.status} />
                          <button
                            onClick={() => handleDownload(doc.id)}
                            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg touch-manipulation transition-colors"
                            title="Download"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(doc)}
                            className="p-1.5 text-white bg-danger-500 hover:bg-danger-700 rounded-lg touch-manipulation transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 border-2 border-dashed border-gray-200 rounded-lg text-center">
                <FileText className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">
                  No insurance policy uploaded
                </p>
              </div>
            )}

            {/* Previously Uploaded Insurance Policies */}
            {(() => {
              // Deduplicate policies by filename, prioritizing current claim's documents
              const uniquePolicies = [];
              const seenFilenames = new Set();
              // Sort to put current claim's documents first
              const sortedPolicies = [...allUserPolicies].sort((a, b) => {
                if (a.claim_id === claimId && b.claim_id !== claimId) return -1;
                if (b.claim_id === claimId && a.claim_id !== claimId) return 1;
                return new Date(b.created_at) - new Date(a.created_at);
              });
              for (const policy of sortedPolicies) {
                const lowerFilename = policy.filename.toLowerCase();
                if (!seenFilenames.has(lowerFilename)) {
                  seenFilenames.add(lowerFilename);
                  uniquePolicies.push(policy);
                }
              }
              return (
                uniquePolicies.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-semibold text-gray-600 mb-2 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      Select from Previously Uploaded Policies
                    </h4>
                    <div className="bg-gray-50 rounded-lg border border-gray-200 divide-y divide-gray-200 max-h-48 overflow-y-auto">
                      {uniquePolicies.map((policy) => {
                        const isCurrentlySelected = policy.claim_id === claimId;
                        return (
                          <div
                            key={policy.id}
                            className={`flex items-center justify-between p-2.5 transition-colors ${
                              isCurrentlySelected
                                ? "bg-primary-50 border-l-4 border-l-primary-500"
                                : "hover:bg-gray-100"
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <FileText className="w-4 h-4 text-green-500 flex-shrink-0" />
                              <div className="min-w-0 flex-1">
                                <p className="font-medium text-gray-900 text-xs truncate">
                                  {policy.filename}
                                  {isCurrentlySelected && (
                                    <span className="ml-2 text-primary-600 font-semibold">
                                      (Selected)
                                    </span>
                                  )}
                                </p>
                                <p className="text-xs text-gray-400 flex items-center gap-1">
                                  {policy.status === "processed" && (
                                    <Check className="w-3 h-3 text-success-500" />
                                  )}
                                  {format(
                                    new Date(policy.created_at),
                                    "MMM d, yyyy",
                                  )}
                                </p>
                              </div>
                            </div>
                            {!isCurrentlySelected && (
                              <button
                                onClick={() => handleSelectPolicy(policy)}
                                disabled={selectingPolicy || uploading}
                                className="px-2.5 py-1 text-xs font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-lg transition-colors touch-manipulation disabled:opacity-50"
                              >
                                {selectingPolicy ? "..." : "Use This"}
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    <p className="text-xs text-gray-400 mt-1.5">
                      Only one insurance policy can be used per claim
                    </p>
                  </div>
                )
              );
            })()}
          </div>
        </div>
      </div>

      {/* Analysis Results - Responsive */}
      <div>
        <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4">
          Compliance Analysis
        </h2>

        {/* Analysis Failed Status Banner */}
        {analysisFailed && !analysis && (
          <div className="mb-4 p-4 bg-danger-50 border border-danger-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-danger-100 rounded-full flex items-center justify-center flex-shrink-0">
                <XCircle className="w-5 h-5 text-danger-600" />
              </div>
              <div>
                <h4 className="font-medium text-danger-800">Analysis Failed</h4>
                <p className="text-sm text-danger-600">
                  The analysis could not be completed. Please check your
                  documents and try again.
                </p>
              </div>
            </div>
          </div>
        )}

        {analysisLoading ? (
          <CardSkeleton />
        ) : (
          <AnalysisResult analysis={analysis} />
        )}
      </div>

      {/* Analysis History - Audit Log */}
      <div>
        <AnalysisHistory history={analysisHistory} loading={historyLoading} />
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Delete Document
              </h3>
              <button
                onClick={() => setDeleteConfirm(null)}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete{" "}
              <span className="font-medium">{deleteConfirm.filename}</span>?
              This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteDocument(deleteConfirm.id)}
                className="flex-1 px-4 py-2 bg-danger-500 text-white rounded-lg hover:bg-danger-700 transition-colors font-medium"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Analysis Progress Modal */}
      {showAnalysisModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <RefreshCw className="w-8 h-8 text-primary-600 animate-spin" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Analyzing Claim
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Processing documents and generating compliance analysis...
              </p>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                <div
                  className="bg-primary-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(analysisProgress, 100)}%` }}
                />
              </div>
              <p className="text-sm font-medium text-primary-600">
                {Math.round(analysisProgress)}% complete
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Missing Document Warning Modal */}
      {missingDocWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
            <div className="text-center">
              <div className="w-14 h-14 bg-warning-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="w-7 h-7 text-warning-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Missing Documents
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                The following required documents are missing:
              </p>
              <ul className="mb-6 space-y-2">
                {missingDocWarning.map((doc) => (
                  <li
                    key={doc}
                    className="flex items-center justify-center gap-2 text-sm text-danger-600"
                  >
                    <X className="w-4 h-4" />
                    {doc}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-gray-500 mb-4">
                Please upload all required documents before running analysis.
              </p>
              <button
                onClick={() => setMissingDocWarning(null)}
                className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
