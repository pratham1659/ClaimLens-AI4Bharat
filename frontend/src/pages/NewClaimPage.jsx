// frontend/src/pages/NewClaimPage.jsx
/**
 * New claim creation page with document upload.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { useClaims } from "../hooks/useClaims";
import { useDocuments } from "../hooks/useDocuments";
import { DocumentUploader } from "../components/claims/DocumentUploader";
import toast from "react-hot-toast";

const steps = [
  { id: 1, name: "Claim Details" },
  { id: 2, name: "Upload Documents" },
  { id: 3, name: "Review & Submit" },
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
    billing_data: null,
  });

  const navigate = useNavigate();
  const { createClaim } = useClaims();
  const { uploadDocument, uploadProgress, uploading } = useDocuments();

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
    if (!createdClaim) return;

    try {
      await uploadDocument(createdClaim.id, file, documentType);
      setUploadedDocs((prev) => ({
        ...prev,
        [documentType]: { filename: file.name },
      }));
    } catch (error) {
      // Error handled in hook
    }
  };

  const handleSubmit = () => {
    if (!uploadedDocs.discharge_summary || !uploadedDocs.insurance_policy) {
      toast.error("Please upload required documents");
      return;
    }
    navigate(`/claims/${createdClaim.id}`);
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Create New Claim</h1>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
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
                {step.name}
              </span>
              {index < steps.length - 1 && (
                <div
                  className={`w-24 h-0.5 mx-4 ${
                    currentStep > step.id ? "bg-primary-600" : "bg-gray-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="card p-8">
        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">
              Claim Information
            </h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
            <div className="flex justify-end">
              <button
                onClick={handleCreateClaim}
                disabled={!claimData.patient_name}
                className="btn-primary"
              >
                Continue
                <ArrowRight className="w-5 h-5 ml-2" />
              </button>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">
              Upload Documents
            </h2>
            <p className="text-gray-600">
              Upload the required documents for compliance analysis.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <DocumentUploader
                documentType="discharge_summary"
                onUpload={handleUpload}
                uploadProgress={uploadProgress["discharge_summary"]}
                uploadedFile={uploadedDocs.discharge_summary}
                disabled={uploading}
              />
              <DocumentUploader
                documentType="insurance_policy"
                onUpload={handleUpload}
                uploadProgress={uploadProgress["insurance_policy"]}
                uploadedFile={uploadedDocs.insurance_policy}
                disabled={uploading}
              />
            </div>

            <div>
              <p className="text-sm text-gray-500 mb-2">
                Optional: Billing Data
              </p>
              <DocumentUploader
                documentType="billing_data"
                onUpload={handleUpload}
                uploadProgress={uploadProgress["billing_data"]}
                uploadedFile={uploadedDocs.billing_data}
                disabled={uploading}
              />
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep(1)}
                className="btn-secondary"
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
                className="btn-primary"
              >
                Continue
                <ArrowRight className="w-5 h-5 ml-2" />
              </button>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">
              Review & Submit
            </h2>

            <div className="bg-gray-50 rounded-lg p-6 space-y-4">
              <div>
                <p className="text-sm text-gray-500">Claim Number</p>
                <p className="font-medium">{createdClaim?.claim_number}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Patient Name</p>
                <p className="font-medium">{claimData.patient_name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Documents Uploaded</p>
                <ul className="mt-1 space-y-1">
                  {Object.entries(uploadedDocs).map(
                    ([type, doc]) =>
                      doc && (
                        <li key={type} className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-success-500" />
                          <span className="text-sm">{doc.filename}</span>
                        </li>
                      ),
                  )}
                </ul>
              </div>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep(2)}
                className="btn-secondary"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Back
              </button>
              <button onClick={handleSubmit} className="btn-primary">
                View Claim & Analyze
                <ArrowRight className="w-5 h-5 ml-2" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
