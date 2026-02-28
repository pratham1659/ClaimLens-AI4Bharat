import axios from "./axios";

export const employeeAPI = {
  applyLeave: async (leaveData) => {
    console.log("[employeeAPI.applyLeave] Called with:", leaveData);
    const response = await axios.post("/employee/leave-requests", leaveData);
    console.log("[employeeAPI.applyLeave] Response:", response.data);
    return response.data;
  },

  getMyLeaveRequests: async () => {
    console.log("[employeeAPI.getMyLeaveRequests] Called");
    const response = await axios.get("/employee/leave-requests");
    console.log("[employeeAPI.getMyLeaveRequests] Response:", response.data);
    return response.data;
  },

  getMyLeaveBalance: async (year) => {
    console.log("[employeeAPI.getMyLeaveBalance] Called with year:", year);
    const response = await axios.get(
      `/employee/leave-balance${year ? `?year=${year}` : ""}`
    );
    console.log("[employeeAPI.getMyLeaveBalance] Response:", response.data);
    return response.data;
  },

  getMyHistory: async (limit = 20) => {
    console.log("[employeeAPI.getMyHistory] Called with limit:", limit);
    const response = await axios.get(
      `/admin-controls/audit-trail/my-history?limit=${limit}`
    );
    console.log("[employeeAPI.getMyHistory] Response:", response.data);
    return response.data;
  },

  updateLeaveRequest: async (requestId, updateData) => {
    console.log("[employeeAPI.updateLeaveRequest] Called with:", {
      requestId,
      updateData,
    });
    const response = await axios.put(
      `/employee/leave-requests/${requestId}`,
      updateData
    );
    console.log("[employeeAPI.updateLeaveRequest] Response:", response.data);
    return response.data;
  },

  cancelLeaveRequest: async (requestId) => {
    console.log("[employeeAPI.cancelLeaveRequest] Called with:", requestId);
    const response = await axios.delete(
      `/employee/leave-requests/${requestId}`
    );
    console.log("[employeeAPI.cancelLeaveRequest] Response:", response.data);
    return response.data;
  },

  getWfhMonthlyUsage: async (year) => {
    console.log("[employeeAPI.getWfhMonthlyUsage] Called with year:", year);
    const response = await axios.get(
      `/employee/wfh-monthly-usage${year ? `?year=${year}` : ""}`
    );
    console.log("[employeeAPI.getWfhMonthlyUsage] Response:", response.data);
    return response.data;
  },
};
