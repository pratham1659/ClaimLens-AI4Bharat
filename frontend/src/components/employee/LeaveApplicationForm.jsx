import React, { useState, useEffect } from "react";
import Card from "../common/Card";
import Input from "../common/Input";
import Button from "../common/Button";
import Alert from "../common/Alert";
import Modal from "../common/Modal";
import LeaveConfirmationModal from "./LeaveConfirmationModal";
import CustomLeaveTypeSelect from "./CustomLeaveTypeSelect";
import { employeeAPI } from "../../api/employee";
import { calculateDays } from "../../utils/validators";

const LeaveApplicationForm = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    leave_type_id: "",
    start_date: "",
    end_date: "",
    reason: "",
  });
  const [totalDays, setTotalDays] = useState(0);
  const [balances, setBalances] = useState([]);
  const [selectedBalance, setSelectedBalance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingBalance, setLoadingBalance] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [errorModalMessage, setErrorModalMessage] = useState("");

  useEffect(() => {
    fetchBalance();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (formData.start_date && formData.end_date) {
      const days = calculateDays(formData.start_date, formData.end_date);
      setTotalDays(days);
    } else {
      setTotalDays(0);
    }
  }, [formData.start_date, formData.end_date]);

  useEffect(() => {
    if (formData.leave_type_id && balances.length > 0) {
      const balance = balances.find(
        (b) => b.leave_type_id === parseInt(formData.leave_type_id)
      );
      setSelectedBalance(balance || null);
    } else {
      setSelectedBalance(null);
    }
  }, [formData.leave_type_id, balances]);

  // Get today's date in YYYY-MM-DD format for min date
  const getTodayDate = () => {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const isWorkFromHome = () => {
    if (!formData.leave_type_id || balances.length === 0) return false;
    const balance = balances.find(
      (b) => b.leave_type_id === parseInt(formData.leave_type_id)
    );
    return balance?.leave_type_name === "Work From Home";
  };

  const fetchBalance = async () => {
    setLoadingBalance(true);
    try {
      const data = await employeeAPI.getMyLeaveBalance();
      // Filter out Paid Leave only
      const filteredBalances = data.filter(
        (balance) => balance.leave_type_name !== "Paid Leave"
      );
      setBalances(filteredBalances);
      // Auto-select first leave type if available
      if (filteredBalances.length > 0) {
        setFormData((prev) => ({
          ...prev,
          leave_type_id: filteredBalances[0].leave_type_id.toString(),
        }));
      }
    } catch (err) {
      console.error("Failed to fetch balance:", err);
    } finally {
      setLoadingBalance(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError("");
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    console.log("[LeaveApplicationForm] Form submission started", formData);

    // Client-side validation
    if (!formData.leave_type_id) {
      setError("Please select a leave type");
      console.error(
        "[LeaveApplicationForm] Validation failed: No leave type selected"
      );
      return;
    }

    if (!formData.start_date || !formData.end_date) {
      setError("Please select start and end dates");
      console.error("[LeaveApplicationForm] Validation failed: Missing dates");
      return;
    }

    if (!formData.reason || formData.reason.trim().length === 0) {
      setError("Please provide a reason for your leave request");
      console.error(
        "[LeaveApplicationForm] Validation failed: No reason provided"
      );
      return;
    }

    // Skip balance check for Work From Home
    if (
      !isWorkFromHome() &&
      selectedBalance &&
      totalDays > selectedBalance.remaining_days
    ) {
      const errorMsg = `Insufficient leave balance. You have ${Number(
        selectedBalance.remaining_days
      ).toFixed(1)} days remaining.`;
      setError(errorMsg);
      console.error(
        "[LeaveApplicationForm] Validation failed: Insufficient balance",
        {
          requested: totalDays,
          available: selectedBalance.remaining_days,
        }
      );
      return;
    }

    // Show confirmation modal
    setShowConfirmModal(true);
  };

  const handleConfirmSubmit = async () => {
    setLoading(true);
    setError("");
    setSuccess("");

    const requestData = {
      leave_type_id: parseInt(formData.leave_type_id),
      start_date: formData.start_date,
      end_date: formData.end_date,
      reason: formData.reason.trim(),
    };

    console.log(
      "[LeaveApplicationForm] Sending request to backend:",
      requestData
    );

    try {
      const response = await employeeAPI.applyLeave(requestData);
      console.log(
        "[LeaveApplicationForm] Leave application successful:",
        response
      );

      setSuccess("Leave application submitted successfully!");
      setFormData({
        leave_type_id:
          balances.length > 0 ? balances[0].leave_type_id.toString() : "",
        start_date: "",
        end_date: "",
        reason: "",
      });
      // Refresh balances after submission
      fetchBalance();
      setShowConfirmModal(false);
      if (onSuccess) onSuccess();
    } catch (err) {
      console.error(
        "[LeaveApplicationForm] Error submitting leave application:",
        err
      );

      // Handle validation errors from backend
      if (err.response?.status === 422 && err.response?.data?.detail) {
        const details = err.response.data.detail;
        if (Array.isArray(details)) {
          // Extract validation error messages
          const errorMessages = details
            .map((detail) => {
              const field = detail.loc
                ? detail.loc[detail.loc.length - 1]
                : "field";
              return `${field}: ${detail.msg}`;
            })
            .join(", ");
          setError(`Validation error: ${errorMessages}`);
          console.error(
            "[LeaveApplicationForm] Backend validation errors:",
            details
          );
        } else if (typeof details === "string") {
          setError(details);
        } else {
          setError("Invalid input. Please check your form.");
        }
      } else if (err.response?.data?.detail) {
        // Handle other backend errors
        const detail = err.response.data.detail;
        const errorMessage =
          typeof detail === "string"
            ? detail
            : "Failed to submit leave application";

        // Show WFH overlap errors in modal
        if (errorMessage.includes("Work From Home request overlaps")) {
          setErrorModalMessage(errorMessage);
          setShowErrorModal(true);
          setShowConfirmModal(false);
        } else {
          setError(errorMessage);
        }
      } else if (err.message) {
        setError(err.message);
      } else {
        setError("Failed to submit leave application. Please try again.");
      }
    } finally {
      setLoading(false);
      console.log("[LeaveApplicationForm] Form submission completed");
    }
  };

  const getLeaveTypeName = () => {
    if (!formData.leave_type_id || balances.length === 0) return "";
    const balance = balances.find(
      (b) => b.leave_type_id === parseInt(formData.leave_type_id)
    );
    return balance ? balance.leave_type_name : "";
  };

  return (
    <>
      <LeaveConfirmationModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handleConfirmSubmit}
        loading={loading}
        leaveData={{
          leaveTypeName: getLeaveTypeName(),
          start_date: formData.start_date,
          end_date: formData.end_date,
          totalDays: totalDays,
          reason: formData.reason,
          balance: isWorkFromHome() ? null : selectedBalance,
        }}
      />

      {/* Error Modal for WFH Overlaps */}
      <Modal
        isOpen={showErrorModal}
        onClose={() => {
          setShowErrorModal(false);
          setErrorModalMessage("");
        }}
        title="Cannot Submit Request"
        size="md"
      >
        <div className="space-y-4">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg
                className="h-6 w-6 text-red-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-700 font-medium">
                {errorModalMessage}
              </p>
              <p className="text-sm text-gray-600 mt-2">
                Please check your existing Work From Home requests and choose
                different dates.
              </p>
            </div>
          </div>
          <div className="flex justify-end pt-3 border-t border-gray-200">
            <Button
              variant="primary"
              onClick={() => {
                setShowErrorModal(false);
                setErrorModalMessage("");
              }}
            >
              Understood
            </Button>
          </div>
        </div>
      </Modal>

      <Card>
        {/* Alert Messages Section */}
        <div className="space-y-3 mb-4">
          {error && (
            <Alert type="error" message={error} onClose={() => setError("")} />
          )}
          {success && (
            <Alert
              type="success"
              message={success}
              onClose={() => setSuccess("")}
            />
          )}

          {loadingBalance ? (
            <div className="text-center py-3">
              <p className="text-sm text-gray-500">Loading leave balance...</p>
            </div>
          ) : balances.length === 0 ? (
            <Alert
              type="warning"
              message="No leave balance found. Please contact your administrator."
            />
          ) : null}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Leave Type with Custom Dropdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <CustomLeaveTypeSelect
              balances={balances}
              value={formData.leave_type_id}
              onChange={handleChange}
              required
            />

            {/* Balance Display KPI - Compact Version */}
            {selectedBalance && !isWorkFromHome() && (
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-300 rounded-lg p-3 shadow-sm">
                <h4 className="text-xs font-semibold text-blue-900 mb-2 flex items-center">
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                    <path
                      fillRule="evenodd"
                      d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"
                      clipRule="evenodd"
                    />
                  </svg>
                  {selectedBalance.leave_type_name} Balance (FY{" "}
                  {selectedBalance.year})
                </h4>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center bg-white rounded-md p-2 shadow-sm">
                    <p className="text-xs text-blue-600 font-medium mb-1">
                      Total
                    </p>
                    <p className="text-xl font-bold text-blue-900">
                      {Number(selectedBalance.total_days).toFixed(1)}
                    </p>
                  </div>
                  <div className="text-center bg-white rounded-md p-2 shadow-sm">
                    <p className="text-xs text-orange-600 font-medium mb-1">
                      Used
                    </p>
                    <p className="text-xl font-bold text-orange-700">
                      {Number(selectedBalance.used_days).toFixed(1)}
                    </p>
                  </div>
                  <div className="text-center bg-white rounded-md p-2 shadow-sm">
                    <p className="text-xs text-green-600 font-medium mb-1">
                      Available
                    </p>
                    <p className="text-xl font-bold text-green-700">
                      {Number(selectedBalance.remaining_days).toFixed(1)}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {isWorkFromHome() && (
              <div className="bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-300 rounded-lg p-4 flex items-center shadow-sm">
                <div className="flex items-start">
                  <svg
                    className="w-6 h-6 text-green-600 mr-3 mt-0.5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
                  </svg>
                  <div>
                    <h4 className="font-semibold text-green-900 text-sm mb-1">
                      Work From Home
                    </h4>
                    <p className="text-xs text-green-700">
                      No balance required - subject to admin approval
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Dates and Total Days - Combined Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Input
              label="Start Date"
              type="date"
              name="start_date"
              value={formData.start_date}
              onChange={handleChange}
              required
              min={getTodayDate()}
            />

            <Input
              label="End Date"
              type="date"
              name="end_date"
              value={formData.end_date}
              onChange={handleChange}
              required
              min={formData.start_date || getTodayDate()}
            />

            {totalDays > 0 && (
              <div className="flex items-end">
                <div
                  className={`w-full border-2 rounded-lg p-2.5 ${
                    !isWorkFromHome() &&
                    selectedBalance &&
                    totalDays > selectedBalance.remaining_days
                      ? "bg-red-50 border-red-300"
                      : "bg-green-50 border-green-300"
                  }`}
                >
                  <p className="text-xs text-gray-600 mb-0.5">Total Days</p>
                  <p
                    className={`text-xl font-bold ${
                      !isWorkFromHome() &&
                      selectedBalance &&
                      totalDays > selectedBalance.remaining_days
                        ? "text-red-700"
                        : "text-green-700"
                    }`}
                  >
                    {totalDays}
                    {!isWorkFromHome() &&
                      selectedBalance &&
                      totalDays > selectedBalance.remaining_days && (
                        <span className="text-xs ml-1 font-normal text-red-600">
                          (Exceeds!)
                        </span>
                      )}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Reason */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              name="reason"
              value={formData.reason}
              onChange={handleChange}
              required
              rows={3}
              className="input-field resize-none"
              placeholder="Please provide a reason for your leave request..."
            />
          </div>

          {/* Submit Button */}
          <div className="flex justify-end pt-2">
            <Button type="submit" variant="primary" loading={loading}>
              Submit Application
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
};

export default LeaveApplicationForm;
