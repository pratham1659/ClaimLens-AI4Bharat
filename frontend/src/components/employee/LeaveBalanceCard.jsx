import React from "react";
import Card from "../common/Card";

const LeaveBalanceCard = ({ balances, wfhData, loading }) => {
  if (loading) {
    return (
      <Card title="Leave Balance">
        <div className="text-center py-8">
          <p className="text-gray-500">Loading...</p>
        </div>
      </Card>
    );
  }

  if (!balances || balances.length === 0) {
    return (
      <Card title="Leave Balance">
        <div className="text-center py-8">
          <p className="text-gray-500">No leave balance found</p>
        </div>
      </Card>
    );
  }

  // Get the year from the first balance or WFH data
  const year = balances[0]?.year || wfhData?.year || new Date().getFullYear();

  return (
    <Card title={`Leave Balance - Year ${year}`}>
      <div className="space-y-6">
        {/* Sick and Casual Leave Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {balances.map((balance) => {
            const usagePercentage =
              balance.total_days > 0
                ? (balance.used_days / balance.total_days) * 100
                : 0;

            return (
              <div
                key={balance.id}
                className="border border-gray-200 rounded-lg p-4 bg-white hover:shadow-md transition-shadow"
              >
                <h3 className="font-semibold text-gray-900 mb-3 text-center">
                  {balance.leave_type_name}
                </h3>

                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="flex flex-col items-center justify-center p-3 bg-blue-50 rounded-lg">
                    <p className="text-xs text-blue-700 font-medium">Total</p>
                    <p className="text-xl font-bold text-blue-900 mt-1">
                      {Number(balance.total_days).toFixed(1)}
                    </p>
                  </div>
                  <div className="flex flex-col items-center justify-center p-3 bg-orange-50 rounded-lg">
                    <p className="text-xs text-orange-700 font-medium">Used</p>
                    <p className="text-xl font-bold text-orange-900 mt-1">
                      {Number(balance.used_days).toFixed(1)}
                    </p>
                  </div>
                  <div className="flex flex-col items-center justify-center p-3 bg-green-50 rounded-lg">
                    <p className="text-xs text-green-700 font-medium">
                      Remaining
                    </p>
                    <p className="text-xl font-bold text-green-900 mt-1">
                      {Number(balance.remaining_days).toFixed(1)}
                    </p>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">Usage</span>
                    <span className="font-medium text-gray-900">
                      {usagePercentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        usagePercentage > 80
                          ? "bg-red-500"
                          : usagePercentage > 50
                          ? "bg-orange-500"
                          : "bg-green-500"
                      }`}
                      style={{ width: `${Math.min(usagePercentage, 100)}%` }}
                    ></div>
                  </div>
                </div>

                {balance.carry_forward_days > 0 && (
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-2 mt-3">
                    <p className="text-xs text-purple-700">
                      <strong>Carry Forward:</strong>{" "}
                      {Number(balance.carry_forward_days).toFixed(1)} days
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Work From Home Section - Full Width */}
        {wfhData && wfhData.monthly_usage && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gradient-to-br from-purple-50 to-indigo-50">
            <h3 className="font-semibold text-gray-900 mb-4 text-center text-lg">
              Work From Home
            </h3>

            {/* Monthly Usage Grid */}
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2 mb-4">
              {wfhData.monthly_usage.map((monthData, index) => (
                <div
                  key={index}
                  className={`flex flex-col items-center justify-center p-2 rounded-lg transition-all min-h-[80px] ${
                    monthData.days > 0
                      ? "bg-purple-100 border border-purple-300"
                      : "bg-white border border-gray-200"
                  }`}
                >
                  <p className="text-xs font-medium text-gray-700 mb-1 whitespace-nowrap">
                    {monthData.month}
                  </p>
                  <p
                    className={`text-base font-bold leading-tight ${
                      monthData.days > 0 ? "text-purple-900" : "text-gray-400"
                    }`}
                  >
                    {monthData.days.toFixed(1)}
                  </p>
                  <p className="text-[10px] text-gray-500 mt-0.5 whitespace-nowrap">
                    {monthData.days === 1 ? "day" : "days"}
                  </p>
                </div>
              ))}
            </div>

            {/* WFH Periods Section (replaces Total WFH Used) */}
            {wfhData.wfh_periods && wfhData.wfh_periods.length > 0 && (
              <div className="mt-4 pt-4 border-t border-purple-200">
                <h4 className="text-sm font-semibold text-gray-700 mb-3">
                  Work From Home Periods:
                </h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {wfhData.wfh_periods.map((period) => (
                    <div
                      key={period.id}
                      className="flex items-center justify-between p-2 bg-white border border-purple-200 rounded-lg hover:shadow-sm transition-shadow"
                    >
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <svg
                            className="w-4 h-4 text-purple-600"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                            />
                          </svg>
                          <span className="text-xs font-medium text-gray-900">
                            {new Date(period.start_date).toLocaleDateString(
                              "en-US",
                              {
                                month: "short",
                                day: "numeric",
                              }
                            )}
                            {period.start_date !== period.end_date && (
                              <>
                                {" "}
                                -{" "}
                                {new Date(period.end_date).toLocaleDateString(
                                  "en-US",
                                  {
                                    month: "short",
                                    day: "numeric",
                                  }
                                )}
                              </>
                            )}
                          </span>
                        </div>
                      </div>
                      <div className="ml-2 flex items-center">
                        <span className="text-xs font-bold text-purple-900 bg-purple-100 px-2 py-1 rounded-full">
                          {period.total_days.toFixed(1)}{" "}
                          {period.total_days === 1 ? "day" : "days"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};

export default LeaveBalanceCard;
