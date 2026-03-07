// frontend/src/pages/PolicySearchPage.jsx

import { useState, useCallback, useEffect } from "react";
import { Search, FileText, Loader, BookOpen } from "lucide-react";
import { policiesAPI } from "../services/api";
import { debounce } from "../utils/helpers";
import toast from "react-hot-toast";

export function PolicySearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [readiness, setReadiness] = useState(null);

  useEffect(() => {
    const loadReadiness = async () => {
      try {
        const response = await policiesAPI.readiness();
        setReadiness(response.data || null);
      } catch {
        setReadiness(null);
      }
    };

    loadReadiness();
  }, []);

  const performSearch = useCallback(
    debounce(async (searchQuery) => {
      if (!searchQuery.trim()) {
        setResults([]);
        setSearched(false);
        return;
      }

      setLoading(true);
      try {
        const response = await policiesAPI.search(searchQuery, null, 20);
        setResults(response.data.results);
        setReadiness(response.data.readiness || response.data.diagnostics || readiness);
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
    performSearch(value);
  };

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
    performSearch(suggestion);
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
        <div className="relative">
          <Search className="absolute left-3 sm:left-4 top-1/2 -translate-y-1/2 w-5 h-5 sm:w-6 sm:h-6 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={handleQueryChange}
            placeholder="Search for coverage, exclusions, or specific conditions..."
            className="w-full pl-10 sm:pl-12 pr-10 sm:pr-4 py-3 sm:py-4 text-base sm:text-lg border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {loading && (
            <Loader className="absolute right-3 sm:right-4 top-1/2 -translate-y-1/2 w-5 h-5 sm:w-6 sm:h-6 text-primary-600 animate-spin" />
          )}
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
            <p className="text-sm font-medium text-amber-800">Search readiness issue detected</p>
            <p className="mt-1 text-xs text-amber-700">
              mode: {readiness.mode || "unknown"} • db embeddings: {readiness.embedding_rows_in_db ?? 0} •
              faiss index: {readiness.faiss_index_exists ? "yes" : "no"}
            </p>
          </div>
        )}
      </div>

      {/* Results - Responsive */}
      {searched && (
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
