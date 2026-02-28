// frontend/src/pages/PolicyChatPage.jsx
/**
 * Policy Chat page with document upload and RAG-powered chat.
 */

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
} from "lucide-react";
import { clsx } from "clsx";
import api from "../services/api";

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

  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

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
      setError(
        err.response?.data?.detail || "Failed to upload and process document",
      );
      setUploading(false);
      setProcessing(false);
    }
  };

  // Send chat message
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || !documentId) return;

    const userMessage = {
      role: "user",
      content: inputMessage.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setSending(true);

    try {
      const response = await api.post("/policies/chat", {
        document_id: documentId,
        message: userMessage.content,
        chat_history: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      });

      const assistantMessage = {
        role: "assistant",
        content:
          response.data.data?.response ||
          response.data.response ||
          "I couldn't generate a response.",
        timestamp: new Date().toISOString(),
        sources: response.data.data?.sources || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Chat error:", err);
      const errorMessage = {
        role: "assistant",
        content:
          "Sorry, I encountered an error processing your question. Please try again.",
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
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)]">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Policy Chat</h1>
        <p className="text-gray-600 mt-1">
          Upload a policy document and chat with AI to understand its contents
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100%-5rem)]">
        {/* Left Panel - Upload and Document Info */}
        <div className="lg:col-span-1 space-y-4">
          {/* Upload Section */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Policy Document
            </h2>

            {!documentId ? (
              <>
                {/* Drop Zone */}
                <div
                  className={clsx(
                    "border-2 border-dashed rounded-lg p-6 text-center transition-colors",
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
                      <FileText className="w-10 h-10 text-primary-600 mx-auto" />
                      <p className="text-sm font-medium text-gray-900">
                        {uploadedFile.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="w-10 h-10 text-gray-400 mx-auto" />
                      <p className="text-sm text-gray-600">
                        Drop a PDF here or click to browse
                      </p>
                      <p className="text-xs text-gray-400">
                        Max file size: 50MB
                      </p>
                    </div>
                  )}
                </div>

                {error && (
                  <div className="mt-4 p-3 bg-red-50 rounded-lg flex items-center gap-2 text-red-700 text-sm">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                  </div>
                )}

                {uploadedFile && (
                  <button
                    onClick={handleUpload}
                    disabled={uploading || processing}
                    className="mt-4 w-full bg-primary-600 text-white py-2 px-4 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
            ) : (
              <div className="space-y-4">
                <div className="p-4 bg-green-50 rounded-lg flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-green-800">
                      Document Ready
                    </p>
                    <p className="text-xs text-green-600 mt-1">
                      {uploadedFile?.name}
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleClear}
                  className="w-full border border-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-50 flex items-center justify-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Upload New Document
                </button>
              </div>
            )}
          </div>

          {/* Policy Chunks Info */}
          {policyChunks.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Extracted Sections
              </h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {policyChunks.slice(0, 10).map((chunk, index) => (
                  <div
                    key={index}
                    className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600"
                  >
                    <p className="font-medium text-gray-800 mb-1">
                      Section {index + 1}
                    </p>
                    <p className="line-clamp-2">{chunk.content || chunk}</p>
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
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col">
          {/* Chat Header */}
          <div className="px-6 py-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">
              Chat with Policy AI
            </h2>
            <p className="text-sm text-gray-500">
              Ask questions about the uploaded policy document
            </p>
          </div>

          {/* Chat Messages */}
          <div
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto p-6 space-y-4"
          >
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-center">
                <div className="text-gray-400">
                  <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">No messages yet</p>
                  <p className="text-sm mt-2">
                    Upload a policy document to start chatting
                  </p>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={clsx(
                    "flex gap-3",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-primary-600" />
                    </div>
                  )}
                  <div
                    className={clsx(
                      "max-w-[80%] rounded-lg px-4 py-3",
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
                        <p className="text-xs text-gray-500">
                          Sources: {message.sources.length} relevant sections
                        </p>
                      </div>
                    )}
                  </div>
                  {message.role === "user" && (
                    <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))
            )}
            {sending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-600" />
                </div>
                <div className="bg-gray-100 rounded-lg px-4 py-3">
                  <Loader2 className="w-4 h-4 animate-spin text-gray-600" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="px-6 py-4 border-t">
            <form onSubmit={handleSendMessage} className="flex gap-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  documentId
                    ? "Ask a question about the policy..."
                    : "Upload a document first to start chatting"
                }
                disabled={!documentId || sending}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={!documentId || !inputMessage.trim() || sending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
