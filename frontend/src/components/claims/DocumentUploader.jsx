// frontend/src/components/claims/DocumentUploader.jsx
/**
 * Document upload component with drag and drop and enhanced loader.
 */

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, CheckCircle, X, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import { LoadingSpinner } from "../common/LoadingSpinner";

const documentTypes = {
  discharge_summary: {
    label: "Discharge Summary",
    description: "Hospital discharge summary (PDF)",
    accept: { "application/pdf": [".pdf"] },
  },
  insurance_policy: {
    label: "Insurance Policy",
    description: "Insurance policy document (PDF)",
    accept: { "application/pdf": [".pdf"] },
  },
  billing_data: {
    label: "Billing Data",
    description: "Billing information (JSON)",
    accept: { "application/json": [".json"] },
  },
};

export function DocumentUploader({
  documentType,
  onUpload,
  uploadProgress,
  uploadedFile,
  disabled,
  onDelete,
}) {
  const config = documentTypes[documentType];

  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        onUpload(acceptedFiles[0], documentType);
      }
    },
    [onUpload, documentType],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: config.accept,
    maxFiles: 1,
    disabled: disabled || uploadProgress !== undefined,
  });

  const isUploading = uploadProgress !== undefined && uploadProgress < 100;
  // Only show as complete when uploaded AND processed
  const isComplete = (uploadProgress === 100 || uploadedFile) && uploadedFile?.status === "processed";
  const isFailed = uploadedFile?.status === "failed";
  const isProcessing = uploadedFile && !isComplete && !isFailed;

  return (
    <div
      {...getRootProps()}
      className={clsx(
        "relative border-2 border-dashed rounded-xl transition-all cursor-pointer overflow-hidden",
        isDragActive && "border-primary-500 bg-primary-50",
        isComplete && "border-success-500 bg-success-50",
        isFailed && "border-danger-500 bg-danger-50",
        isProcessing && "border-primary-400 bg-primary-25",
        !isDragActive &&
          !isComplete &&
          !isFailed &&
          !isProcessing &&
          "border-gray-300 hover:border-primary-400 hover:bg-gray-50",
        isUploading && "border-primary-400 bg-primary-25",
      )}
    >
      <input {...getInputProps()} />

      {/* Loading Overlay Background */}
      {isUploading && (
        <div className="absolute inset-0 bg-white/50 backdrop-blur-sm z-10" />
      )}

      <div
        className={clsx(
          "flex flex-col items-center text-center p-6 sm:p-8 transition-all",
          isUploading && "relative z-20",
        )}
      >
        {isUploading ? (
          <>
            {/* Spinner */}
            <LoadingSpinner size="lg" />

            {/* Loading Text */}
            <p className="mt-4 text-base sm:text-lg font-semibold text-gray-900">
              Uploading Document
            </p>
            <p className="mt-1 text-sm text-gray-600">
              Please wait while we process your file...
            </p>

            {/* Progress Percentage */}
            <p className="mt-3 text-2xl font-bold text-primary-600">
              {uploadProgress}%
            </p>

            {/* Enhanced Progress Bar */}
            <div className="w-full mt-4 bg-gray-200 rounded-full h-3 overflow-hidden shadow-sm">
              <div
                className="bg-gradient-to-r from-primary-500 to-primary-600 h-3 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>

            {/* Status Message */}
            <p className="mt-3 text-xs sm:text-sm text-gray-500">
              {uploadProgress < 50
                ? "Reading file..."
                : uploadProgress < 100
                  ? "Processing upload..."
                  : "Finalizing..."}
            </p>
          </>
        ) : isFailed ? (
          <>
            <AlertTriangle className="w-12 h-12 sm:w-14 sm:h-14 text-danger-500" />
            <p className="mt-3 text-base sm:text-lg font-semibold text-danger-700">
              {uploadedFile?.filename || "Document Processing Failed"}
            </p>
            <p className="mt-1 text-xs sm:text-sm text-danger-600">
              Processing failed. Please retry upload.
            </p>
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                className="mt-4 btn-danger text-xs inline-flex items-center gap-1"
                title="Retry upload"
              >
                <X className="w-4 h-4" />
                Retry
              </button>
            )}
          </>
        ) : isProcessing ? (
          <>
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-base sm:text-lg font-semibold text-gray-900">
              {uploadedFile?.filename || "Document Uploaded"}
            </p>
            <p className="mt-1 text-xs sm:text-sm text-primary-600">
              Processing document... This may take a minute
            </p>
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                className="mt-4 btn-danger text-xs inline-flex items-center gap-1"
                title="Delete this document"
              >
                <X className="w-4 h-4" />
                Cancel
              </button>
            )}
          </>
        ) : isComplete ? (
          <>
            <CheckCircle className="w-12 h-12 sm:w-14 sm:h-14 text-success-500" />
            <p className="mt-3 text-base sm:text-lg font-semibold text-success-700">
              {uploadedFile?.filename || "Document Uploaded"}
            </p>
            <p className="mt-1 text-xs sm:text-sm text-success-600">
              Ready for analysis
            </p>
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                className="mt-4 btn-danger text-xs inline-flex items-center gap-1"
                title="Delete this document"
              >
                <X className="w-4 h-4" />
                Delete
              </button>
            )}
          </>
        ) : (
          <>
            <Upload className="w-10 h-10 sm:w-12 sm:h-12 text-gray-400" />
            <p className="mt-3 text-base sm:text-lg font-semibold text-gray-900">
              {config.label}
            </p>
            <p className="mt-1 text-xs sm:text-sm text-gray-600">
              {config.description}
            </p>
            <p className="mt-2 text-xs text-gray-500">
              Drag & drop or click to upload
            </p>
          </>
        )}
      </div>
    </div>
  );
}
