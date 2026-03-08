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
  Shield,
  Upload,
  Search,
  MessageSquare,
  Zap,
  Target,
  FileCheck,
  Brain,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { useClaims } from "../hooks/useClaims";
import { ClaimCard } from "../components/claims/ClaimCard";
import { CardSkeleton } from "../components/common/Skeleton";
import { useAuth } from "../context/AuthContext";

export function DashboardPage() {
  const { claims, loading, pagination, fetchClaims, deleteClaim } = useClaims();
  const { user } = useAuth();
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    analyzed: 0,
    failed: 0,
  });
  const [showWelcome, setShowWelcome] = useState(true);

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

  const features = [
    {
      icon: Upload,
      title: "Upload Documents",
      description:
        "Upload discharge summaries and insurance policies securely to our platform.",
      color: "bg-blue-500",
    },
    {
      icon: Brain,
      title: "AI-Powered Analysis",
      description:
        "Our AI analyzes your documents against policy clauses for compliance.",
      color: "bg-purple-500",
    },
    {
      icon: FileCheck,
      title: "Compliance Reports",
      description:
        "Get detailed reports showing coverage, exclusions, and recommendations.",
      color: "bg-green-500",
    },
    {
      icon: MessageSquare,
      title: "Policy Chat",
      description:
        "Ask questions about your insurance policy and get instant answers.",
      color: "bg-orange-500",
    },
  ];

  const workflowSteps = [
    {
      step: 1,
      title: "Create a Claim",
      description:
        "Start by entering patient details and creating a new claim.",
      icon: Plus,
    },
    {
      step: 2,
      title: "Upload Documents",
      description:
        "Upload the discharge summary and insurance policy documents.",
      icon: Upload,
    },
    {
      step: 3,
      title: "Run Analysis",
      description: "Let our AI analyze the documents for policy compliance.",
      icon: Zap,
    },
    {
      step: 4,
      title: "Review Results",
      description:
        "Get detailed insights on coverage, risks, and recommendations.",
      icon: Target,
    },
  ];

  return (
    <div className="space-y-4 sm:space-y-6 lg:space-y-8">
      {/* Welcome Hero Section */}
      {showWelcome && (
        <div className="relative overflow-hidden bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 rounded-2xl p-6 sm:p-8 text-white">
          {/* Background Pattern */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full transform translate-x-1/2 -translate-y-1/2" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full transform -translate-x-1/2 translate-y-1/2" />
          </div>

          <div className="relative z-10">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-5 h-5 text-yellow-300" />
                  <span className="text-primary-200 text-sm font-medium">
                    Welcome to ClaimLens
                  </span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-bold mb-3">
                  Hello,{" "}
                  {user?.full_name || user?.email?.split("@")[0] || "there"}!
                </h1>
                <p className="text-primary-100 text-sm sm:text-base max-w-2xl mb-6">
                  ClaimLens is your AI-powered insurance claim compliance
                  assistant. Upload medical documents and insurance policies to
                  instantly analyze coverage, identify exclusions, and get
                  actionable recommendations.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Link
                    to="/claims/new"
                    className="inline-flex items-center gap-2 px-4 py-2.5 bg-white text-primary-700 rounded-lg font-medium hover:bg-primary-50 transition-colors shadow-lg"
                  >
                    <Plus className="w-5 h-5" />
                    Create New Claim
                  </Link>
                  <Link
                    to="/policy-chat"
                    className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary-500/30 text-white rounded-lg font-medium hover:bg-primary-500/40 transition-colors border border-primary-400/30"
                  >
                    <MessageSquare className="w-5 h-5" />
                    Chat with Policy
                  </Link>
                </div>
              </div>
              <button
                onClick={() => setShowWelcome(false)}
                className="text-primary-200 hover:text-white transition-colors p-1"
                title="Dismiss"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      )}

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

      {/* Features Section */}
      <div className="card p-4 sm:p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-primary-600" />
          <h2 className="text-base sm:text-lg font-semibold text-gray-900">
            What ClaimLens Can Do
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group p-4 rounded-xl bg-gray-50 hover:bg-gray-100 transition-all cursor-default"
            >
              <div
                className={`w-10 h-10 ${feature.color} rounded-lg flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}
              >
                <feature.icon className="w-5 h-5 text-white" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">
                {feature.title}
              </h3>
              <p className="text-sm text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How It Works Section */}
      <div className="card p-4 sm:p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-600" />
            <h2 className="text-base sm:text-lg font-semibold text-gray-900">
              How It Works
            </h2>
          </div>
          <Link
            to="/claims/new"
            className="text-sm text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
          >
            Get Started
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Workflow Steps */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {workflowSteps.map((step, index) => (
            <div key={step.step} className="relative">
              {/* Connector Line (hidden on mobile, shown on larger screens) */}
              {index < workflowSteps.length - 1 && (
                <div className="hidden lg:block absolute top-8 left-[calc(100%_-_1rem)] w-[calc(100%_-_2rem)] h-0.5 bg-gradient-to-r from-primary-300 to-primary-100" />
              )}

              <div className="relative p-4 rounded-xl border-2 border-gray-100 hover:border-primary-200 transition-colors bg-white">
                {/* Step Number Badge */}
                <div className="absolute -top-3 -left-2 w-7 h-7 bg-primary-600 rounded-full flex items-center justify-center text-white text-sm font-bold shadow-lg">
                  {step.step}
                </div>

                <div className="pt-2">
                  <div className="w-12 h-12 bg-primary-50 rounded-xl flex items-center justify-center mb-3">
                    <step.icon className="w-6 h-6 text-primary-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {step.title}
                  </h3>
                  <p className="text-sm text-gray-600">{step.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Call to Action */}
        <div className="mt-6 p-4 bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="font-semibold text-gray-900">
                Ready to analyze your first claim?
              </p>
              <p className="text-sm text-gray-600">
                It only takes a few minutes to get started.
              </p>
            </div>
          </div>
          <Link to="/claims/new" className="btn-primary whitespace-nowrap">
            <Plus className="w-5 h-5 mr-2" />
            Create Claim
          </Link>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          to="/claims/new"
          className="group card p-4 hover:shadow-lg transition-all border-2 border-transparent hover:border-primary-200"
        >
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center group-hover:bg-primary-200 transition-colors">
              <Plus className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 group-hover:text-primary-700 transition-colors">
                New Claim
              </h3>
              <p className="text-sm text-gray-500">
                Start analyzing a new claim
              </p>
            </div>
          </div>
        </Link>

        <Link
          to="/policy-chat"
          className="group card p-4 hover:shadow-lg transition-all border-2 border-transparent hover:border-orange-200"
        >
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center group-hover:bg-orange-200 transition-colors">
              <MessageSquare className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 group-hover:text-orange-700 transition-colors">
                Policy Chat
              </h3>
              <p className="text-sm text-gray-500">
                Ask questions about policies
              </p>
            </div>
          </div>
        </Link>

        <Link
          to="/policy-search"
          className="group card p-4 hover:shadow-lg transition-all border-2 border-transparent hover:border-green-200"
        >
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center group-hover:bg-green-200 transition-colors">
              <Search className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 group-hover:text-green-700 transition-colors">
                Policy Search
              </h3>
              <p className="text-sm text-gray-500">Search policy clauses</p>
            </div>
          </div>
        </Link>
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
        <div className="p-3 sm:p-4">
          {loading ? (
            <div className="space-y-2 sm:space-y-3">
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : claims.length === 0 ? (
            <div className="text-center py-6 sm:py-10">
              <FileText className="w-10 h-10 sm:w-12 sm:h-12 text-gray-400 mx-auto" />
              <p className="mt-2 sm:mt-3 text-sm sm:text-base text-gray-600">
                No claims yet
              </p>
              <Link
                to="/claims/new"
                className="btn-primary mt-2 sm:mt-3 inline-flex touch-manipulation"
              >
                Create your first claim
              </Link>
            </div>
          ) : (
            <div className="space-y-2 sm:space-y-3">
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
