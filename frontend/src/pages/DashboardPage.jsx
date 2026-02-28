// frontend/src/pages/DashboardPage.jsx
/**
 * Dashboard page with overview statistics.
 */

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
    },
    {
      label: "Analyzed",
      value: stats.analyzed,
      icon: CheckCircle,
      color: "bg-success-500",
    },
    {
      label: "Pending",
      value: stats.pending,
      icon: Clock,
      color: "bg-warning-500",
    },
    {
      label: "Failed",
      value: stats.failed,
      icon: AlertTriangle,
      color: "bg-danger-500",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Overview of your insurance claim compliance
          </p>
        </div>
        <Link to="/claims/new" className="btn-primary">
          <Plus className="w-5 h-5 mr-2" />
          New Claim
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => (
          <div key={stat.label} className="card p-6">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-600">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Claims */}
      <div className="card">
        <div className="p-6 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Claims</h2>
          <Link
            to="/claims"
            className="text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
          >
            View all
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="p-6">
          {loading ? (
            <div className="space-y-4">
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : claims.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-gray-400 mx-auto" />
              <p className="mt-4 text-gray-600">No claims yet</p>
              <Link to="/claims/new" className="btn-primary mt-4">
                Create your first claim
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
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
