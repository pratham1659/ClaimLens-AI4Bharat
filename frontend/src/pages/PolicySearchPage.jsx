// frontend/src/pages/PolicySearchPage.jsx

import { useState, useCallback, useEffect, useRef } from "react";
import {
  Search,
  FileText,
  Loader,
  BookOpen,
  ChevronDown,
  Check,
} from "lucide-react";
import { policiesAPI } from "../services/api";
import { debounce } from "../utils/helpers";
import toast from "react-hot-toast";

export function PolicySearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [readiness, setReadiness] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [showDocDropdown, setShowDocDropdown] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDocDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        // Load readiness and documents in parallel
        const [readinessRes, docsRes] = await Promise.all([
          policiesAPI.readiness(),
          policiesAPI.list(),
        ]);
        setReadiness(readinessRes.data || null);
        // Deduplicate documents by filename - keep only unique filenames
        const allDocs = docsRes.data || [];
        const uniqueDocs = allDocs.reduce((acc, doc) => {
          if (!acc.find((d) => d.filename === doc.filename)) {
            acc.push(doc);
          }
          return acc;
        }, []);
        setDocuments(uniqueDocs);
      } catch {
        setReadiness(null);
      }
    };

    loadInitialData();
  }, []);

  const performSearch = useCallback(
    debounce(async (searchQuery, documentId) => {
      if (!searchQuery.trim()) {
        setResults([]);
        setSearched(false);
        return;
      }

      setLoading(true);
      try {
        // Pass document_ids as array if selected, null for all
        const docIds = documentId ? [documentId] : null;
        const response = await policiesAPI.search(searchQuery, docIds, 20);
        setResults(response.data.results);
        setReadiness(
          response.data.readiness || response.data.diagnostics || readiness,
        );
        setSearched(true);
      } catch (error) {
        const detailPayload = error?.response?.data?.detail;
        const detailMessage =
          typeof detailPayload === "string"
            ? detailPayload
            : detailPayload?.message;
        const readinessPayload =
          error?.response?.data?.readiness ||
          (typeof detailPayload === "object" ? detailPayload?.readiness : null);
        if (readinessPayload) {
          setReadiness(readinessPayload);
        }
        const detail =
          detailMessage ||
          error?.response?.data?.hint ||
          error?.userMessage ||
          "Search failed";
        toast.error(detail);
      } finally {
        setLoading(false);
      }
    }, 500),
    [],
  );

  const handleQueryChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    performSearch(value, selectedDocument?.id);
  };

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
    performSearch(suggestion, selectedDocument?.id);
  };

  const handleDocumentSelect = (doc) => {
    setSelectedDocument(doc);
    setShowDocDropdown(false);
    // Re-search with new document filter if there's a query
    if (query.trim()) {
      performSearch(query, doc?.id);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header - Responsive */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
          Policy Search
        </h1>
        <p className="text-sm sm:text-base text-gray-600 mt-1">
          Search across your insurance policy documents using natural language
        </p>
      </div>

      {/* Search Box - Responsive */}
      <div className="card p-4 sm:p-6">
        {/* Document Filter Dropdown */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Filter by Document
          </label>
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setShowDocDropdown(!showDocDropdown)}
              className="w-full sm:w-64 flex items-center justify-between px-4 py-2.5 bg-white border border-gray-300 rounded-lg hover:border-primary-400 transition-colors text-left"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <span className="text-sm truncate">
                  {selectedDocument
                    ? selectedDocument.filename
                    : "All Documents"}
                </span>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform ${showDocDropdown ? "rotate-180" : ""}`}
              />
            </button>

            {/* Dropdown Menu */}
            {showDocDropdown && (
              <div className="absolute top-full left-0 right-0 sm:right-auto sm:w-64 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-60 overflow-y-auto">
                {/* All Documents Option */}
                <button
                  onClick={() => handleDocumentSelect(null)}
                  className={`w-full px-4 py-2.5 flex items-center justify-between hover:bg-gray-50 transition-colors text-left ${
                    !selectedDocument ? "bg-primary-50" : ""
                  }`}
                >
                  <span className="text-sm font-medium text-gray-700">
                    All Documents
                  </span>
                  {!selectedDocument && (
                    <Check className="w-4 h-4 text-primary-600" />
                  )}
                </button>

                {/* Document Options */}
                {documents.length > 0 ? (
                  documents.map((doc) => (
                    <button
                      key={doc.id}
                      onClick={() => handleDocumentSelect(doc)}
                      className={`w-full px-4 py-2.5 flex items-center justify-between hover:bg-gray-50 transition-colors text-left ${
                        selectedDocument?.id === doc.id ? "bg-primary-50" : ""
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="w-4 h-4 text-primary-500 flex-shrink-0" />
                        <span className="text-sm truncate">{doc.filename}</span>
                      </div>
                      {selectedDocument?.id === doc.id && (
                        <Check className="w-4 h-4 text-primary-600 flex-shrink-0" />
                      )}
                    </button>
                  ))
                ) : (
                  <div className="px-4 py-3 text-sm text-gray-500 text-center">
                    No documents available
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="relative">
          <Search className="absolute left-3 sm:left-4 top-1/2 -translate-y-1/2 w-5 h-5 sm:w-6 sm:h-6 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={handleQueryChange}
            placeholder="Search for coverage, exclusions, or specific conditions..."
            className="w-full pl-10 sm:pl-12 pr-10 sm:pr-4 py-3 sm:py-4 text-base sm:text-lg border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Suggestions - Responsive scroll on mobile */}
        <div className="mt-3 sm:mt-4 flex items-start gap-2">
          <span className="text-xs sm:text-sm text-gray-500 flex-shrink-0 pt-1">
            Try:
          </span>
          <div className="flex flex-wrap gap-2 overflow-x-auto pb-1 -mx-1 px-1 sm:mx-0 sm:px-0">
            {[
              "pre-existing conditions",
              "emergency coverage",
              "prescription drugs",
              "mental health benefits",
            ].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => handleSuggestionClick(suggestion)}
                className="px-2.5 sm:px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs sm:text-sm hover:bg-gray-200 transition-colors whitespace-nowrap touch-manipulation"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>

        {readiness && !readiness.ready_for_policy_search && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <p className="text-sm font-medium text-amber-800">
              Search readiness issue detected
            </p>
            <p className="mt-1 text-xs text-amber-700">
              mode: {readiness.mode || "unknown"} • db embeddings:{" "}
              {readiness.embedding_rows_in_db ?? 0} • faiss index:{" "}
              {readiness.faiss_index_exists ? "yes" : "no"}
            </p>
          </div>
        )}
      </div>

      {/* Loading State - Below Search */}
      {loading && (
        <div className="card p-8 sm:p-12">
          <div className="flex flex-col items-center justify-center">
            <div className="w-12 h-12 sm:w-16 sm:h-16 bg-primary-100 rounded-full flex items-center justify-center mb-4">
              <Loader className="w-6 h-6 sm:w-8 sm:h-8 text-primary-600 animate-spin" />
            </div>
            <h3 className="text-base sm:text-lg font-medium text-gray-900 mb-1">
              Searching...
            </h3>
            <p className="text-sm text-gray-500">
              Finding relevant policy clauses
            </p>
          </div>
        </div>
      )}

      {/* Results - Responsive */}
      {searched && !loading && (
        <div className="space-y-3 sm:space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900">
              {results.length} Results Found
            </h2>
          </div>

          {results.length === 0 ? (
            <div className="card p-8 sm:p-12 text-center">
              <BookOpen className="w-10 h-10 sm:w-12 sm:h-12 text-gray-400 mx-auto" />
              <h3 className="mt-3 sm:mt-4 text-base sm:text-lg font-medium text-gray-900">
                No matching clauses found
              </h3>
              <p className="mt-2 text-sm sm:text-base text-gray-500">
                Try different keywords or phrases
              </p>
            </div>
          ) : (
            <div className="space-y-3 sm:space-y-4">
              {results.map((result, index) => (
                <div
                  key={index}
                  className="card p-4 sm:p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start gap-3 sm:gap-4">
                    <div className="w-8 h-8 sm:w-10 sm:h-10 bg-primary-50 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileText className="w-4 h-4 sm:w-5 sm:h-5 text-primary-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-2 mb-2">
                        <span className="text-xs sm:text-sm text-gray-500">
                          Chunk #{result.chunk_index + 1}
                        </span>
                        <span className="text-xs sm:text-sm font-medium text-primary-600">
                          {Math.round(result.relevance_score * 100)}% match
                        </span>
                      </div>
                      <p className="text-sm sm:text-base text-gray-700 whitespace-pre-wrap break-words">
                        {highlightText(result.content, query)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty State - Responsive */}
      {!searched && !loading && (
        <div className="card p-8 sm:p-12 text-center">
          <Search className="w-12 h-12 sm:w-16 sm:h-16 text-gray-300 mx-auto" />
          <h3 className="mt-3 sm:mt-4 text-base sm:text-lg font-medium text-gray-900">
            Search Your Policies
          </h3>
          <p className="mt-2 text-sm sm:text-base text-gray-500 max-w-md mx-auto">
            Enter a query above to search through all your uploaded insurance
            policy documents using AI-powered semantic search.
          </p>
        </div>
      )}
    </div>
  );
}

// Helper function to highlight matching text
function highlightText(text, query) {
  if (!query.trim()) return text;

  const words = query.toLowerCase().split(/\s+/);
  let result = text;

  words.forEach((word) => {
    if (word.length > 2) {
      const regex = new RegExp(`(${word})`, "gi");
      result = result.replace(
        regex,
        '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>',
      );
    }
  });

  return <span dangerouslySetInnerHTML={{ __html: result }} />;
}
