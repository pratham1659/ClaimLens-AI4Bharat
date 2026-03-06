// frontend/src/pages/PolicyChatPage.jsx

import { useState, useRef, useEffect } from "react";
import {
  Upload,
  FileText,
  Send,
  Bot,
  User,
  Loader2,
  X,
  CheckCircle,
  AlertCircle,
  Trash2,
  Database,
  BookOpen,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Plus,
  HardDrive,
} from "lucide-react";
import { clsx } from "clsx";
import api from "../services/api";
import { getErrorMessage } from "../utils/error";
import toast from "react-hot-toast";
import { ConfirmDialog } from "../components/common/ConfirmDialog";

export function PolicyChatPage() {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [documentId, setDocumentId] = useState(null);
  const [policyChunks, setPolicyChunks] = useState([]);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  // New state for pre-indexed mode
  const [usePreindexed, setUsePreindexed] = useState(false);
  const [preindexedInfo, setPreindexedInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(false);

  // Index management state
  const [refreshingIndex, setRefreshingIndex] = useState(false);
  const [deletingIndex, setDeletingIndex] = useState(false);
  const [buildStatus, setBuildStatus] = useState(""); // Status message during build
  const [buildProgress, setBuildProgress] = useState(0); // Progress percentage

  // Files list state
  const [indexedFiles, setIndexedFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [deletingFile, setDeletingFile] = useState(null);
  const [showFilesPanel, setShowFilesPanel] = useState(false);

  // Delete confirmation modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDeleteFileModal, setShowDeleteFileModal] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);

  // Mobile panel state
  const [showMobilePanel, setShowMobilePanel] = useState(false);

  const fileInputRef = useRef(null);
  const pdfInputRef = useRef(null);
  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Fetch pre-indexed policy info
  const fetchPreindexedInfo = async () => {
    setLoadingInfo(true);
    try {
      const response = await api.get("/policies/preindexed/info");
      setPreindexedInfo(response.data);
    } catch (err) {
      console.error("Failed to fetch pre-indexed info:", err);
      setPreindexedInfo({ available: false });
    } finally {
      setLoadingInfo(false);
    }
  };

  // Fetch indexed files list
  const fetchIndexedFiles = async () => {
    setLoadingFiles(true);
    try {
      const response = await api.get("/policies/preindexed/files");
      setIndexedFiles(response.data.files || []);
    } catch (err) {
      console.error("Failed to fetch indexed files:", err);
      setIndexedFiles([]);
    } finally {
      setLoadingFiles(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchPreindexedInfo();
    fetchIndexedFiles();
  }, []);

  // Refresh/rebuild the FAISS index
  const handleRefreshIndex = async () => {
    setRefreshingIndex(true);
    setBuildStatus("Initializing index build...");
    setBuildProgress(5);

    // Simulate progress while waiting for response
    const progressInterval = setInterval(() => {
      setBuildProgress((prev) => {
        if (prev >= 90) return prev;
        // Slow down as we approach 90%
        const increment = prev < 30 ? 5 : prev < 60 ? 3 : 1;
        return Math.min(prev + increment, 90);
      });
    }, 2000);

    try {
      setBuildStatus("Extracting clauses from PDFs...");
      setBuildProgress(10);

      // Use longer timeout for index building (5 minutes)
      const response = await api.post(
        "/policies/preindexed/refresh",
        {},
        {
          timeout: 300000, // 5 minutes
        },
      );

      clearInterval(progressInterval);

      if (response.data.success) {
        setBuildProgress(100);
        setBuildStatus("Index built successfully!");
        toast.success("Index rebuilt successfully!");
        // Refresh the info and file list
        await fetchPreindexedInfo();
        await fetchIndexedFiles();
      } else {
        setBuildProgress(0);
        setBuildStatus("");
        toast.error(response.data.error || "Failed to rebuild index");
      }
    } catch (err) {
      clearInterval(progressInterval);
      console.error("Refresh error:", err);
      setBuildProgress(0);
      setBuildStatus("");

      // Handle timeout error specifically
      if (err.code === "ECONNABORTED" || err.message?.includes("timeout")) {
        toast.error(
          "Index build is taking longer than expected. Please try again or check server logs.",
        );
      } else {
        toast.error(getErrorMessage(err, "Failed to refresh index"));
      }
    } finally {
      // Keep success message for a moment before clearing
      setTimeout(() => {
        setRefreshingIndex(false);
        setBuildStatus("");
        setBuildProgress(0);
      }, 1500);
    }
  };

  // Delete the FAISS index
  const handleDeleteIndex = async () => {
    setDeletingIndex(true);
    try {
      const response = await api.delete("/policies/preindexed/delete");
      if (response.data.success) {
        toast.success(response.data.message || "Index deleted");
        setUsePreindexed(false);
        setMessages([]);
        // Refresh the info
        await fetchPreindexedInfo();
      } else {
        toast.error(response.data.error || "Failed to delete index");
      }
    } catch (err) {
      console.error("Delete error:", err);
      toast.error(getErrorMessage(err, "Failed to delete index"));
    } finally {
      setDeletingIndex(false);
      setShowDeleteModal(false);
    }
  };

  // Delete individual PDF file
  const handleDeleteFile = async () => {
    if (!fileToDelete) return;

    setDeletingFile(fileToDelete.filename);
    try {
      const response = await api.delete(
        `/policies/preindexed/files/${encodeURIComponent(fileToDelete.filename)}`,
      );
      if (response.data.success) {
        toast.success(`Deleted ${fileToDelete.filename}`);
        // Refresh file list
        await fetchIndexedFiles();
      } else {
        toast.error(response.data.error || "Failed to delete file");
      }
    } catch (err) {
      console.error("Delete file error:", err);
      toast.error(getErrorMessage(err, "Failed to delete file"));
    } finally {
      setDeletingFile(null);
      setShowDeleteFileModal(false);
      setFileToDelete(null);
    }
  };

  // Open delete file confirmation
  const confirmDeleteFile = (file) => {
    setFileToDelete(file);
    setShowDeleteFileModal(true);
  };

  // Add new policy PDF to index
  const handleAddPolicyToIndex = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith(".pdf")) {
      toast.error("Please select a PDF file");
      return;
    }

    setRefreshingIndex(true);
    setBuildStatus(`Uploading ${file.name}...`);
    setBuildProgress(5);

    try {
      // First upload the file to data folder
      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_type", "policy");

      setBuildProgress(10);
      await api.post("/documents/upload-policy", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000, // 1 minute for upload
      });

      setBuildProgress(20);
      toast.success(`Uploaded ${file.name}. Rebuilding index...`);

      // Reset progress tracking for the refresh phase - don't call setRefreshingIndex again
      // Let handleRefreshIndex take over from here
      setBuildStatus("Starting index rebuild...");

      // Clear file input before calling refresh
      if (pdfInputRef.current) {
        pdfInputRef.current.value = "";
      }

      // Call refresh but don't set refreshingIndex to false at the end of this function
      // since handleRefreshIndex will manage that
      await handleRefreshIndex();
      return; // handleRefreshIndex will handle the finally cleanup
    } catch (err) {
      console.error("Add policy error:", err);
      setBuildProgress(0);
      setBuildStatus("");

      if (err.code === "ECONNABORTED" || err.message?.includes("timeout")) {
        toast.error(
          "Upload/build is taking too long. Please try with a smaller file or check server.",
        );
      } else {
        toast.error(getErrorMessage(err, "Failed to add policy to index"));
      }

      setRefreshingIndex(false);
      if (pdfInputRef.current) {
        pdfInputRef.current.value = "";
      }
    }
  };

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
        setUploadedFile(file);
        setError(null);
      } else {
        setError("Please upload a PDF file");
      }
    }
  };

  // Handle file drop
  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
        setUploadedFile(file);
        setError(null);
      } else {
        setError("Please upload a PDF file");
      }
    }
  };

  // Upload and process document
  const handleUpload = async () => {
    if (!uploadedFile) return;

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", uploadedFile);
      formData.append("document_type", "policy");

      // Upload document
      const uploadResponse = await api.post(
        "/documents/upload-policy",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );

      const docId =
        uploadResponse.data.data?.id || uploadResponse.data.document_id;
      setDocumentId(docId);
      setUploading(false);
      setProcessing(true);

      // Process document with RAG
      const processResponse = await api.post(`/policies/process/${docId}`);

      setPolicyChunks(processResponse.data.data?.chunks || []);
      setProcessing(false);
      setShowMobilePanel(false); // Close panel on mobile after upload

      // Add welcome message
      setMessages([
        {
          role: "assistant",
          content: `I've processed the policy document "${uploadedFile.name}". I found ${processResponse.data.data?.chunks?.length || 0} relevant sections. You can now ask me questions about this policy!`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      console.error("Upload error:", err);
      setError(getErrorMessage(err, "Failed to upload and process document"));
      setUploading(false);
      setProcessing(false);
    }
  };

  // Enable pre-indexed mode
  const handleUsePreindexed = () => {
    setUsePreindexed(true);
    setUploadedFile(null);
    setDocumentId(null);
    setPolicyChunks([]);
    setError(null);
    setShowMobilePanel(false); // Close panel on mobile

    // Add welcome message for pre-indexed mode
    setMessages([
      {
        role: "assistant",
        content: `I'm ready to help you with pre-indexed insurance policies! I have access to ${preindexedInfo?.total_clauses || "multiple"} policy clauses from: ${preindexedInfo?.policies?.join(", ") || "various insurers"}.\n\nYou can ask me questions about coverage, claims, waiting periods, exclusions, and more!`,
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  // Send chat message
  const handleSendMessage = async (e) => {
    e.preventDefault();

    // Allow sending if pre-indexed mode OR document uploaded
    if (!inputMessage.trim() || (!documentId && !usePreindexed)) return;

    const userMessage = {
      role: "user",
      content: inputMessage.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setSending(true);

    try {
      let response;

      if (usePreindexed) {
        // Use pre-indexed query endpoint
        response = await api.post("/policies/query", {
          query: userMessage.content,
          top_k: 5,
        });
      } else {
        // Use document-specific chat endpoint
        response = await api.post("/policies/chat", {
          document_id: documentId,
          message: userMessage.content,
          chat_history: messages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        });
      }

      const assistantMessage = {
        role: "assistant",
        content:
          response.data.data?.response ||
          response.data.response ||
          "I couldn't generate a response.",
        timestamp: new Date().toISOString(),
        sources: response.data.data?.sources || [],
        mode: response.data.data?.mode || "unknown",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Chat error:", err);
      const errorMessage = {
        role: "assistant",
        content: getErrorMessage(
          err,
          "Sorry, I encountered an error processing your question. Please try again.",
        ),
        timestamp: new Date().toISOString(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setSending(false);
    }
  };

  // Clear everything and start over
  const handleClear = () => {
    setUploadedFile(null);
    setDocumentId(null);
    setPolicyChunks([]);
    setMessages([]);
    setError(null);
    setUsePreindexed(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Check if chat is ready
  const isChatReady = documentId || usePreindexed;

  return (
    <div className="h-[calc(100vh-8rem)] sm:h-[calc(100vh-4rem)] flex flex-col">
      {/* Header - Responsive */}
      <div className="mb-4 sm:mb-6 flex-shrink-0">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
          Policy Chat
        </h1>
        <p className="text-sm sm:text-base text-gray-600 mt-1">
          Upload a policy document or use pre-indexed policies to chat with AI
        </p>
      </div>

      {/* Mobile Toggle Panel Button */}
      <div className="lg:hidden mb-3 flex-shrink-0">
        <button
          onClick={() => setShowMobilePanel(!showMobilePanel)}
          className="w-full flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 shadow-sm touch-manipulation"
        >
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary-600" />
            <span className="font-medium text-gray-900">
              {usePreindexed
                ? "Using Pre-indexed Policies"
                : documentId
                  ? "Document Ready"
                  : "Select Policy Source"}
            </span>
          </div>
          {showMobilePanel ? (
            <ChevronUp className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          )}
        </button>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 min-h-0">
        {/* Left Panel - Upload and Document Info (Collapsible on mobile) */}
        <div
          className={clsx(
            "lg:col-span-1 space-y-4 overflow-y-auto",
            showMobilePanel ? "block" : "hidden lg:block",
          )}
        >
          {/* Pre-indexed Policies Card */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4 flex items-center gap-2">
              <Database className="w-5 h-5 text-primary-600" />
              Pre-indexed Policies
            </h2>

            {loadingInfo ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : preindexedInfo?.available ? (
              <div className="space-y-3">
                <div className="p-3 bg-green-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-green-800">
                        {preindexedInfo.total_clauses} clauses available
                      </p>
                      <p className="text-xs text-green-600 mt-1">
                        From:{" "}
                        {preindexedInfo.policies?.join(", ") ||
                          "Multiple insurers"}
                      </p>
                    </div>
                    {preindexedInfo.index_size_mb > 0 && (
                      <div className="flex items-center gap-1 text-xs text-green-600">
                        <HardDrive className="w-3 h-3" />
                        {preindexedInfo.index_size_mb} MB
                      </div>
                    )}
                  </div>
                </div>

                {!usePreindexed ? (
                  <button
                    onClick={handleUsePreindexed}
                    className="w-full bg-primary-600 text-white py-2.5 sm:py-2 px-4 rounded-lg hover:bg-primary-700 flex items-center justify-center gap-2 touch-manipulation"
                  >
                    <BookOpen className="w-4 h-4" />
                    Chat with Pre-indexed Policies
                  </button>
                ) : (
                  <div className="space-y-2">
                    <div className="p-3 bg-primary-50 rounded-lg flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-primary-600" />
                        <span className="text-sm text-primary-700 font-medium">
                          Using pre-indexed policies
                        </span>
                      </div>
                      <button
                        onClick={handleClear}
                        className="text-xs text-primary-600 hover:text-primary-800 underline touch-manipulation"
                      >
                        Exit
                      </button>
                    </div>
                  </div>
                )}

                {/* Index Management Buttons */}
                <div className="pt-2 border-t border-gray-200">
                  <p className="text-xs text-gray-500 mb-2">Index Management</p>
                  <div className="flex gap-2 flex-wrap">
                    {/* Add New Policy */}
                    <label className="flex-1 min-w-0">
                      <input
                        ref={pdfInputRef}
                        type="file"
                        accept=".pdf"
                        onChange={handleAddPolicyToIndex}
                        className="hidden"
                        disabled={refreshingIndex}
                      />
                      <button
                        type="button"
                        onClick={() => pdfInputRef.current?.click()}
                        disabled={refreshingIndex}
                        className="w-full px-3 py-2 text-xs bg-green-50 text-green-700 rounded-lg hover:bg-green-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1 touch-manipulation"
                      >
                        <Plus className="w-3 h-3" />
                        Add Policy
                      </button>
                    </label>

                    {/* Refresh Index */}
                    <button
                      onClick={handleRefreshIndex}
                      disabled={refreshingIndex || deletingIndex}
                      className="flex-1 px-3 py-2 text-xs bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1 touch-manipulation"
                    >
                      {refreshingIndex ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <RefreshCw className="w-3 h-3" />
                      )}
                      Rebuild
                    </button>

                    {/* Delete Index */}
                    <button
                      onClick={() => setShowDeleteModal(true)}
                      disabled={refreshingIndex || deletingIndex}
                      className="flex-1 px-3 py-2 text-xs bg-red-50 text-red-700 rounded-lg hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1 touch-manipulation"
                    >
                      {deletingIndex ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Trash2 className="w-3 h-3" />
                      )}
                      Delete
                    </button>
                  </div>

                  {/* Files List Toggle */}
                  <button
                    onClick={() => {
                      setShowFilesPanel(!showFilesPanel);
                      if (!showFilesPanel) fetchIndexedFiles();
                    }}
                    className="w-full mt-2 px-3 py-2 text-xs text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 flex items-center justify-between touch-manipulation"
                  >
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      View PDF Files ({indexedFiles.length})
                    </span>
                    {showFilesPanel ? (
                      <ChevronUp className="w-3 h-3" />
                    ) : (
                      <ChevronDown className="w-3 h-3" />
                    )}
                  </button>

                  {/* Files List Panel */}
                  {showFilesPanel && (
                    <div className="mt-2 border border-gray-200 rounded-lg overflow-hidden">
                      {loadingFiles ? (
                        <div className="p-4 text-center">
                          <Loader2 className="w-4 h-4 animate-spin mx-auto text-gray-400" />
                        </div>
                      ) : indexedFiles.length === 0 ? (
                        <div className="p-4 text-center text-xs text-gray-500">
                          No PDF files found in data folder
                        </div>
                      ) : (
                        <div className="max-h-48 overflow-y-auto">
                          {indexedFiles.map((file, index) => (
                            <div
                              key={file.filename}
                              className={clsx(
                                "flex items-center justify-between px-3 py-2 text-xs",
                                index % 2 === 0 ? "bg-gray-50" : "bg-white",
                              )}
                            >
                              <div className="flex items-center gap-2 min-w-0 flex-1">
                                <FileText className="w-3 h-3 text-red-500 flex-shrink-0" />
                                <span
                                  className="truncate text-gray-700"
                                  title={file.filename}
                                >
                                  {file.filename}
                                </span>
                                <span className="text-gray-400 flex-shrink-0">
                                  ({file.size_mb} MB)
                                </span>
                              </div>
                              <button
                                onClick={() => confirmDeleteFile(file)}
                                disabled={deletingFile === file.filename}
                                className="ml-2 p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded disabled:opacity-50 touch-manipulation"
                                title="Delete file"
                              >
                                {deletingFile === file.filename ? (
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                ) : (
                                  <X className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="px-3 py-2 bg-yellow-50 border-t border-gray-200">
                        <p className="text-xs text-yellow-700">
                          Note: Rebuild index after deleting files
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3 bg-yellow-50 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    No pre-indexed policies available.
                  </p>
                  <p className="text-xs text-yellow-600 mt-1">
                    Add a policy PDF or rebuild the index.
                  </p>
                </div>

                {/* Build Index Options when none exists */}
                <div className="flex flex-col sm:flex-row gap-2">
                  <label className="flex-1 w-full">
                    <input
                      ref={pdfInputRef}
                      type="file"
                      accept=".pdf"
                      onChange={handleAddPolicyToIndex}
                      className="hidden"
                      disabled={refreshingIndex}
                    />
                    <button
                      type="button"
                      onClick={() => pdfInputRef.current?.click()}
                      disabled={refreshingIndex}
                      className="w-full px-3 py-2.5 sm:py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 touch-manipulation"
                    >
                      {refreshingIndex ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Plus className="w-4 h-4" />
                      )}
                      Add Policy PDF
                    </button>
                  </label>

                  <button
                    onClick={handleRefreshIndex}
                    disabled={refreshingIndex}
                    className="w-full sm:w-auto px-3 py-2.5 sm:py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 touch-manipulation"
                  >
                    {refreshingIndex ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                    Build Index
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Upload Section */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-gray-600" />
              Upload Custom Policy
            </h2>

            {!documentId && !usePreindexed ? (
              <>
                {/* Drop Zone */}
                <div
                  className={clsx(
                    "border-2 border-dashed rounded-lg p-4 sm:p-6 text-center transition-colors cursor-pointer touch-manipulation",
                    uploadedFile
                      ? "border-primary-500 bg-primary-50"
                      : "border-gray-300 hover:border-gray-400",
                  )}
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                  />

                  {uploadedFile ? (
                    <div className="space-y-2">
                      <FileText className="w-8 h-8 sm:w-10 sm:h-10 text-primary-600 mx-auto" />
                      <p className="text-sm font-medium text-gray-900 truncate px-2">
                        {uploadedFile.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="w-8 h-8 sm:w-10 sm:h-10 text-gray-400 mx-auto" />
                      <p className="text-sm text-gray-600">
                        Drop a PDF here or tap to browse
                      </p>
                      <p className="text-xs text-gray-400">
                        Max file size: 50MB
                      </p>
                    </div>
                  )}
                </div>

                {error && (
                  <div className="mt-3 sm:mt-4 p-3 bg-red-50 rounded-lg flex items-center gap-2 text-red-700 text-sm">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                  </div>
                )}

                {uploadedFile && (
                  <button
                    onClick={handleUpload}
                    disabled={uploading || processing}
                    className="mt-3 sm:mt-4 w-full bg-primary-600 text-white py-2.5 sm:py-2 px-4 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 touch-manipulation"
                  >
                    {uploading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Uploading...
                      </>
                    ) : processing ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Processing with AI...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4" />
                        Process Document
                      </>
                    )}
                  </button>
                )}
              </>
            ) : documentId ? (
              <div className="space-y-3 sm:space-y-4">
                <div className="p-3 sm:p-4 bg-green-50 rounded-lg flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-green-800">
                      Document Ready
                    </p>
                    <p className="text-xs text-green-600 mt-1 truncate">
                      {uploadedFile?.name}
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleClear}
                  className="w-full border border-gray-300 text-gray-700 py-2.5 sm:py-2 px-4 rounded-lg hover:bg-gray-50 flex items-center justify-center gap-2 touch-manipulation"
                >
                  <Trash2 className="w-4 h-4" />
                  Start Over
                </button>
              </div>
            ) : usePreindexed ? (
              <div className="text-center py-4">
                <p className="text-sm text-gray-500">
                  Using pre-indexed policies
                </p>
                <button
                  onClick={handleClear}
                  className="mt-3 text-sm text-primary-600 hover:text-primary-700 touch-manipulation"
                >
                  Switch to custom upload
                </button>
              </div>
            ) : null}
          </div>

          {/* Policy Chunks Info - Hidden on mobile when panel is collapsed */}
          {policyChunks.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
              <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4">
                Extracted Sections
              </h2>
              <div className="space-y-2 max-h-48 sm:max-h-64 overflow-y-auto">
                {policyChunks.slice(0, 10).map((chunk, index) => (
                  <div
                    key={index}
                    className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600"
                  >
                    <p className="font-medium text-gray-800 mb-1">
                      Section {index + 1}
                    </p>
                    <p className="line-clamp-2 text-xs sm:text-sm">
                      {chunk.content || chunk}
                    </p>
                  </div>
                ))}
                {policyChunks.length > 10 && (
                  <p className="text-xs text-gray-500 text-center">
                    +{policyChunks.length - 10} more sections
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Chat */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col min-h-0">
          {/* Chat Header */}
          <div className="px-4 sm:px-6 py-3 sm:py-4 border-b flex-shrink-0">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Bot className="w-5 h-5 text-primary-600" />
              Chat with Policy AI
            </h2>
            <p className="text-xs sm:text-sm text-gray-500 mt-1">
              {usePreindexed
                ? "Ask questions about pre-indexed insurance policies"
                : documentId
                  ? "Ask questions about your uploaded policy document"
                  : "Upload a document or use pre-indexed policies to start chatting"}
            </p>
          </div>

          {/* Chat Messages */}
          <div
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-3 sm:space-y-4"
          >
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-center px-4">
                <div className="text-gray-400">
                  <Bot className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 sm:mb-4 opacity-50" />
                  <p className="text-base sm:text-lg font-medium">
                    No messages yet
                  </p>
                  <p className="text-xs sm:text-sm mt-2">
                    {preindexedInfo?.available
                      ? "Use pre-indexed policies or upload a document to start chatting"
                      : "Upload a policy document to start chatting"}
                  </p>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={clsx(
                    "flex gap-2 sm:gap-3",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="w-7 h-7 sm:w-8 sm:h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-primary-600" />
                    </div>
                  )}
                  <div
                    className={clsx(
                      "max-w-[85%] sm:max-w-[80%] rounded-lg px-3 sm:px-4 py-2 sm:py-3",
                      message.role === "user"
                        ? "bg-primary-600 text-white"
                        : message.isError
                          ? "bg-red-50 text-red-800"
                          : "bg-gray-100 text-gray-800",
                    )}
                  >
                    <p className="text-sm whitespace-pre-wrap">
                      {message.content}
                    </p>
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-200">
                        <p className="text-xs text-gray-500 mb-1">
                          Sources: {message.sources.length} relevant sections
                        </p>
                        <div className="space-y-1">
                          {message.sources.slice(0, 2).map((source, idx) => (
                            <p
                              key={idx}
                              className="text-xs text-gray-400 truncate"
                            >
                              •{" "}
                              {source.content?.substring(0, 80) ||
                                source.clause_id}
                              ...
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  {message.role === "user" && (
                    <div className="w-7 h-7 sm:w-8 sm:h-8 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <User className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
                    </div>
                  )}
                </div>
              ))
            )}
            {sending && (
              <div className="flex gap-2 sm:gap-3">
                <div className="w-7 h-7 sm:w-8 sm:h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-primary-600" />
                </div>
                <div className="bg-gray-100 rounded-lg px-3 sm:px-4 py-2 sm:py-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-gray-600" />
                    <span className="text-sm text-gray-500">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="px-4 sm:px-6 py-3 sm:py-4 border-t flex-shrink-0">
            <form onSubmit={handleSendMessage} className="flex gap-2 sm:gap-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  isChatReady
                    ? "Ask a question about the policy..."
                    : "Upload a document or select pre-indexed policies first"
                }
                disabled={!isChatReady || sending}
                className="flex-1 px-3 sm:px-4 py-2.5 sm:py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed text-base sm:text-sm"
              />
              <button
                type="submit"
                disabled={!isChatReady || !inputMessage.trim() || sending}
                className="px-3 sm:px-4 py-2.5 sm:py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 touch-manipulation"
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline">Send</span>
              </button>
            </form>
            {usePreindexed && (
              <p className="mt-2 text-xs text-gray-400 text-center">
                Using local RAG with pre-indexed policy data
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Index Building Overlay */}
      {refreshingIndex && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 sm:p-8 max-w-md mx-4 text-center">
            <div className="mb-4">
              <div className="w-16 h-16 mx-auto bg-primary-100 rounded-full flex items-center justify-center">
                <RefreshCw className="w-8 h-8 text-primary-600 animate-spin" />
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Building Index
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              {buildStatus || "Processing policy documents..."}
            </p>
            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
              <div
                className="bg-primary-600 h-2 rounded-full transition-all duration-500"
                style={{
                  width: `${buildProgress}%`,
                }}
              />
            </div>
            <p className="text-xs text-gray-500 mb-4">
              {buildProgress}% complete
            </p>
            <p className="text-xs text-gray-400">
              This may take a few minutes depending on the number of documents
            </p>
          </div>
        </div>
      )}

      {/* Delete Index Confirmation Modal */}
      <ConfirmDialog
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteIndex}
        title="Delete Index"
        message="Are you sure you want to delete the FAISS index? This action cannot be undone. You will need to rebuild the index before using pre-indexed policies again."
        confirmText={deletingIndex ? "Deleting..." : "Delete Index"}
        cancelText="Cancel"
        variant="danger"
      />

      {/* Delete File Confirmation Modal */}
      <ConfirmDialog
        isOpen={showDeleteFileModal}
        onClose={() => {
          setShowDeleteFileModal(false);
          setFileToDelete(null);
        }}
        onConfirm={handleDeleteFile}
        title="Delete PDF File"
        message={`Are you sure you want to delete "${fileToDelete?.filename}"? This will remove the file from the data folder. You'll need to rebuild the index after deleting files.`}
        confirmText={deletingFile ? "Deleting..." : "Delete File"}
        cancelText="Cancel"
        variant="danger"
      />
    </div>
  );
}
