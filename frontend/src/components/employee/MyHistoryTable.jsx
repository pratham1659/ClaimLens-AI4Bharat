import React from "react";
import Table from "../common/Table";
import Badge from "../common/Badge";
import { formatDateTime } from "../../utils/formatters";

const MyHistoryTable = ({ auditLogs, loading }) => {
  const getActionBadgeVariant = (action) => {
    const variants = {
      APPLY: "info",
      UPDATE: "primary",
      APPROVE: "success",
      REJECT: "danger",
      CANCEL: "warning",
      ADJUST: "primary",
      ISSUE: "success",
      BALANCE_ADJUST: "primary",
      FY_LAPSE: "warning",
      FY_CARRYFORWARD: "info",
      SYSTEM_ACCRUAL: "info",
    };
    return variants[action] || "default";
  };

  const getActionLabel = (action) => {
    const labels = {
      APPLY: "Applied",
      UPDATE: "Updated",
      APPROVE: "Approved",
      REJECT: "Rejected",
      CANCEL: "Cancelled",
      ISSUE: "Issued",
      ADJUST: "Adjusted",
      BALANCE_ADJUST: "Balance Adjusted",
      FY_LAPSE: "FY Lapsed",
      FY_CARRYFORWARD: "Carried Forward",
      SYSTEM_ACCRUAL: "Monthly Accrual",
    };
    return labels[action] || action;
  };

  const renderDetails = (row) => {
    const { details, audit_metadata, action, leave_type_name } = row;

    if (!details && !audit_metadata) {
      return (
        <span className="text-gray-400 text-sm">No details available</span>
      );
    }

    // For SYSTEM_ACCRUAL actions, show month information
    const isAccrual = action === "SYSTEM_ACCRUAL";
    const isUpdate = action === "UPDATE";
    const metadata = audit_metadata || {};

    // Debug: Log metadata for UPDATE actions
    if (isUpdate) {
      console.log("UPDATE action metadata:", metadata);
      console.log("Leave type:", leave_type_name);
    }

    // Check if it's Work From Home - skip balance/change display for WFH
    const isWorkFromHome = leave_type_name === "Work From Home";

    return (
      <div className="space-y-1 text-sm">
        {details?.leave_type && (
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-700">Leave Type:</span>
            <Badge variant="info">{details.leave_type}</Badge>
          </div>
        )}

        {/* Show month for accrual entries */}
        {isAccrual && metadata.month_name && (
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-700">Month:</span>
            <Badge variant="info">
              {metadata.month_name} {metadata.year}
            </Badge>
          </div>
        )}

        {/* Show accrual amount for accrual entries */}
        {isAccrual && metadata.accrual_amount && (
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-700">Accrued:</span>
            <span className="font-semibold text-green-600">
              +{metadata.accrual_amount} days
            </span>
          </div>
        )}

        {/* Show update details - what changed (check for presence of old/new data) */}
        {isUpdate && (metadata.old_start_date || metadata.old_end_date) && (
          <div className="space-y-1 bg-blue-50 p-3 rounded border border-blue-200">
            <div className="font-medium text-blue-900 text-sm mb-2 flex items-center">
              <span className="mr-2">📝</span> Changes Made:
            </div>
            {metadata.old_start_date &&
              metadata.new_start_date &&
              metadata.old_start_date !== metadata.new_start_date && (
                <div className="flex items-center space-x-2 ml-4">
                  <span className="font-medium text-gray-700 text-xs">
                    Start Date:
                  </span>
                  <span className="text-red-600 line-through text-xs bg-red-50 px-2 py-0.5 rounded">
                    {new Date(metadata.old_start_date).toLocaleDateString()}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="text-green-600 font-semibold text-xs bg-green-50 px-2 py-0.5 rounded">
                    {new Date(metadata.new_start_date).toLocaleDateString()}
                  </span>
                </div>
              )}
            {metadata.old_end_date &&
              metadata.new_end_date &&
              metadata.old_end_date !== metadata.new_end_date && (
                <div className="flex items-center space-x-2 ml-4">
                  <span className="font-medium text-gray-700 text-xs">
                    End Date:
                  </span>
                  <span className="text-red-600 line-through text-xs bg-red-50 px-2 py-0.5 rounded">
                    {new Date(metadata.old_end_date).toLocaleDateString()}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="text-green-600 font-semibold text-xs bg-green-50 px-2 py-0.5 rounded">
                    {new Date(metadata.new_end_date).toLocaleDateString()}
                  </span>
                </div>
              )}
            {metadata.old_total_days != null &&
              metadata.new_total_days != null &&
              metadata.old_total_days !== metadata.new_total_days && (
                <div className="flex items-center space-x-2 ml-4">
                  <span className="font-medium text-gray-700 text-xs">
                    Total Days:
                  </span>
                  <span className="text-red-600 line-through text-xs bg-red-50 px-2 py-0.5 rounded">
                    {metadata.old_total_days} days
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="text-green-600 font-semibold text-xs bg-green-50 px-2 py-0.5 rounded">
                    {metadata.new_total_days} days
                  </span>
                </div>
              )}
          </div>
        )}

        {/* Show reason update */}
        {isUpdate &&
          metadata.old_reason != null &&
          metadata.new_reason != null &&
          metadata.old_reason !== metadata.new_reason && (
            <div className="space-y-1 bg-amber-50 p-3 rounded border border-amber-200 mt-1">
              <div className="font-medium text-amber-900 text-sm mb-2 flex items-center">
                <span className="mr-2">💬</span> Reason Updated:
              </div>
              <div className="flex flex-col space-y-2 ml-4">
                <div>
                  <span className="font-medium text-gray-700 text-xs">
                    Previous:
                  </span>
                  <p className="text-red-600 line-through text-xs italic mt-1 bg-red-50 p-2 rounded">
                    {metadata.old_reason || "No reason provided"}
                  </p>
                </div>
                <div>
                  <span className="font-medium text-gray-700 text-xs">
                    Current:
                  </span>
                  <p className="text-green-600 font-semibold text-xs italic mt-1 bg-green-50 p-2 rounded">
                    {metadata.new_reason || "No reason provided"}
                  </p>
                </div>
              </div>
            </div>
          )}

        {/* Fallback for older UPDATE entries without detailed metadata */}
        {isUpdate &&
          !metadata.old_start_date &&
          !metadata.old_end_date &&
          metadata.start_date && (
            <div className="bg-gray-50 p-2 rounded border border-gray-200">
              <div className="font-medium text-gray-700 text-sm flex items-center">
                <span className="mr-2">ℹ️</span> Leave request was updated
              </div>
              <div className="text-xs text-gray-600 mt-1 ml-6">
                Current dates:{" "}
                {new Date(metadata.start_date).toLocaleDateString()} -{" "}
                {new Date(metadata.end_date).toLocaleDateString()}
              </div>
            </div>
          )}

        {details?.status_change && (
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-700">Status:</span>
            <span className="text-gray-600">{details.status_change}</span>
          </div>
        )}

        {/* Show balance before/after for balance changes (skip for Work From Home) */}
        {!isWorkFromHome &&
          row.balance_before !== null &&
          row.balance_after !== null && (
            <div className="flex items-center space-x-2">
              <span className="font-medium text-gray-700">Balance:</span>
              <span className="text-gray-600">
                {parseFloat(row.balance_before).toFixed(1)} →{" "}
                {parseFloat(row.balance_after).toFixed(1)} days
              </span>
            </div>
          )}

        {/* Show balance change (skip for Work From Home) */}
        {!isWorkFromHome && details?.balance_change && (
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-700">Change:</span>
            <span className="text-gray-600">{details.balance_change} days</span>
          </div>
        )}

        {details?.days_affected !== null &&
          details?.days_affected !== undefined && (
            <div className="flex items-center space-x-2">
              <span className="font-medium text-gray-700">Days:</span>
              <span
                className={`font-semibold ${
                  // For Work From Home, show in green when approved, blue otherwise
                  isWorkFromHome
                    ? action === "APPROVE"
                      ? "text-green-600"
                      : "text-blue-600"
                    : // For CANCEL and REJECT actions, show as green (days freed up/not used)
                    action === "CANCEL" || action === "REJECT"
                    ? "text-green-600"
                    : details.days_affected > 0
                    ? "text-red-600"
                    : "text-green-600"
                }`}
              >
                {/* For Work From Home, show different text based on action */}
                {isWorkFromHome
                  ? action === "APPROVE"
                    ? `${Math.abs(details.days_affected)} days taken for WFH`
                    : `${Math.abs(details.days_affected)} days`
                  : /* For CANCEL and REJECT, show as positive since days are freed up/not used */
                  action === "CANCEL" || action === "REJECT"
                  ? `${Math.abs(details.days_affected)} days (not used)`
                  : `${details.days_affected > 0 ? "-" : "+"}${Math.abs(
                      details.days_affected
                    )}`}
              </span>
            </div>
          )}

        {(details?.reason || row.reason) && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <span className="font-medium text-gray-700 block mb-1">
              Reason:
            </span>
            <p className="text-gray-600 text-xs italic bg-gray-50 p-2 rounded">
              {details?.reason || row.reason}
            </p>
          </div>
        )}
      </div>
    );
  };

  const columns = [
    {
      header: "Date & Time",
      accessor: "created_at",
      render: (row) => (
        <div className="text-sm">
          <div className="font-medium text-gray-900">
            {new Date(row.created_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </div>
          <div className="text-xs text-gray-500">
            {new Date(row.created_at).toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
      ),
    },
    {
      header: "Action",
      accessor: "action",
      render: (row) => (
        <div className="flex flex-col items-start space-y-1">
          <Badge variant={getActionBadgeVariant(row.action)}>
            {getActionLabel(row.action)}
          </Badge>
          {row.leave_type_name && (
            <span className="text-xs text-gray-500">{row.leave_type_name}</span>
          )}
        </div>
      ),
    },
    {
      header: "Details",
      accessor: "details",
      render: renderDetails,
    },
  ];

  return (
    <Table
      columns={columns}
      data={auditLogs}
      loading={loading}
      emptyMessage="No activity history found. Your leave applications and updates will appear here."
    />
  );
};

export default MyHistoryTable;
