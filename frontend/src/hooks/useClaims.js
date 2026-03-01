// frontend/src/hooks/useClaims.js
/**
 * Custom hook for claims management.
 */

import { useState, useCallback } from "react";
import { claimsAPI } from "../services/api";
import toast from "react-hot-toast";
import { getErrorMessage } from "../utils/error";

export function useClaims() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    pageSize: 20,
  });

  const fetchClaims = useCallback(async (params = {}) => {
    setLoading(true);
    try {
      const response = await claimsAPI.list(params);
      setClaims(response.data.claims);
      setPagination({
        total: response.data.total,
        page: response.data.page,
        pageSize: response.data.page_size,
      });
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to fetch claims"));
    } finally {
      setLoading(false);
    }
  }, []);

  const createClaim = useCallback(async (data) => {
    try {
      const response = await claimsAPI.create(data);
      toast.success("Claim created successfully");
      return response.data.data;
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to create claim"));
      throw error;
    }
  }, []);

  const getClaim = useCallback(async (claimId) => {
    try {
      const response = await claimsAPI.get(claimId);
      return response.data.data;
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to fetch claim"));
      throw error;
    }
  }, []);

  const deleteClaim = useCallback(async (claimId) => {
    try {
      await claimsAPI.delete(claimId);
      toast.success("Claim deleted successfully");
      setClaims((prev) => prev.filter((c) => c.id !== claimId));
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to delete claim"));
      throw error;
    }
  }, []);

  return {
    claims,
    loading,
    pagination,
    fetchClaims,
    createClaim,
    getClaim,
    deleteClaim,
  };
}
