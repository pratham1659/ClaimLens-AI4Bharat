import React, { useState, useEffect } from "react";
import Card from "../common/Card";
import Alert from "../common/Alert";
import Table from "../common/Table";
import { accrualAPI } from "../../api/accrual";

const AccrualSummary = () => {
  const [accrualHistory, setAccrualHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  useEffect(() => {
    fetchAccrualHistory();
  }, [selectedYear]);

  const fetchAccrualHistory = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await accrualAPI.getAccrualHistory(selectedYear);
      console.log("[AccrualSummary] Accrual History Response:", response);

      const history = response?.data || [];
      setAccrualHistory(Array.isArray(history) ? history : []);
    } catch (err) {
      console.error("[AccrualSummary] Error fetching accrual history:", err);
      setError("Failed to fetch accrual history");
    } finally {
      setLoading(false);
    }
  };

  // Calculate summary statistics
  const totalCredited = accrualHistory.reduce(
    (sum, item) => sum + (item.days_credited || 0),
    0
  );

  const leaveTypeBreakdown = accrualHistory.reduce((acc, item) => {
    const typeName = item.leave_type_name;
    if (!acc[typeName]) {
      acc[typeName] = 0;
    }
    acc[typeName] += item.days_credited || 0;
    return acc;
  }, {});

  // Generate year options (current year and previous 2 years)
  const currentYear = new Date().getFullYear();
  const yearOptions = [currentYear, currentYear - 1, currentYear - 2];

  // Table columns
  const columns = [
    {
      accessor: "accrual_date",
      header: "Date",
      render: (row) =>
        new Date(row.accrual_date).toLocaleDateString("en-IN", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        }),
    },
    {
      accessor: "leave_type_name",
      header: "Leave Type",
      render: (row) => (
        <span className="font-medium text-gray-900">{row.leave_type_name}</span>
      ),
    },
    {
      accessor: "days_credited",
      header: "Days Credited",
      render: (row) => (
        <span className="font-semibold text-green-600">
          +{Number(row.days_credited || 0).toFixed(1)}
        </span>
      ),
    },
    {
      accessor: "balance_before",
      header: "Previous Balance",
      render: (row) => (
        <span className="text-gray-600">
          {Number(row.balance_before || 0).toFixed(1)}
        </span>
      ),
    },
    {
      accessor: "balance_after",
      header: "Current Balance",
      render: (row) => (
        <span className="font-semibold text-blue-600">
          {Number(row.balance_after || 0).toFixed(1)}
        </span>
      ),
    },
    {
      accessor: "reason",
      header: "Description",
      render: (row) => (
        <span className="text-sm text-gray-500">{row.reason || "-"}</span>
      ),
    },
  ];

  if (loading) {
    return (
      <Card title="Accrual Credits History">
        <div className="text-center py-8">
          <p className="text-gray-500">Loading...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Accrual Credits History">
        <Alert type="error" message={error} />
      </Card>
    );
  }

  return (
    <Card
      title="Accrual Credits History"
      subtitle="View all accrual credits received for your leave balance"
    >
      <div className="space-y-6">
        {/* Year Filter */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">
              Financial Year:
            </label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {yearOptions.map((year) => (
                <option key={year} value={year}>
                  FY {year}-{year + 1}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Summary Stats */}
        {accrualHistory.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
              <p className="text-sm text-green-700 font-medium">
                Total Credits Received
              </p>
              <p className="text-3xl font-bold text-green-900 mt-1">
                {totalCredited.toFixed(1)} days
              </p>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700 font-medium">
                Total Transactions
              </p>
              <p className="text-3xl font-bold text-blue-900 mt-1">
                {accrualHistory.length}
              </p>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
              <p className="text-sm text-purple-700 font-medium">Leave Types</p>
              <div className="mt-1 space-y-1">
                {Object.entries(leaveTypeBreakdown).map(([type, days]) => (
                  <div key={type} className="flex justify-between text-sm">
                    <span className="text-purple-900 font-medium">{type}:</span>
                    <span className="text-purple-700 font-bold">
                      {Number(days).toFixed(1)} days
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Accrual History Table */}
        {accrualHistory.length === 0 ? (
          <Alert
            type="info"
            message={`No accrual credits found for FY ${selectedYear}-${
              selectedYear + 1
            }. Credits are typically added monthly when accrual processing is run.`}
          />
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {/* Table Header */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
              <h3 className="text-lg font-semibold text-white">
                Accrual Credit Transactions
              </h3>
              <p className="text-sm text-blue-100 mt-1">
                Showing all leave credits received for FY {selectedYear}-
                {selectedYear + 1}
              </p>
            </div>

            {/* Table Content */}
            <div className="overflow-x-auto">
              <Table
                columns={columns}
                data={accrualHistory}
                emptyMessage="No accrual history available"
              />
            </div>
          </div>
        )}

        {/* Info Note */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <svg
              className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="text-sm text-blue-800">
              <p className="font-semibold mb-1">About Accrual Credits:</p>
              <ul className="list-disc list-inside space-y-1 text-blue-700">
                <li>
                  Leave credits are automatically added to your balance each
                  month
                </li>
                <li>Casual Leave: 1.5 days per month (18 days per year)</li>
                <li>Sick Leave: 1.0 day per month (12 days per year)</li>
                <li>Credits are processed by admin at the end of each month</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default AccrualSummary;
