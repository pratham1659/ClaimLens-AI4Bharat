// frontend/src/pages/PolicySearchPage.jsx
/**
 * Policy search page with semantic search.
 */

import { useState, useCallback } from "react";
import { Search, FileText, Loader, BookOpen } from "lucide-react";
import { policiesAPI } from "../services/api";
import { debounce } from "../utils/helpers";
import toast from "react-hot-toast";

export function PolicySearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

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
        setSearched(true);
      } catch (error) {
        toast.error("Search failed");
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Policy Search</h1>
        <p className="text-gray-600 mt-1">
          Search across your insurance policy documents using natural language
        </p>
      </div>

      {/* Search Box */}
      <div className="card p-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-6 h-6 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={handleQueryChange}
            placeholder="Search for coverage, exclusions, or specific conditions..."
            className="w-full pl-12 pr-4 py-4 text-lg border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {loading && (
            <Loader className="absolute right-4 top-1/2 -translate-y-1/2 w-6 h-6 text-primary-600 animate-spin" />
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-gray-500">Try:</span>
          {[
            "pre-existing conditions",
            "emergency coverage",
            "prescription drugs",
            "mental health benefits",
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => {
                setQuery(suggestion);
                performSearch(suggestion);
              }}
              className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {searched && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              {results.length} Results Found
            </h2>
          </div>

          {results.length === 0 ? (
            <div className="card p-12 text-center">
              <BookOpen className="w-12 h-12 text-gray-400 mx-auto" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">
                No matching clauses found
              </h3>
              <p className="mt-2 text-gray-500">
                Try different keywords or phrases
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result, index) => (
                <div
                  key={index}
                  className="card p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-primary-50 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-primary-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-500">
                          Chunk #{result.chunk_index + 1}
                        </span>
                        <span className="text-sm font-medium text-primary-600">
                          {Math.round(result.relevance_score * 100)}% match
                        </span>
                      </div>
                      <p className="text-gray-700 whitespace-pre-wrap">
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

      {/* Empty State */}
      {!searched && !loading && (
        <div className="card p-12 text-center">
          <Search className="w-16 h-16 text-gray-300 mx-auto" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">
            Search Your Policies
          </h3>
          <p className="mt-2 text-gray-500 max-w-md mx-auto">
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
