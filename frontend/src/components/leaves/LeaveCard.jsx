import React, { useState } from "react";
import { format } from "date-fns";
import Button from "../common/Button";
import Modal from "../common/Modal";
import { useAuth } from "../../hooks/useAuth";
import { calculateDays } from "../../utils/validators";

const LeaveCard = ({ leave, onUpdate, onDelete }) => {
  const [showModal, setShowModal] = useState(false);
  const [adminComment, setAdminComment] = useState("");
  const [actionType, setActionType] = useState("");
  const { isAdmin } = useAuth();

  const getStatusBadge = (status) => {
    const badges = {
      pending: "badge-pending",
      approved: "badge-approved",
      rejected: "badge-rejected",
    };
    return badges[status] || "badge-pending";
  };

  const getLeaveTypeColor = (type) => {
    const colors = {
      sick: "bg-red-100 text-red-800",
      casual: "bg-blue-100 text-blue-800",
      emergency: "bg-orange-100 text-orange-800",
    };
    return colors[type] || "bg-gray-100 text-gray-800";
  };

  const handleAction = (action) => {
    setActionType(action);
    setShowModal(true);
  };

  const handleConfirmAction = async () => {
    await onUpdate(leave.id, {
      status: actionType,
      admin_comment: adminComment,
    });
    setShowModal(false);
    setAdminComment("");
  };

  const leaveDays = calculateDays(leave.start_date, leave.end_date);

  return (
    <>
      <div className="card hover:shadow-lg transition-shadow duration-200">
        <div className="flex justify-between items-start mb-4">
          <div>
            <span className={`badge ${getLeaveTypeColor(leave.leave_type)}`}>
              {leave.leave_type.charAt(0).toUpperCase() +
                leave.leave_type.slice(1)}{" "}
              Leave
            </span>
            <span className={`badge ${getStatusBadge(leave.status)} ml-2`}>
              {leave.status.charAt(0).toUpperCase() + leave.status.slice(1)}
            </span>
          </div>
          <span className="text-sm text-gray-500">
            {leaveDays} day{leaveDays > 1 ? "s" : ""}
          </span>
        </div>

        <div className="space-y-3">
          <div>
            <p className="text-sm text-gray-600">Duration</p>
            <p className="font-medium">
              {format(new Date(leave.start_date), "MMM dd, yyyy")} -{" "}
              {format(new Date(leave.end_date), "MMM dd, yyyy")}
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-600">Reason</p>
            <p className="text-gray-800">{leave.reason}</p>
          </div>

          {leave.admin_comment && (
            <div className="bg-gray-50 p-3 rounded-lg">
              <p className="text-sm text-gray-600">Admin Comment</p>
              <p className="text-gray-800">{leave.admin_comment}</p>
            </div>
          )}

          <div className="text-xs text-gray-500">
            Requested on{" "}
            {format(new Date(leave.created_at), "MMM dd, yyyy HH:mm")}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 pt-4 border-t border-gray-200 flex gap-2">
          {isAdmin && leave.status === "pending" && (
            <>
              <Button
                variant="success"
                onClick={() => handleAction("approved")}
                className="flex-1"
              >
                Approve
              </Button>
              <Button
                variant="danger"
                onClick={() => handleAction("rejected")}
                className="flex-1"
              >
                Reject
              </Button>
            </>
          )}

          {!isAdmin && leave.status === "pending" && (
            <Button
              variant="danger"
              onClick={() => onDelete(leave.id)}
              fullWidth
            >
              Cancel Request
            </Button>
          )}
        </div>
      </div>

      {/* Action Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={`${
          actionType === "approved" ? "Approve" : "Reject"
        } Leave Request`}
      >
        <div className="space-y-4">
          <p className="text-gray-700">
            Are you sure you want to{" "}
            {actionType === "approved" ? "approve" : "reject"} this leave
            request?
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Comment (Optional)
            </label>
            <textarea
              value={adminComment}
              onChange={(e) => setAdminComment(e.target.value)}
              rows="3"
              className="input-field"
              placeholder="Add a comment..."
            />
          </div>

          <div className="flex gap-3 justify-end">
            <Button variant="secondary" onClick={() => setShowModal(false)}>
              Cancel
            </Button>
            <Button
              variant={actionType === "approved" ? "success" : "danger"}
              onClick={handleConfirmAction}
            >
              Confirm
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};

export default LeaveCard;
