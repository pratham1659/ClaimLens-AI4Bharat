// frontend/src/pages/DashboardPage.jsx


import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  CheckCircle,
  Clock,
  AlertTriangle,
  Plus,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import { useClaims } from "../hooks/useClaims";
import { ClaimCard } from "../components/claims/ClaimCard";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { CardSkeleton } from "../components/common/Skeleton";

export function DashboardPage() {
  const { claims, loading, pagination, fetchClaims, deleteClaim } = useClaims();
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    analyzed: 0,
    failed: 0,
  });

  useEffect(() => {
    fetchClaims({ page: 1, page_size: 5 });
  }, [fetchClaims]);

  useEffect(() => {
    // Calculate stats from claims
    const newStats = {
      total: pagination.total,
      pending: claims.filter((c) => c.status === "pending").length,
      analyzed: claims.filter((c) => c.status === "analyzed").length,
      failed: claims.filter((c) => c.status === "failed").length,
    };
    setStats(newStats);
  }, [claims, pagination.total]);

  const statCards = [
    {
      label: "Total Claims",
      value: stats.total,
      icon: FileText,
      color: "bg-primary-500",
      textColor: "text-primary-600",
    },
    {
      label: "Analyzed",
      value: stats.analyzed,
      icon: CheckCircle,
      color: "bg-success-500",
      textColor: "text-success-600",
    },
    {
      label: "Pending",
      value: stats.pending,
      icon: Clock,
      color: "bg-warning-500",
      textColor: "text-warning-600",
    },
    {
      label: "Failed",
      value: stats.failed,
      icon: AlertTriangle,
      color: "bg-danger-500",
      textColor: "text-danger-600",
    },
  ];

  return (
    <div className="space-y-4 sm:space-y-6 lg:space-y-8">
      {/* Header - Responsive */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
            Dashboard
          </h1>
          <p className="text-sm sm:text-base text-gray-600 mt-1">
            Overview of your insurance claim compliance
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

      {/* Stats Grid - Responsive: 2 cols on mobile, 4 on desktop */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6">
        {statCards.map((stat) => (
          <div key={stat.label} className="card p-3 sm:p-4 lg:p-6">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
              <div className={`p-2 sm:p-3 rounded-lg ${stat.color} w-fit`}>
                <stat.icon className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-xs sm:text-sm text-gray-600 truncate">
                  {stat.label}
                </p>
                <p className="text-xl sm:text-2xl font-bold text-gray-900">
                  {stat.value}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Claims - Responsive */}
      <div className="card overflow-hidden">
        <div className="p-4 sm:p-6 border-b flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <h2 className="text-base sm:text-lg font-semibold text-gray-900">
            Recent Claims
          </h2>
          <Link
            to="/claims"
            className="text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1 text-sm touch-manipulation"
          >
            View all
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="p-4 sm:p-6">
          {loading ? (
            <div className="space-y-3 sm:space-y-4">
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : claims.length === 0 ? (
            <div className="text-center py-8 sm:py-12">
              <FileText className="w-10 h-10 sm:w-12 sm:h-12 text-gray-400 mx-auto" />
              <p className="mt-3 sm:mt-4 text-sm sm:text-base text-gray-600">
                No claims yet
              </p>
              <Link
                to="/claims/new"
                className="btn-primary mt-3 sm:mt-4 inline-flex touch-manipulation"
              >
                Create your first claim
              </Link>
            </div>
          ) : (
            <div className="space-y-3 sm:space-y-4">
              {claims.map((claim) => (
                <ClaimCard
                  key={claim.id}
                  claim={claim}
                  onDelete={deleteClaim}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
