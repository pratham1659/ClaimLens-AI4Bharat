import axios from "./axios";

export const adminAPI = {
  // Leave Request Management
  getLeaveRequests: async (status = null) => {
    console.log("[adminAPI.getLeaveRequests] Called with status:", status);
    const params = status ? `?status=${status}` : "";
    const response = await axios.get(`/admin/leave-requests${params}`);
    console.log("[adminAPI.getLeaveRequests] Response:", response.data);
    return response.data;
  },

  approveLeaveRequest: async (requestId, allowNegative = false) => {
    console.log("[adminAPI.approveLeaveRequest] Called with:", {
      requestId,
      allowNegative,
    });
    const response = await axios.post(
      `/admin-controls/leave-requests/${requestId}/approve`,
      { allow_negative: allowNegative }
    );
    console.log("[adminAPI.approveLeaveRequest] Response:", response.data);
    return response.data;
  },

  rejectLeaveRequest: async (requestId, rejectionReason) => {
    console.log("[adminAPI.rejectLeaveRequest] Called with:", {
      requestId,
      rejectionReason,
    });
    const response = await axios.post(
      `/admin-controls/leave-requests/${requestId}/reject`,
      { rejection_reason: rejectionReason }
    );
    console.log("[adminAPI.rejectLeaveRequest] Response:", response.data);
    return response.data;
  },

  revertLeaveStatus: async (requestId, newStatus, reason = null) => {
    console.log("[adminAPI.revertLeaveStatus] Called with:", {
      requestId,
      newStatus,
      reason,
    });
    const params = new URLSearchParams({ new_status: newStatus });
    if (reason) {
      params.append("reason", reason);
    }
    const response = await axios.post(
      `/admin/leave-requests/${requestId}/revert-status?${params.toString()}`
    );
    console.log("[adminAPI.revertLeaveStatus] Response:", response.data);
    return response.data;
  },

  issueDirectLeave: async (leaveData) => {
    console.log("[adminAPI.issueDirectLeave] Called with:", leaveData);
    const response = await axios.post(
      "/admin-controls/leave-requests/issue-direct",
      leaveData
    );
    console.log("[adminAPI.issueDirectLeave] Response:", response.data);
    return response.data;
  },

  // Balance Management
  adjustLeaveBalance: async (balanceId, newTotalDays, reason) => {
    console.log("[adminAPI.adjustLeaveBalance] Called with:", {
      balanceId,
      newTotalDays,
      reason,
    });
    const response = await axios.post(
      `/admin-controls/leave-balance/${balanceId}/adjust`,
      { new_total_days: newTotalDays, reason }
    );
    console.log("[adminAPI.adjustLeaveBalance] Response:", response.data);
    return response.data;
  },

  // FY Transition
  processLapse: async (fromYear) => {
    console.log("[adminAPI.processLapse] Called with fromYear:", fromYear);
    const response = await axios.post(
      `/admin-controls/fy-transition/lapse?from_year=${fromYear}`
    );
    console.log("[adminAPI.processLapse] Response:", response.data);
    return response.data;
  },

  processCarryForward: async (fromYear, toYear) => {
    console.log("[adminAPI.processCarryForward] Called with:", {
      fromYear,
      toYear,
    });
    const response = await axios.post(
      `/admin-controls/fy-transition/carryforward?from_year=${fromYear}&to_year=${toYear}`
    );
    console.log("[adminAPI.processCarryForward] Response:", response.data);
    return response.data;
  },

  completeFYTransition: async (fromYear, toYear) => {
    console.log("[adminAPI.completeFYTransition] Called with:", {
      fromYear,
      toYear,
    });
    const response = await axios.post(
      "/admin-controls/fy-transition/complete",
      { from_year: fromYear, to_year: toYear }
    );
    console.log("[adminAPI.completeFYTransition] Response:", response.data);
    return response.data;
  },

  // Audit Trail
  getAuditTrail: async (params = {}) => {
    console.log("[adminAPI.getAuditTrail] Called with params:", params);
    const queryString = new URLSearchParams(params).toString();
    const response = await axios.get(
      `/admin-controls/audit-trail${queryString ? `?${queryString}` : ""}`
    );
    console.log("[adminAPI.getAuditTrail] Response:", response.data);
    return response.data;
  },

  // Employee Management
  getEmployeesWithBalances: async (includeInactive = true) => {
    const params = includeInactive ? "?include_inactive=true" : "";
    const response = await axios.get(`/admin/employees-with-balances${params}`);
    console.log("[adminAPI.getEmployeesWithBalances] Response:", response.data);
    return response.data;
  },

  createEmployee: async (employeeData) => {
    const response = await axios.post("/admin/employees", employeeData);
    console.log("[adminAPI.createEmployee] Response:", response.data);
    return response.data;
  },

  getEmployees: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await axios.get(
      `/admin/employees${queryString ? `?${queryString}` : ""}`
    );
    console.log("[adminAPI.getEmployees] Response:", response.data);
    return response.data;
  },

  updateEmployee: async (employeeId, employeeData) => {
    const response = await axios.put(
      `/admin/employees/${employeeId}`,
      employeeData
    );
    console.log("[adminAPI.updateEmployee] Response:", response.data);
    return response.data;
  },

  deleteEmployee: async (employeeId) => {
    const response = await axios.delete(`/admin/employees/${employeeId}`);
    console.log("[adminAPI.deleteEmployee] Response:", response.data);
    return response.data;
  },

  toggleEmployeeStatus: async (employeeId) => {
    const response = await axios.post(
      `/admin/employees/${employeeId}/toggle-status`
    );
    console.log("[adminAPI.statusEmployees] Response:", response.data);
    return response.data;
  },

  activateEmployee: async (employeeId) => {
    const response = await axios.put(`/admin/employees/${employeeId}/activate`);
    console.log("[adminAPI.statusEmployees] Response:", response.data);
    return response.data;
  },

  getEmployeeLeaveBalance: async (employeeId, year = null) => {
    const params = year ? `?year=${year}` : "";
    const response = await axios.get(
      `/admin/employees/${employeeId}/leave-balance${params}`
    );
    console.log("[adminAPI.getEmployeeLeaveBalance] Response:", response.data);
    return response.data;
  },
};
