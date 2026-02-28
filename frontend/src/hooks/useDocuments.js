// frontend/src/hooks/useDocuments.js
/**
 * Custom hook for document management.
 */

import { useState, useCallback } from "react";
import { documentsAPI } from "../services/api";
import toast from "react-hot-toast";

export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  const uploadDocument = useCallback(async (claimId, file, documentType) => {
    const fileId = `${Date.now()}-${file.name}`;
    setUploading(true);
    setUploadProgress((prev) => ({ ...prev, [fileId]: 0 }));

    try {
      // Get presigned URL
      const urlResponse = await documentsAPI.getUploadUrl({
        claim_id: claimId,
        document_type: documentType,
        filename: file.name,
        content_type: file.type || "application/pdf",
        file_size: file.size,
      });

      const { document_id, upload_url } = urlResponse.data;

      // Upload to S3
      await documentsAPI.uploadToS3(
        upload_url,
        file,
        file.type || "application/pdf",
      );
      setUploadProgress((prev) => ({ ...prev, [fileId]: 50 }));

      // Trigger processing
      await documentsAPI.process(document_id);
      setUploadProgress((prev) => ({ ...prev, [fileId]: 100 }));

      toast.success(`${file.name} uploaded successfully`);
      return document_id;
    } catch (error) {
      toast.error(`Failed to upload ${file.name}`);
      throw error;
    } finally {
      setUploading(false);
      setTimeout(() => {
        setUploadProgress((prev) => {
          const newProgress = { ...prev };
          delete newProgress[fileId];
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
      toast.error("Failed to fetch documents");
      throw error;
    }
  }, []);

  const deleteDocument = useCallback(async (documentId) => {
    try {
      await documentsAPI.delete(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      toast.success("Document deleted");
    } catch (error) {
      toast.error("Failed to delete document");
      throw error;
    }
  }, []);

  const getDownloadUrl = useCallback(async (documentId) => {
    try {
      const response = await documentsAPI.getDownloadUrl(documentId);
      return response.data.download_url;
    } catch (error) {
      toast.error("Failed to get download URL");
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
