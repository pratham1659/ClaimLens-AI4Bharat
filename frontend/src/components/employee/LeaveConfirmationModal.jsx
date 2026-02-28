import React from "react";
import Modal from "../common/Modal";
import Button from "../common/Button";
import { formatDate } from "../../utils/formatters";

const LeaveConfirmationModal = ({
  isOpen,
  onClose,
  onConfirm,
  leaveData,
  loading,
}) => {
  if (!isOpen || !leaveData) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Confirm Leave Request"
      size="xl"
    >
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-4">
          {/* Left Column */}
          <div className="space-y-3">
            <div className="border-b border-gray-200 pb-2">
              <p className="text-xs text-gray-600 font-medium">Leave Type</p>
              <p className="text-base text-gray-900 font-semibold">
                {leaveData.leaveTypeName}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 border-b border-gray-200 pb-2">
              <div>
                <p className="text-xs text-gray-600 font-medium">Start Date</p>
                <p className="text-sm text-gray-900 font-semibold">
                  {formatDate(leaveData.start_date)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600 font-medium">End Date</p>
                <p className="text-sm text-gray-900 font-semibold">
                  {formatDate(leaveData.end_date)}
                </p>
              </div>
            </div>

            <div className="border-b border-gray-200 pb-2">
              <p className="text-xs text-gray-600 font-medium">Total Days</p>
              <p className="text-xl text-gray-900 font-bold">
                {leaveData.totalDays}{" "}
                {leaveData.totalDays === 1 ? "day" : "days"}
              </p>
            </div>

            {leaveData.balance ? (
              <>
                <div className="bg-green-50 border border-green-200 rounded-lg p-2">
                  <p className="text-xs text-green-800 font-medium mb-1">
                    Leave Balance
                  </p>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <p className="text-green-700">Total</p>
                      <p className="text-base font-bold text-green-900">
                        {Number(leaveData.balance.total_days).toFixed(1)}
                      </p>
                    </div>
                    <div>
                      <p className="text-green-700">Used</p>
                      <p className="text-base font-bold text-green-900">
                        {Number(leaveData.balance.used_days).toFixed(1)}
                      </p>
                    </div>
                    <div>
                      <p className="text-green-700">Remaining</p>
                      <p className="text-base font-bold text-green-900">
                        {Number(leaveData.balance.remaining_days).toFixed(1)}
                      </p>
                    </div>
                  </div>
                </div>

                {leaveData.totalDays <= leaveData.balance.remaining_days && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-2">
                    <p className="text-xs text-yellow-800 font-medium">
                      After Approval
                    </p>
                    <p className="text-sm text-yellow-900 font-semibold">
                      Remaining:{" "}
                      {(
                        leaveData.balance.remaining_days - leaveData.totalDays
                      ).toFixed(1)}{" "}
                      days
                    </p>
                  </div>
                )}
              </>
            ) : (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-2">
                <p className="text-xs text-purple-800 font-medium">
                  Work From Home
                </p>
                <p className="text-sm text-purple-900">
                  No balance required - subject to admin approval
                </p>
              </div>
            )}
          </div>

          {/* Right Column - Reason */}
          <div className="border-l border-gray-200 pl-4">
            <p className="text-xs text-gray-600 font-medium mb-2">Reason</p>
            <div className="bg-gray-50 rounded-lg p-3 h-full max-h-64 overflow-y-auto">
              <p className="text-sm text-gray-900 whitespace-pre-wrap">
                {leaveData.reason}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-sm text-amber-800">
            <strong>Note:</strong> Once submitted, your request will be sent for
            approval. Please ensure all information is correct before
            confirming.
          </p>
        </div>

        <div className="flex justify-end gap-3 pt-3 border-t border-gray-200">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onConfirm} loading={loading}>
            Confirm & Submit
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default LeaveConfirmationModal;
