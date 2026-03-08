// frontend/src/pages/NewClaimPage.jsx

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  FileText,
  Trash2,
  X,
  Clock,
} from "lucide-react";
import { format } from "date-fns";
import { useClaims } from "../hooks/useClaims";
import { useDocuments } from "../hooks/useDocuments";
import { DocumentUploader } from "../components/claims/DocumentUploader";
import { documentsAPI } from "../services/api";
import toast from "react-hot-toast";

const steps = [
  { id: 1, name: "Details", fullName: "Claim Details" },
  { id: 2, name: "Upload", fullName: "Upload Documents" },
  { id: 3, name: "Review", fullName: "Review & Submit" },
];

export function NewClaimPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [claimData, setClaimData] = useState({
    patient_name: "",
    metadata: {},
  });
  const [createdClaim, setCreatedClaim] = useState(null);
  const [uploadedDocs, setUploadedDocs] = useState({
    discharge_summary: null,
    insurance_policy: null,
  });
  const [previousPolicies, setPreviousPolicies] = useState([]);
  const [loadingPolicies, setLoadingPolicies] = useState(false);
  const [deleteConfirmDoc, setDeleteConfirmDoc] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const pollingIntervalsRef = useRef({});

  const navigate = useNavigate();
  const { createClaim } = useClaims();
  const {
    uploadDocument,
    uploadProgress,
    uploading,
    fetchDocuments,
    deleteDocument,
  } = useDocuments();

  const handleCreateClaim = async () => {
    try {
      const claim = await createClaim(claimData);
      setCreatedClaim(claim);
      setCurrentStep(2);
    } catch (error) {
      // Error handled in hook
    }
  };

  const handleUpload = async (file, documentType) => {
    if (!createdClaim) {
      console.log("handleUpload: No created claim, returning");
      return;
    }

    console.log("handleUpload called:", { fileName: file.name, documentType });

    // Check for duplicate insurance policy files
    if (documentType === "insurance_policy") {
      // Always fetch fresh list before checking for duplicates
      let currentPolicies = [];
      try {
        const response = await documentsAPI.listUserInsurancePolicies();
        // response.data is directly the array of documents (API uses List[DocumentResponse])
        currentPolicies = Array.isArray(response.data) ? response.data : [];
        console.log(
          "Duplicate check - existing policies:",
          currentPolicies.map((p) => p.filename),
        );
        console.log("Duplicate check - uploading file:", file.name);
        setPreviousPolicies(currentPolicies);
      } catch (err) {
        console.error("Failed to fetch policies for duplicate check:", err);
        // Use state list if API fails
        currentPolicies = Array.isArray(previousPolicies)
          ? previousPolicies
          : [];
      }

      // Find duplicate by filename (case-insensitive)
      const uploadFileName = (file.name || "").toLowerCase().trim();
      const existingPolicy = currentPolicies.find((doc) => {
        const existingFileName = (doc.filename || "").toLowerCase().trim();
        const isMatch = existingFileName === uploadFileName;
        console.log(
          `Comparing: "${existingFileName}" vs "${uploadFileName}" = ${isMatch}`,
        );
        return isMatch;
      });

      console.log(
        "Duplicate check - found existing:",
        existingPolicy ? existingPolicy.filename : "none",
      );

      if (existingPolicy) {
        // BLOCK THE UPLOAD - file already exists!
        toast.error(
          `"${file.name}" is already uploaded. Please select it from the list below instead.`,
        );

        // Delete any currently selected policy first (only one policy per claim)
        const currentDocId = uploadedDocs.insurance_policy?.documentId;
        if (currentDocId && currentDocId !== existingPolicy.id) {
          try {
            await deleteDocument(currentDocId);
          } catch (err) {
            console.error("Failed to delete old policy:", err);
          }
        }

        // Auto-select the existing file
        if (existingPolicy.claim_id === createdClaim.id) {
          // Already in this claim, just select it
          setUploadedDocs((prev) => ({
            ...prev,
            insurance_policy: {
              filename: existingPolicy.filename,
              status: existingPolicy.status,
              documentId: existingPolicy.id,
            },
          }));
        } else {
          // From another claim, copy it
          try {
            const copyResponse = await documentsAPI.copyToClaim(
              existingPolicy.id,
              createdClaim.id,
            );
            const copiedDoc = copyResponse.data?.data || copyResponse.data;
            setUploadedDocs((prev) => ({
              ...prev,
              insurance_policy: {
                filename: copiedDoc.filename,
                status: copiedDoc.status,
                documentId: copiedDoc.id,
              },
            }));
            // Refresh policies list
            const policiesResponse =
              await documentsAPI.listUserInsurancePolicies();
            setPreviousPolicies(policiesResponse.data || []);
          } catch (copyError) {
            console.error("Failed to copy existing policy:", copyError);
          }
        }
        toast.success(`Selected existing file: ${existingPolicy.filename}`);
        return;
      }

      // If uploading a NEW insurance policy file, delete ALL existing policies first
      try {
        toast.loading("Replacing existing policy...", { id: "replace-policy" });
        const currentClaimDocs = await fetchDocuments(createdClaim.id);
        const existingPolicies = currentClaimDocs.filter(
          (d) => d.document_type === "insurance_policy",
        );
        for (const oldPolicy of existingPolicies) {
          console.log(
            "Deleting old policy before upload:",
            oldPolicy.id,
            oldPolicy.filename,
          );
          await deleteDocument(oldPolicy.id);
        }
        toast.dismiss("replace-policy");
      } catch (err) {
        console.error("Failed to delete old policies:", err);
        toast.dismiss("replace-policy");
      }
    }

    try {
      const documentId = await uploadDocument(
        createdClaim.id,
        file,
        documentType,
      );
      // Store document with initial status (uploading, then processing, then processed)
      setUploadedDocs((prev) => ({
        ...prev,
        [documentType]: {
          filename: file.name,
          status: "uploaded", // Initial status while processing
          documentId,
        },
      }));
      // Start polling for processing completion
      pollDocumentStatus(documentType, documentId);

      // Refresh previous policies list after successful upload for insurance_policy
      if (documentType === "insurance_policy") {
        setTimeout(async () => {
          try {
            const response = await documentsAPI.listUserInsurancePolicies();
            setPreviousPolicies(response.data || []);
          } catch (error) {
            // Silently fail - list will refresh on next step change
          }
        }, 1000);
      }
    } catch (error) {
      // Error handled in hook
    }
  };

  const pollDocumentStatus = (documentType, documentId) => {
    if (!documentId) return;

    const existingInterval = pollingIntervalsRef.current[documentType];
    if (existingInterval) {
      clearInterval(existingInterval);
    }

    let nonOkCount = 0;

    const pollInterval = setInterval(async () => {
      try {
        const token = localStorage.getItem("access_token");
        const response = await fetch(
          `${process.env.REACT_APP_API_URL || "/api/v1"}/documents/${documentId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );

        if (response.ok) {
          nonOkCount = 0;
          const docs = await response.json();
          const newStatus = docs.data?.status || docs.status;

          setUploadedDocs((prev) => ({
            ...prev,
            [documentType]: {
              ...prev[documentType],
              status: newStatus,
            },
          }));

          // Stop polling on terminal statuses
          if (newStatus === "processed" || newStatus === "failed") {
            clearInterval(pollInterval);
            delete pollingIntervalsRef.current[documentType];
          }
        } else {
          nonOkCount += 1;
          if (nonOkCount >= 5) {
            clearInterval(pollInterval);
            delete pollingIntervalsRef.current[documentType];
          }
        }
      } catch (error) {
        console.error("Error polling document status:", error);
      }
    }, 2000); // Poll every 2 seconds

    pollingIntervalsRef.current[documentType] = pollInterval;

    // Stop polling after 5 minutes
    setTimeout(() => {
      clearInterval(pollInterval);
      if (pollingIntervalsRef.current[documentType] === pollInterval) {
        delete pollingIntervalsRef.current[documentType];
      }
    }, 300000);
  };

  useEffect(() => {
    return () => {
      Object.values(pollingIntervalsRef.current).forEach((intervalId) => {
        clearInterval(intervalId);
      });
      pollingIntervalsRef.current = {};
    };
  }, []);

  // Fetch all previously uploaded insurance policy documents from all user's claims when on step 2
  useEffect(() => {
    const loadPreviousPolicies = async () => {
      if (currentStep === 2) {
        setLoadingPolicies(true);
        try {
          // Fetch all insurance policies from all user's claims
          const response = await documentsAPI.listUserInsurancePolicies();
          setPreviousPolicies(response.data || []);
        } catch (error) {
          console.error("Error fetching previous policies:", error);
          // Fallback to current claim documents if the new endpoint fails
          if (createdClaim) {
            try {
              const docs = await fetchDocuments(createdClaim.id);
              const policies = docs.filter(
                (doc) => doc.document_type === "insurance_policy",
              );
              setPreviousPolicies(policies);
            } catch {
              // Silently fail
            }
          }
        } finally {
          setLoadingPolicies(false);
        }
      }
    };
    loadPreviousPolicies();
  }, [currentStep, createdClaim, fetchDocuments]);

  const handleDeletePreviousPolicy = async () => {
    if (!deleteConfirmDoc) return;

    setIsDeleting(true);
    try {
      await deleteDocument(deleteConfirmDoc.id);
      setPreviousPolicies((prev) =>
        prev.filter((doc) => doc.id !== deleteConfirmDoc.id),
      );
      setDeleteConfirmDoc(null);
    } catch (error) {
      // Error handled in hook
    } finally {
      setIsDeleting(false);
    }
  };

  // Handle removing document selection (clears selection only, does NOT delete from S3)
  const handleClearDocumentSelection = (documentType) => {
    // For insurance_policy, just clear the selection so user can select another
    // The document remains in S3 and in the "Previously Uploaded" list
    setUploadedDocs((prev) => ({
      ...prev,
      [documentType]: null,
    }));
    toast.success("Document selection cleared");
  };

  // Handle actual deletion from S3 (used for discharge_summary or permanent delete)
  const handleDeleteDocument = async (documentType) => {
    const doc = uploadedDocs[documentType];

    // If document has been uploaded to S3, delete it from S3 as well
    if (doc?.documentId) {
      try {
        await deleteDocument(doc.documentId);

        // Refresh previous policies list if insurance_policy was deleted
        if (documentType === "insurance_policy") {
          try {
            const response = await documentsAPI.listUserInsurancePolicies();
            setPreviousPolicies(response.data || []);
          } catch {
            // Silently fail
          }
        }

        toast.success("Document removed from storage");
      } catch (error) {
        // Error handled in hook, but still clear local state
        console.error("Error deleting document from S3:", error);
      }
    } else {
      toast.success("Document removed");
    }

    // Clear local state regardless of S3 deletion result
    setUploadedDocs((prev) => ({
      ...prev,
      [documentType]: null,
    }));
  };

  const handleSubmit = () => {
    if (!uploadedDocs.discharge_summary || !uploadedDocs.insurance_policy) {
      toast.error("Please upload required documents");
      return;
    }
    navigate(`/claims/${createdClaim.id}`);
  };

  const renderDocumentStatus = (doc, requiredLabel) => {
    if (!doc) {
      return (
        <p className="text-xs text-gray-500">{requiredLabel}: Not uploaded</p>
      );
    }

    const status = String(doc.status || "uploaded").toLowerCase();
    if (status === "processed") {
      return (
        <p className="text-xs text-success-700 font-medium">
          {requiredLabel}: Processed
        </p>
      );
    }

    if (status === "failed") {
      return (
        <p className="text-xs text-danger-700 font-medium">
          {requiredLabel}: Processing failed — retry upload
        </p>
      );
    }

    return (
      <p className="text-xs text-primary-700 font-medium">
        {requiredLabel}: Processing...
      </p>
    );
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header - Responsive */}
      <div className="mb-6 sm:mb-8">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-3 sm:mb-4 touch-manipulation p-1 -ml-1"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="text-sm sm:text-base">Back</span>
        </button>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
          Create New Claim
        </h1>
      </div>

      {/* Progress Steps - Responsive */}
      <div className="mb-6 sm:mb-8">
        {/* Desktop Steps */}
        <div className="hidden sm:flex items-center justify-between">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors ${
                  currentStep > step.id
                    ? "bg-primary-600 border-primary-600"
                    : currentStep === step.id
                      ? "border-primary-600 text-primary-600"
                      : "border-gray-300 text-gray-400"
                }`}
              >
                {currentStep > step.id ? (
                  <Check className="w-5 h-5 text-white" />
                ) : (
                  <span className="font-medium">{step.id}</span>
                )}
              </div>
              <span
                className={`ml-3 font-medium ${
                  currentStep >= step.id ? "text-gray-900" : "text-gray-400"
                }`}
              >
                {step.fullName}
              </span>
              {index < steps.length - 1 && (
                <div
                  className={`w-16 lg:w-24 h-0.5 mx-4 transition-colors ${
                    currentStep > step.id ? "bg-primary-600" : "bg-gray-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Mobile Steps - Compact */}
        <div className="sm:hidden">
          <div className="flex items-center justify-between mb-2">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center flex-1">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors ${
                    currentStep > step.id
                      ? "bg-primary-600 border-primary-600"
                      : currentStep === step.id
                        ? "border-primary-600 text-primary-600"
                        : "border-gray-300 text-gray-400"
                  }`}
                >
                  {currentStep > step.id ? (
                    <Check className="w-4 h-4 text-white" />
                  ) : (
                    <span className="text-sm font-medium">{step.id}</span>
                  )}
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-2 transition-colors ${
                      currentStep > step.id ? "bg-primary-600" : "bg-gray-200"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <p className="text-center text-sm font-medium text-gray-900">
            Step {currentStep}: {steps[currentStep - 1].fullName}
          </p>
        </div>
      </div>

      {/* Step Content - Responsive */}
      <div className="card p-4 sm:p-6 lg:p-8">
        {currentStep === 1 && (
          <div className="space-y-4 sm:space-y-6">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900">
              Claim Information
            </h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5 sm:mb-2">
                Patient Name *
              </label>
              <input
                type="text"
                value={claimData.patient_name}
                onChange={(e) =>
                  setClaimData({ ...claimData, patient_name: e.target.value })
                }
                className="input"
                placeholder="Enter patient's full name"
                required
              />
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={handleCreateClaim}
                disabled={!claimData.patient_name}
                className="btn-primary w-full sm:w-auto justify-center touch-manipulation"
              >
                Continue
                <ArrowRight className="w-5 h-5 ml-2" />
              </button>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-4 sm:space-y-6">
            <div>
              <h2 className="text-base sm:text-lg font-semibold text-gray-900">
                Upload Documents
              </h2>
              <p className="text-sm sm:text-base text-gray-600 mt-1">
                Upload the required documents for compliance analysis.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:gap-4">
              <DocumentUploader
                documentType="discharge_summary"
                onUpload={handleUpload}
                uploadProgress={uploadProgress["discharge_summary"]}
                uploadedFile={uploadedDocs.discharge_summary}
                disabled={uploading}
                onDelete={() => handleDeleteDocument("discharge_summary")}
              />
              {renderDocumentStatus(
                uploadedDocs.discharge_summary,
                "Discharge Summary",
              )}
              <DocumentUploader
                documentType="insurance_policy"
                onUpload={handleUpload}
                uploadProgress={uploadProgress["insurance_policy"]}
                uploadedFile={uploadedDocs.insurance_policy}
                disabled={uploading}
                onDelete={() =>
                  handleClearDocumentSelection("insurance_policy")
                }
              />
              {renderDocumentStatus(
                uploadedDocs.insurance_policy,
                "Insurance Policy",
              )}
            </div>

            {/* Previously Uploaded Insurance Policies Section */}
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-500" />
                Previously Uploaded Insurance Policies
              </h3>
              {(() => {
                // Deduplicate policies by filename, prioritizing current claim's documents
                const uniquePolicies = [];
                const seenFilenames = new Set();
                // Sort to put current claim's documents first
                const sortedPolicies = [...previousPolicies].sort((a, b) => {
                  if (
                    a.claim_id === createdClaim?.id &&
                    b.claim_id !== createdClaim?.id
                  )
                    return -1;
                  if (
                    b.claim_id === createdClaim?.id &&
                    a.claim_id !== createdClaim?.id
                  )
                    return 1;
                  return new Date(b.created_at) - new Date(a.created_at);
                });
                for (const policy of sortedPolicies) {
                  const lowerFilename = policy.filename.toLowerCase();
                  if (!seenFilenames.has(lowerFilename)) {
                    seenFilenames.add(lowerFilename);
                    uniquePolicies.push(policy);
                  }
                }
                return uniquePolicies.length > 0 ? (
                  <>
                    <div className="bg-gray-50 rounded-lg border border-gray-200 divide-y divide-gray-200">
                      {uniquePolicies.map((doc) => {
                        const isSelected =
                          uploadedDocs.insurance_policy?.documentId === doc.id;
                        return (
                          <div
                            key={doc.id}
                            className={`flex items-center justify-between p-3 hover:bg-gray-100 transition-colors ${
                              isSelected
                                ? "bg-primary-50 border-l-4 border-l-primary-500"
                                : ""
                            }`}
                          >
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <FileText className="w-5 h-5 text-green-500 flex-shrink-0" />
                              <div className="min-w-0 flex-1">
                                <p className="font-medium text-gray-900 text-sm truncate">
                                  {doc.filename}
                                  {isSelected && (
                                    <span className="ml-2 text-xs text-primary-600 font-semibold">
                                      (Selected)
                                    </span>
                                  )}
                                </p>
                                <p className="text-xs text-gray-500 flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  {format(
                                    new Date(doc.created_at),
                                    "MMM d, yyyy 'at' h:mm a",
                                  )}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 ml-2">
                              {!isSelected && (
                                <button
                                  onClick={async () => {
                                    try {
                                      toast.loading(
                                        `Selecting ${doc.filename}...`,
                                        { id: "select-policy" },
                                      );

                                      // Fetch ALL insurance policies for this claim
                                      const currentClaimDocs =
                                        await fetchDocuments(createdClaim.id);
                                      const existingPolicies =
                                        currentClaimDocs.filter(
                                          (d) =>
                                            d.document_type ===
                                              "insurance_policy" &&
                                            d.id !== doc.id,
                                        );

                                      // Delete ALL existing insurance policies for this claim
                                      for (const oldPolicy of existingPolicies) {
                                        console.log(
                                          "Deleting old policy:",
                                          oldPolicy.id,
                                          oldPolicy.filename,
                                        );
                                        try {
                                          await deleteDocument(oldPolicy.id);
                                        } catch (err) {
                                          console.error(
                                            "Failed to delete old policy:",
                                            err,
                                          );
                                        }
                                      }

                                      // Check if this document is from the current claim or another claim
                                      if (doc.claim_id === createdClaim?.id) {
                                        // Document already belongs to this claim, just select it
                                        setUploadedDocs((prev) => ({
                                          ...prev,
                                          insurance_policy: {
                                            filename: doc.filename,
                                            status: doc.status,
                                            documentId: doc.id,
                                          },
                                        }));
                                      } else {
                                        // Document from another claim - copy it
                                        const copyResponse =
                                          await documentsAPI.copyToClaim(
                                            doc.id,
                                            createdClaim.id,
                                          );
                                        const copiedDoc =
                                          copyResponse.data?.data ||
                                          copyResponse.data;
                                        setUploadedDocs((prev) => ({
                                          ...prev,
                                          insurance_policy: {
                                            filename: copiedDoc.filename,
                                            status: copiedDoc.status,
                                            documentId: copiedDoc.id,
                                          },
                                        }));
                                      }

                                      // Refresh the policies list
                                      const policiesResponse =
                                        await documentsAPI.listUserInsurancePolicies();
                                      setPreviousPolicies(
                                        policiesResponse.data || [],
                                      );

                                      toast.success(
                                        `Selected: ${doc.filename}`,
                                        { id: "select-policy" },
                                      );
                                    } catch (error) {
                                      console.error(
                                        "Error selecting policy:",
                                        error,
                                      );
                                      toast.error(
                                        "Failed to select policy. Please try again.",
                                        { id: "select-policy" },
                                      );
                                    }
                                  }}
                                  disabled={uploading}
                                  className="px-3 py-1.5 text-xs font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-lg transition-colors touch-manipulation disabled:opacity-50"
                                >
                                  Select
                                </button>
                              )}
                              <button
                                onClick={() => setDeleteConfirmDoc(doc)}
                                className="p-1.5 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded-lg transition-colors touch-manipulation"
                                title="Delete this document"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Select a previously uploaded file or upload a new one.
                      Deleting will permanently remove files from storage.
                    </p>
                  </>
                ) : (
                  <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 text-center">
                    <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                    <p className="text-sm text-gray-500">
                      No insurance policies uploaded yet
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Upload an insurance policy document above to see it here
                    </p>
                  </div>
                );
              })()}
            </div>

            <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-3 pt-2">
              <button
                onClick={() => setCurrentStep(1)}
                className="btn-secondary w-full sm:w-auto justify-center touch-manipulation"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Back
              </button>
              <button
                onClick={() => setCurrentStep(3)}
                disabled={
                  !uploadedDocs.discharge_summary ||
                  !uploadedDocs.insurance_policy
                }
                className="btn-primary w-full sm:w-auto justify-center touch-manipulation"
              >
                Continue
                <ArrowRight className="w-5 h-5 ml-2" />
              </button>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-4 sm:space-y-6">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900">
              Review & Submit
            </h2>

            <div className="bg-gray-50 rounded-lg p-4 sm:p-6 space-y-3 sm:space-y-4">
              <div>
                <p className="text-xs sm:text-sm text-gray-500">Claim Number</p>
                <p className="font-medium text-sm sm:text-base">
                  {createdClaim?.claim_number}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500">Patient Name</p>
                <p className="font-medium text-sm sm:text-base">
                  {claimData.patient_name}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500">
                  Discharge Summary
                </p>
                {uploadedDocs.discharge_summary && (
                  <div className="mt-1 flex items-center gap-2">
                    <Check className="w-4 h-4 text-success-500 flex-shrink-0" />
                    <span className="text-sm font-medium truncate">
                      {uploadedDocs.discharge_summary.filename}
                    </span>
                  </div>
                )}
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500">
                  Insurance Policy
                </p>
                {uploadedDocs.insurance_policy ? (
                  <div className="mt-1 flex items-center gap-2">
                    <Check className="w-4 h-4 text-success-500 flex-shrink-0" />
                    <span className="text-sm font-medium truncate">
                      {uploadedDocs.insurance_policy.filename}
                    </span>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 mt-1">Not selected</p>
                )}
              </div>
            </div>

            {/* Insurance Policy Selection - Same as Step 2 */}
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-500" />
                Select Insurance Policy
              </h3>
              {(() => {
                // Deduplicate policies by filename, prioritizing current claim's documents
                const uniquePolicies = [];
                const seenFilenames = new Set();
                // Sort to put current claim's documents first
                const sortedPolicies = [...previousPolicies].sort((a, b) => {
                  if (
                    a.claim_id === createdClaim?.id &&
                    b.claim_id !== createdClaim?.id
                  )
                    return -1;
                  if (
                    b.claim_id === createdClaim?.id &&
                    a.claim_id !== createdClaim?.id
                  )
                    return 1;
                  return new Date(b.created_at) - new Date(a.created_at);
                });
                for (const policy of sortedPolicies) {
                  const lowerFilename = policy.filename.toLowerCase();
                  if (!seenFilenames.has(lowerFilename)) {
                    seenFilenames.add(lowerFilename);
                    uniquePolicies.push(policy);
                  }
                }
                return uniquePolicies.length > 0 ? (
                  <>
                    <div className="bg-gray-50 rounded-lg border border-gray-200 divide-y divide-gray-200">
                      {uniquePolicies.map((doc) => {
                        const isSelected =
                          uploadedDocs.insurance_policy?.documentId === doc.id;
                        return (
                          <div
                            key={doc.id}
                            className={`flex items-center justify-between p-3 hover:bg-gray-100 transition-colors ${
                              isSelected
                                ? "bg-primary-50 border-l-4 border-l-primary-500"
                                : ""
                            }`}
                          >
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <FileText className="w-5 h-5 text-green-500 flex-shrink-0" />
                              <div className="min-w-0 flex-1">
                                <p className="font-medium text-gray-900 text-sm truncate">
                                  {doc.filename}
                                  {isSelected && (
                                    <span className="ml-2 text-xs text-primary-600 font-semibold">
                                      (Selected)
                                    </span>
                                  )}
                                </p>
                                <p className="text-xs text-gray-500 flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  {format(
                                    new Date(doc.created_at),
                                    "MMM d, yyyy 'at' h:mm a",
                                  )}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 ml-2">
                              {!isSelected && (
                                <button
                                  onClick={async () => {
                                    try {
                                      toast.loading(
                                        `Selecting ${doc.filename}...`,
                                        { id: "select-policy-review" },
                                      );

                                      // Fetch ALL insurance policies for this claim
                                      const currentClaimDocs =
                                        await fetchDocuments(createdClaim.id);
                                      const existingPolicies =
                                        currentClaimDocs.filter(
                                          (d) =>
                                            d.document_type ===
                                              "insurance_policy" &&
                                            d.id !== doc.id,
                                        );

                                      // Delete ALL existing insurance policies for this claim
                                      for (const oldPolicy of existingPolicies) {
                                        console.log(
                                          "Deleting old policy:",
                                          oldPolicy.id,
                                          oldPolicy.filename,
                                        );
                                        try {
                                          await deleteDocument(oldPolicy.id);
                                        } catch (err) {
                                          console.error(
                                            "Failed to delete old policy:",
                                            err,
                                          );
                                        }
                                      }

                                      // Check if this document is from the current claim or another claim
                                      if (doc.claim_id === createdClaim?.id) {
                                        // Document already belongs to this claim, just select it
                                        setUploadedDocs((prev) => ({
                                          ...prev,
                                          insurance_policy: {
                                            filename: doc.filename,
                                            status: doc.status,
                                            documentId: doc.id,
                                          },
                                        }));
                                      } else {
                                        // Document from another claim - copy it
                                        const copyResponse =
                                          await documentsAPI.copyToClaim(
                                            doc.id,
                                            createdClaim.id,
                                          );
                                        const copiedDoc =
                                          copyResponse.data?.data ||
                                          copyResponse.data;
                                        setUploadedDocs((prev) => ({
                                          ...prev,
                                          insurance_policy: {
                                            filename: copiedDoc.filename,
                                            status: copiedDoc.status,
                                            documentId: copiedDoc.id,
                                          },
                                        }));
                                      }

                                      // Refresh the policies list
                                      const policiesResponse =
                                        await documentsAPI.listUserInsurancePolicies();
                                      setPreviousPolicies(
                                        policiesResponse.data || [],
                                      );

                                      toast.success(
                                        `Selected: ${doc.filename}`,
                                        { id: "select-policy-review" },
                                      );
                                    } catch (error) {
                                      console.error(
                                        "Error selecting policy:",
                                        error,
                                      );
                                      toast.error(
                                        "Failed to select policy. Please try again.",
                                        { id: "select-policy-review" },
                                      );
                                    }
                                  }}
                                  disabled={uploading}
                                  className="px-3 py-1.5 text-xs font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-lg transition-colors touch-manipulation disabled:opacity-50"
                                >
                                  Select
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Click "Select" to choose a different insurance policy for
                      this claim.
                    </p>
                  </>
                ) : (
                  <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 text-center">
                    <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                    <p className="text-sm text-gray-500">
                      No insurance policies available
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Go back to upload an insurance policy
                    </p>
                  </div>
                );
              })()}
            </div>

            <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-3 pt-2">
              <button
                onClick={() => setCurrentStep(2)}
                className="btn-secondary w-full sm:w-auto justify-center touch-manipulation"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={
                  !uploadedDocs.discharge_summary ||
                  !uploadedDocs.insurance_policy
                }
                className="btn-primary w-full sm:w-auto justify-center touch-manipulation disabled:opacity-50"
              >
                View Claim & Analyze
                <ArrowRight className="w-5 h-5 ml-2" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmDoc && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Delete Document
              </h3>
              <button
                onClick={() => setDeleteConfirmDoc(null)}
                disabled={isDeleting}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <p className="text-gray-600 mb-2">
              Are you sure you want to delete{" "}
              <span className="font-medium">{deleteConfirmDoc.filename}</span>?
            </p>
            <p className="text-sm text-gray-500 mb-6">
              This will permanently remove the file from storage. This action
              cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirmDoc(null)}
                disabled={isDeleting}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeletePreviousPolicy}
                disabled={isDeleting}
                className="flex-1 px-4 py-2 bg-danger-500 text-white rounded-lg hover:bg-danger-700 transition-colors font-medium disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
