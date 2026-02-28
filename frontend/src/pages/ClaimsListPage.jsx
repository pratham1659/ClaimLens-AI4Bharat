// frontend/src/pages/ClaimsListPage.jsx
/**
 * Claims list page with filtering and pagination.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import { useClaims } from "../hooks/useClaims";
import { ClaimCard } from "../components/claims/ClaimCard";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { CardSkeleton } from "../components/common/Skeleton";

const statusOptions = [
  { value: "", label: "All Status" },
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "analyzed", label: "Analyzed" },
  { value: "failed", label: "Failed" },
];

export function ClaimsListPage() {
  const { claims, loading, pagination, fetchClaims, deleteClaim } = useClaims();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    fetchClaims({
      page: currentPage,
      page_size: 10,
      status: statusFilter || undefined,
    });
  }, [fetchClaims, currentPage, statusFilter]);

  const totalPages = Math.ceil(pagination.total / pagination.pageSize);

  const handlePageChange = (page) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const filteredClaims = claims.filter(
    (claim) =>
      claim.claim_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      claim.patient_name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Claims</h1>
          <p className="text-gray-600 mt-1">
            Manage and track your insurance claims
          </p>
        </div>
        <Link to="/claims/new" className="btn-primary">
          <Plus className="w-5 h-5 mr-2" />
          New Claim
        </Link>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search claims..."
              className="input pl-10"
            />
          </div>

          {/* Status Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="input pl-10 pr-8 appearance-none cursor-pointer"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Claims List */}
      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : filteredClaims.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
            <Search className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="mt-4 text-lg font-medium text-gray-900">
            No claims found
          </h3>
          <p className="mt-2 text-gray-500">
            {searchQuery || statusFilter
              ? "Try adjusting your filters"
              : "Create your first claim to get started"}
          </p>
          {!searchQuery && !statusFilter && (
            <Link to="/claims/new" className="btn-primary mt-4">
              Create Claim
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredClaims.map((claim) => (
            <ClaimCard key={claim.id} claim={claim} onDelete={deleteClaim} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Showing {(currentPage - 1) * pagination.pageSize + 1} to{" "}
            {Math.min(currentPage * pagination.pageSize, pagination.total)} of{" "}
            {pagination.total} claims
          </p>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="btn-secondary p-2"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>

            {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
              let pageNum;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`w-10 h-10 rounded-lg font-medium transition-colors ${
                    currentPage === pageNum
                      ? "bg-primary-600 text-white"
                      : "bg-white text-gray-700 hover:bg-gray-50 border"
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="btn-secondary p-2"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
