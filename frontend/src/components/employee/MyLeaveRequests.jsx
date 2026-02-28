import React, { useState, useEffect } from "react";
import Table from "../common/Table";
import Badge from "../common/Badge";
import Button from "../common/Button";
import ConfirmModal from "../common/ConfirmModal";
import Modal from "../common/Modal";
import Input from "../common/Input";
import { formatDate } from "../../utils/formatters";
import { LEAVE_STATUS_COLORS } from "../../utils/constants";
import { employeeAPI } from "../../api/employee";
import { useToast } from "../../hooks/useToast";
import { calculateDays } from "../../utils/validators";

const MyLeaveRequests = ({ requests, loading, onRequestCancelled }) => {
  const [cancellingId, setCancellingId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [editFormData, setEditFormData] = useState({
    leave_type_id: "",
    start_date: "",
    end_date: "",
    reason: "",
  });
  const [totalDays, setTotalDays] = useState(0);
  const [balances, setBalances] = useState([]);
  const toast = useToast();

  useEffect(() => {
    if (showEditModal && selectedRequest) {
      fetchBalance();
    }
  }, [showEditModal, selectedRequest]);

  useEffect(() => {
    if (editFormData.start_date && editFormData.end_date) {
      const days = calculateDays(
        editFormData.start_date,
        editFormData.end_date
      );
      setTotalDays(days);
    } else {
      setTotalDays(0);
    }
  }, [editFormData.start_date, editFormData.end_date]);

  const fetchBalance = async () => {
    try {
      const data = await employeeAPI.getMyLeaveBalance();
      const filteredBalances = data.filter(
        (balance) => balance.leave_type_name !== "Paid Leave"
      );
      setBalances(filteredBalances);
    } catch (err) {
      console.error("Failed to fetch balance:", err);
    }
  };

  const handleEditClick = (request) => {
    setSelectedRequest(request);
    setEditFormData({
      leave_type_id: request.leave_type_id.toString(),
      start_date: request.start_date,
      end_date: request.end_date,
      reason: request.reason,
    });
    setShowEditModal(true);
  };

  const handleEditChange = (e) => {
    setEditFormData({
      ...editFormData,
      [e.target.name]: e.target.value,
    });
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    if (!selectedRequest) return;

    setEditingId(selectedRequest.id);
    try {
      const updateData = {
        leave_type_id: parseInt(editFormData.leave_type_id),
        start_date: editFormData.start_date,
        end_date: editFormData.end_date,
        reason: editFormData.reason.trim(),
      };

      await employeeAPI.updateLeaveRequest(selectedRequest.id, updateData);
      toast.success("Leave request updated successfully");
      setShowEditModal(false);
      setSelectedRequest(null);
      if (onRequestCancelled) {
        onRequestCancelled();
      }
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Failed to update leave request"
      );
    } finally {
      setEditingId(null);
    }
  };

  const handleCancelClick = (request) => {
    setSelectedRequest(request);
    setShowCancelModal(true);
  };

  const handleCancelConfirm = async () => {
    if (!selectedRequest) return;

    setCancellingId(selectedRequest.id);
    try {
      await employeeAPI.cancelLeaveRequest(selectedRequest.id);
      toast.success("Leave request cancelled successfully");
      setShowCancelModal(false);
      setSelectedRequest(null);
      if (onRequestCancelled) {
        onRequestCancelled();
      }
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Failed to cancel leave request"
      );
    } finally {
      setCancellingId(null);
    }
  };

  const columns = [
    {
      header: "Leave Period",
      render: (row) => (
        <div className="w-[120px]">
          <p className="font-medium text-xs leading-tight">
            {formatDate(row.start_date)} - {formatDate(row.end_date)}
          </p>
          <p className="text-xs text-gray-500">{row.total_days} days</p>
        </div>
      ),
    },
    {
      header: "Type",
      accessor: "leave_type_name",
      render: (row) => (
        <div className="w-[80px] text-xs break-words">
          {row.leave_type_name}
        </div>
      ),
    },
    {
      header: "Reason",
      accessor: "reason",
      render: (row) => (
        <div className="max-w-[150px] min-w-[120px]">
          <p className="text-xs leading-tight break-words whitespace-normal overflow-hidden">
            {row.reason}
          </p>
        </div>
      ),
    },
    {
      header: "Applied",
      accessor: "created_at",
      render: (row) => (
        <div className="w-[75px] text-xs">{formatDate(row.created_at)}</div>
      ),
    },
    {
      header: "Status",
      accessor: "status",
      render: (row) => (
        <div className="w-[85px]">
          <Badge variant={LEAVE_STATUS_COLORS[row.status]}>{row.status}</Badge>
        </div>
      ),
    },
    {
      header: "Response",
      render: (row) => (
        <div className="text-xs w-[110px] break-words">
          {row.status === "APPROVED" && row.approver_name && (
            <div>
              <p className="text-green-600">
                ✓ Approved by {row.approver_name}
              </p>
              {row.approved_at && (
                <p className="text-xs text-gray-500">
                  {formatDate(row.approved_at)}
                </p>
              )}
            </div>
          )}
          {row.status === "REJECTED" && (
            <div>
              <p className="text-red-600">
                ✗ Rejected{row.approver_name && ` by ${row.approver_name}`}
              </p>
              {row.approved_at && (
                <p className="text-xs text-gray-500">
                  {formatDate(row.approved_at)}
                </p>
              )}
              {row.rejection_reason && (
                <p className="text-xs text-gray-600 mt-1">
                  {row.rejection_reason}
                </p>
              )}
            </div>
          )}
          {row.status === "PENDING" && (
            <p className="text-gray-500">Awaiting approval</p>
          )}
          {row.status === "CANCELLED" && (
            <p className="text-gray-500">Cancelled by you</p>
          )}
        </div>
      ),
    },
    {
      header: "Actions",
      render: (row) => (
        <div className="flex gap-2 w-[130px]">
          {row.status === "PENDING" && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleEditClick(row)}
                disabled={editingId === row.id}
                title="Edit leave request"
                className="px-3 py-1.5"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleCancelClick(row)}
                disabled={cancellingId === row.id}
                title="Cancel leave request"
                className="px-3 py-1.5 text-sm"
              >
                {cancellingId === row.id ? "..." : "Cancel"}
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <Table
        columns={columns}
        data={requests}
        loading={loading}
        emptyMessage="No leave requests found"
      />

      <ConfirmModal
        isOpen={showCancelModal}
        onClose={() => {
          setShowCancelModal(false);
          setSelectedRequest(null);
        }}
        onConfirm={handleCancelConfirm}
        title="Cancel Leave Request"
        message={
          selectedRequest ? (
            <div>
              <p>Are you sure you want to cancel this leave request?</p>
              <div className="mt-3 p-3 bg-gray-50 rounded">
                <p className="text-sm">
                  <strong>Period:</strong>{" "}
                  {formatDate(selectedRequest.start_date)} -{" "}
                  {formatDate(selectedRequest.end_date)}
                </p>
                <p className="text-sm">
                  <strong>Days:</strong> {selectedRequest.total_days}
                </p>
                <p className="text-sm">
                  <strong>Reason:</strong> {selectedRequest.reason}
                </p>
              </div>
            </div>
          ) : (
            "Are you sure you want to cancel this leave request?"
          )
        }
        confirmText="Yes, Cancel Request"
        confirmVariant="danger"
      />

      <Modal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedRequest(null);
        }}
        title="Edit Leave Request"
      >
        <form onSubmit={handleEditSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Leave Type <span className="text-red-500">*</span>
            </label>
            <select
              name="leave_type_id"
              value={editFormData.leave_type_id}
              onChange={handleEditChange}
              required
              className="input-field"
            >
              <option value="">Select leave type</option>
              {balances.map((balance) => (
                <option
                  key={balance.leave_type_id}
                  value={balance.leave_type_id}
                >
                  {balance.leave_type_name}
                  {balance.leave_type_name !== "Work From Home" &&
                    ` (Available: ${Number(balance.remaining_days).toFixed(
                      1
                    )} days)`}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Start Date"
              type="date"
              name="start_date"
              value={editFormData.start_date}
              onChange={handleEditChange}
              required
            />

            <Input
              label="End Date"
              type="date"
              name="end_date"
              value={editFormData.end_date}
              onChange={handleEditChange}
              required
              min={editFormData.start_date}
            />
          </div>

          {totalDays > 0 && (
            <div className="bg-green-50 border-2 border-green-200 rounded-lg p-3">
              <p className="text-sm font-medium text-green-800">
                Total Days: {totalDays}
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              name="reason"
              value={editFormData.reason}
              onChange={handleEditChange}
              required
              rows={4}
              className="input-field"
              placeholder="Please provide a reason for your leave request..."
            />
          </div>

          <div className="flex justify-end gap-2 mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowEditModal(false);
                setSelectedRequest(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={editingId === selectedRequest?.id}
            >
              {editingId === selectedRequest?.id
                ? "Updating..."
                : "Update Leave Request"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
};

export default MyLeaveRequests;
