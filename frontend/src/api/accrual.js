import axios from "./axios";

export const accrualAPI = {
  processMonthlyAccrual: async (month, year, userId = null) => {
    console.log("[accrualAPI.processMonthlyAccrual] Called with:", {
      month,
      year,
      userId,
    });
    const params = new URLSearchParams();
    params.append("month", month);
    params.append("year", year);
    if (userId) params.append("user_id", userId);

    const response = await axios.post(
      `/accrual/process-monthly?${params.toString()}`
    );
    console.log("[accrualAPI.processMonthlyAccrual] Response:", response.data);
    return response.data;
  },

  processAccrual: async (userId = null, year = null) => {
    console.log("[accrualAPI.processAccrual] Called with:", { userId, year });
    const params = new URLSearchParams();
    if (userId) params.append("user_id", userId);
    if (year) params.append("year", year);

    const response = await axios.post(
      `/accrual/process${params.toString() ? `?${params.toString()}` : ""}`
    );
    console.log("[accrualAPI.processAccrual] Response:", response.data);
    return response.data;
  },

  getAccrualSummary: async (userId = null, year = null) => {
    console.log("[accrualAPI.getAccrualSummary] Called with:", {
      userId,
      year,
    });
    const url = userId
      ? `/accrual/summary/${userId}${year ? `?year=${year}` : ""}`
      : `/accrual/summary${year ? `?year=${year}` : ""}`;

    const response = await axios.get(url);
    console.log("[accrualAPI.getAccrualSummary] Response:", response.data);
    return response.data;
  },

  initializeRates: async () => {
    console.log("[accrualAPI.initializeRates] Called");
    const response = await axios.post("/accrual/initialize-rates");
    console.log("[accrualAPI.initializeRates] Response:", response.data);
    return response.data;
  },

  getFinancialYearInfo: async () => {
    console.log("[accrualAPI.getFinancialYearInfo] Called");
    const response = await axios.get("/accrual/financial-year-info");
    console.log("[accrualAPI.getFinancialYearInfo] Response:", response.data);
    return response.data;
  },

  getAccrualHistory: async (year = null) => {
    console.log("[accrualAPI.getAccrualHistory] Called with:", { year });
    const url = `/accrual/history${year ? `?year=${year}` : ""}`;
    const response = await axios.get(url);
    console.log("[accrualAPI.getAccrualHistory] Response:", response.data);
    return response.data;
  },

  updateLeaveBalance: async (balanceId, updateData) => {
    console.log("[accrualAPI.updateLeaveBalance] Called with:", {
      balanceId,
      updateData,
    });
    const response = await axios.put(
      `/admin/leave-balance/${balanceId}`,
      updateData
    );
    console.log("[accrualAPI.updateLeaveBalance] Response:", response.data);
    return response.data;
  },
};
