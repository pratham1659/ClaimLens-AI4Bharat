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
} from "lucide-react";
import { clsx } from "clsx";
import api from "../services/api";
import { getErrorMessage } from "../utils/error";

// Maximum file size: 5 MB in bytes
const MAX_FILE_SIZE = 5 * 1024 * 1024;

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

  // Mobile panel state
  const [showMobilePanel, setShowMobilePanel] = useState(false);

  // Upload progress modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState("");

  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Fetch pre-indexed policy info on mount
  useEffect(() => {
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
    fetchPreindexedInfo();
  }, []);

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > MAX_FILE_SIZE) {
        setError("File is too large. Maximum size is 5 MB.");
        return;
      }
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
      if (file.size > MAX_FILE_SIZE) {
        setError("File is too large. Maximum size is 5 MB.");
        return;
      }
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
    setShowUploadModal(true);
    setUploadProgress(0);
    setUploadStage("Uploading document...");

    // Simulate initial progress
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 30) return prev;
        return prev + Math.random() * 5;
      });
    }, 200);

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
      setUploadProgress(40);
      setUploadStage("Processing document...");

      // Simulate processing progress
      clearInterval(progressInterval);
      const processingInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 85) return prev;
          return prev + Math.random() * 8;
        });
      }, 300);

      // Process document with RAG
      setUploadStage("Extracting text and creating embeddings...");
      const processResponse = await api.post(`/policies/process/${docId}`);

      clearInterval(processingInterval);
      setUploadProgress(100);
      setUploadStage("Complete!");

      setPolicyChunks(processResponse.data.data?.chunks || []);
      setProcessing(false);

      // Close modal after short delay
      setTimeout(() => {
        setShowUploadModal(false);
        setShowMobilePanel(false); // Close panel on mobile after upload
      }, 500);

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
      clearInterval(progressInterval);
      setShowUploadModal(false);

      const backendMessage = getErrorMessage(
        err,
        "Failed to upload and process document",
      );

      if (
        backendMessage
          .toLowerCase()
          .includes("does not appear to be an insurance policy")
      ) {
        setError(
          "Only insurance policy PDFs are accepted. Please upload a valid insurance policy document.",
        );
      } else {
        setError(backendMessage);
      }

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
                  <p className="text-sm font-medium text-green-800">
                    {preindexedInfo.total_clauses} clauses available
                  </p>
                  <div className="text-xs text-green-600 mt-1">
                    <p>From:</p>
                    {preindexedInfo.policies?.length ? (
                      <ul className="list-disc list-inside mt-1 space-y-0.5">
                        {preindexedInfo.policies.map((policyName) => (
                          <li key={policyName}>{policyName}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-1">Multiple insurers</p>
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
                  <div className="p-3 bg-primary-50 rounded-lg flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-primary-600" />
                    <span className="text-sm text-primary-700 font-medium">
                      Using pre-indexed policies
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-3 bg-yellow-50 rounded-lg">
                <p className="text-sm text-yellow-800">
                  No pre-indexed policies available.
                </p>
                <p className="text-xs text-yellow-600 mt-1">
                  Run the indexing script to enable this feature.
                </p>
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
                      <p className="text-xs text-amber-700 font-medium">
                        Only insurance policy PDFs are accepted
                      </p>
                      <p className="text-xs text-gray-400">
                        Maximum file size: 5 MB
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

      {/* Upload Progress Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                {uploadProgress < 100 ? (
                  <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
                ) : (
                  <CheckCircle className="w-8 h-8 text-green-600" />
                )}
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {uploadProgress < 100 ? "Processing Document" : "Complete!"}
              </h3>
              <p className="text-sm text-gray-600 mb-6">{uploadStage}</p>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                <div
                  className="bg-primary-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(uploadProgress, 100)}%` }}
                />
              </div>
              <p className="text-sm font-medium text-primary-600">
                {Math.round(uploadProgress)}% complete
              </p>

              {/* Stage indicators */}
              <div className="mt-4 flex justify-center gap-2 text-xs text-gray-500">
                <span
                  className={
                    uploadProgress >= 0 ? "text-primary-600 font-medium" : ""
                  }
                >
                  Upload
                </span>
                <span>→</span>
                <span
                  className={
                    uploadProgress >= 40 ? "text-primary-600 font-medium" : ""
                  }
                >
                  Process
                </span>
                <span>→</span>
                <span
                  className={
                    uploadProgress >= 70 ? "text-primary-600 font-medium" : ""
                  }
                >
                  Embed
                </span>
                <span>→</span>
                <span
                  className={
                    uploadProgress >= 100 ? "text-green-600 font-medium" : ""
                  }
                >
                  Done
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
