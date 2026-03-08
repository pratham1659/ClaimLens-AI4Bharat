// frontend/src/pages/ClaimsListPage.jsx

import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  X,
  ChevronDown,
  Check,
} from "lucide-react";
import { useClaims } from "../hooks/useClaims";
import { ClaimCard } from "../components/claims/ClaimCard";
import { CardSkeleton } from "../components/common/Skeleton";

const statusOptions = [
  { value: "", label: "All Status", color: "bg-gray-100 text-gray-700" },
  {
    value: "pending",
    label: "Pending",
    color: "bg-warning-100 text-warning-700",
  },
  {
    value: "analyzed",
    label: "Analyzed",
    color: "bg-success-100 text-success-700",
  },
  { value: "failed", label: "Failed", color: "bg-danger-100 text-danger-700" },
];

export function ClaimsListPage() {
  const { claims, loading, pagination, fetchClaims, deleteClaim } = useClaims();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowStatusDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedStatus =
    statusOptions.find((opt) => opt.value === statusFilter) || statusOptions[0];

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

  const clearFilters = () => {
    setSearchQuery("");
    setStatusFilter("");
    setCurrentPage(1);
  };

  const hasActiveFilters = searchQuery || statusFilter;

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header - Responsive */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
            Claims
          </h1>
          <p className="text-sm sm:text-base text-gray-600 mt-1">
            Manage and track your insurance claims
          </p>
        </div>
        <Link
          to="/claims/new"
          className="btn-primary w-full sm:w-auto justify-center touch-manipulation"
        >
          <Plus className="w-5 h-5 mr-2" />
          New Claim
        </Link>
      </div>

      {/* Filters - Responsive */}
      <div className="card p-3 sm:p-4">
        {/* Desktop Filters */}
        <div className="hidden sm:flex flex-col md:flex-row gap-4">
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

          {/* Custom Status Filter Dropdown */}
          <div className="relative w-full md:w-48" ref={dropdownRef}>
            <button
              onClick={() => setShowStatusDropdown(!showStatusDropdown)}
              className="input w-full flex items-center justify-between cursor-pointer hover:border-primary-400 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-400" />
                <span
                  className={`text-sm px-2 py-0.5 rounded-full ${selectedStatus.color}`}
                >
                  {selectedStatus.label}
                </span>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-gray-400 transition-transform ${showStatusDropdown ? "rotate-180" : ""}`}
              />
            </button>

            {/* Dropdown Menu */}
            {showStatusDropdown && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 overflow-hidden">
                {statusOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => {
                      setStatusFilter(option.value);
                      setCurrentPage(1);
                      setShowStatusDropdown(false);
                    }}
                    className={`w-full px-3 py-2.5 flex items-center justify-between hover:bg-gray-50 transition-colors ${
                      statusFilter === option.value ? "bg-primary-50" : ""
                    }`}
                  >
                    <span
                      className={`text-sm px-2 py-0.5 rounded-full ${option.color}`}
                    >
                      {option.label}
                    </span>
                    {statusFilter === option.value && (
                      <Check className="w-4 h-4 text-primary-600" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {hasActiveFilters && (
            <button onClick={clearFilters} className="btn-secondary text-sm">
              <X className="w-4 h-4 mr-1" />
              Clear
            </button>
          )}
        </div>

        {/* Mobile Filters */}
        <div className="sm:hidden space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search claims..."
              className="input pl-10 pr-12"
            />
            <button
              onClick={() => setShowMobileFilters(!showMobileFilters)}
              className={`absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg touch-manipulation ${
                hasActiveFilters
                  ? "text-primary-600 bg-primary-50"
                  : "text-gray-400"
              }`}
            >
              <SlidersHorizontal className="w-5 h-5" />
            </button>
          </div>

          {/* Mobile Filter Dropdown */}
          {showMobileFilters && (
            <div className="p-3 bg-gray-50 rounded-lg space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Status
                </label>
                <div className="flex flex-wrap gap-2">
                  {statusOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setStatusFilter(option.value);
                        setCurrentPage(1);
                      }}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${option.color} ${
                        statusFilter === option.value
                          ? "ring-2 ring-primary-500 ring-offset-1"
                          : "opacity-70 hover:opacity-100"
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="btn-secondary w-full justify-center text-sm"
                >
                  <X className="w-4 h-4 mr-1" />
                  Clear Filters
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Claims List */}
      {loading ? (
        <div className="space-y-3 sm:space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : filteredClaims.length === 0 ? (
        <div className="card p-8 sm:p-12 text-center">
          <div className="w-14 h-14 sm:w-16 sm:h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
            <Search className="w-7 h-7 sm:w-8 sm:h-8 text-gray-400" />
          </div>
          <h3 className="mt-4 text-base sm:text-lg font-medium text-gray-900">
            No claims found
          </h3>
          <p className="mt-2 text-sm sm:text-base text-gray-500">
            {searchQuery || statusFilter
              ? "Try adjusting your filters"
              : "Create your first claim to get started"}
          </p>
          {!searchQuery && !statusFilter && (
            <Link
              to="/claims/new"
              className="btn-primary mt-4 inline-flex touch-manipulation"
            >
              Create Claim
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-3 sm:space-y-4">
          {filteredClaims.map((claim) => (
            <ClaimCard key={claim.id} claim={claim} onDelete={deleteClaim} />
          ))}
        </div>
      )}

      {/* Pagination - Responsive */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs sm:text-sm text-gray-600 text-center sm:text-left">
            Showing {(currentPage - 1) * pagination.pageSize + 1} to{" "}
            {Math.min(currentPage * pagination.pageSize, pagination.total)} of{" "}
            {pagination.total} claims
          </p>

          <div className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="btn-secondary p-2 touch-manipulation"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>

            {/* Show fewer page buttons on mobile */}
            <div className="hidden sm:flex items-center gap-2">
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
                    className={`w-10 h-10 rounded-lg font-medium transition-colors touch-manipulation ${
                      currentPage === pageNum
                        ? "bg-primary-600 text-white"
                        : "bg-white text-gray-700 hover:bg-gray-50 border"
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            {/* Mobile: Just show current page */}
            <div className="sm:hidden px-3 py-2 text-sm font-medium text-gray-700">
              {currentPage} / {totalPages}
            </div>

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="btn-secondary p-2 touch-manipulation"
              aria-label="Next page"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
