// frontend/src/hooks/useDocuments.js
/**
 * Custom hook for document management.
 */

import { useState, useCallback } from "react";
import { documentsAPI } from "../services/api";
import toast from "react-hot-toast";
import { getErrorMessage } from "../utils/error";

export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  const uploadDocument = useCallback(async (claimId, file, documentType) => {
    const progressKey = documentType;
    setUploading(true);
    setUploadProgress((prev) => ({ ...prev, [progressKey]: 0 }));

    try {
      // Always use backend direct upload to avoid browser-to-S3 CORS/preflight issues
      const directResponse = await documentsAPI.uploadDirect(
        claimId,
        documentType,
        file,
      );
      const documentId = directResponse.data.document_id;
      setUploadProgress((prev) => ({ ...prev, [progressKey]: 60 }));

      // Trigger processing
      await documentsAPI.process(documentId);
      setUploadProgress((prev) => ({ ...prev, [progressKey]: 100 }));

      toast.success(`${file.name} uploaded successfully`);
      return documentId;
    } catch (error) {
      const message = getErrorMessage(error, `Failed to upload ${file.name}`);
      if (error?.response?.status === 404) {
        toast.error(
          "Direct upload endpoint not found. Restart backend with latest code and try again.",
        );
      } else {
        toast.error(message);
      }
      throw error;
    } finally {
      setUploading(false);
      setTimeout(() => {
        setUploadProgress((prev) => {
          const newProgress = { ...prev };
          delete newProgress[progressKey];
          return newProgress;
        });
      }, 1000);
    }
  }, []);

  const fetchDocuments = useCallback(async (claimId) => {
    try {
      const response = await documentsAPI.listByClaimId(claimId);
      setDocuments(response.data);
      return response.data;
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to fetch documents"));
      throw error;
    }
  }, []);

  const deleteDocument = useCallback(async (documentId) => {
    try {
      await documentsAPI.delete(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      toast.success("Document deleted");
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to delete document"));
      throw error;
    }
  }, []);

  const getDownloadUrl = useCallback(async (documentId) => {
    try {
      const response = await documentsAPI.getDownloadUrl(documentId);
      return response.data.download_url;
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to get download URL"));
      throw error;
    }
  }, []);

  return {
    documents,
    uploading,
    uploadProgress,
    uploadDocument,
    fetchDocuments,
    deleteDocument,
    getDownloadUrl,
  };
}
