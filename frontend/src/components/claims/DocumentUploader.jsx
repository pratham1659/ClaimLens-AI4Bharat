// frontend/src/components/claims/DocumentUploader.jsx
/**
 * Document upload component with drag and drop.
 */

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, File, X, CheckCircle, Loader } from "lucide-react";
import { clsx } from "clsx";

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
  const isComplete = uploadProgress === 100 || uploadedFile;

  return (
    <div
      {...getRootProps()}
      className={clsx(
        "relative border-2 border-dashed rounded-xl p-6 transition-all cursor-pointer",
        isDragActive && "border-primary-500 bg-primary-50",
        isComplete && "border-success-500 bg-success-50",
        !isDragActive &&
          !isComplete &&
          "border-gray-300 hover:border-primary-400",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      <input {...getInputProps()} />

      <div className="flex flex-col items-center text-center">
        {isUploading ? (
          <>
            <Loader className="w-10 h-10 text-primary-600 animate-spin" />
            <p className="mt-2 text-sm font-medium text-gray-700">
              Uploading... {uploadProgress}%
            </p>
            <div className="w-full mt-2 bg-gray-200 rounded-full h-2">
              <div
                className="bg-primary-600 h-2 rounded-full transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </>
        ) : isComplete ? (
          <>
            <CheckCircle className="w-10 h-10 text-success-500" />
            <p className="mt-2 text-sm font-medium text-success-700">
              {uploadedFile?.filename || "Uploaded"}
            </p>
          </>
        ) : (
          <>
            <Upload className="w-10 h-10 text-gray-400" />
            <p className="mt-2 text-sm font-medium text-gray-700">
              {config.label}
            </p>
            <p className="text-xs text-gray-500">{config.description}</p>
            <p className="mt-2 text-xs text-gray-400">
              Drag & drop or click to upload
            </p>
          </>
        )}
      </div>
    </div>
  );
}
