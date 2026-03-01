// frontend/src/hooks/useAnalysis.js
/**
 * Custom hook for claim analysis.
 */

import { useState, useCallback } from "react";
import { analysisAPI } from "../services/api";
import toast from "react-hot-toast";
import { getErrorMessage, isNotFoundError } from "../utils/error";

export function useAnalysis() {
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [loading, setLoading] = useState(false);

  const analyzeClaim = useCallback(async (claimId) => {
    setAnalyzing(true);
    try {
      const response = await analysisAPI.analyze(claimId);
      setAnalysis(response.data.data);
      toast.success("Analysis completed");
      return response.data.data;
    } catch (error) {
      toast.error(getErrorMessage(error, "Analysis failed"));
      throw error;
    } finally {
      setAnalyzing(false);
    }
  }, []);

  const fetchAnalysis = useCallback(async (claimId) => {
    setLoading(true);
    try {
      const response = await analysisAPI.get(claimId);
      setAnalysis(response.data.data);
      return response.data.data;
    } catch (error) {
      // No analysis yet is not an error
      if (!isNotFoundError(error)) {
        toast.error(getErrorMessage(error, "Failed to fetch analysis"));
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async (claimId) => {
    try {
      const response = await analysisAPI.getHistory(claimId);
      return response.data;
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to fetch analysis history"));
      throw error;
    }
  }, []);

  return {
    analysis,
    analyzing,
    loading,
    analyzeClaim,
    analyzeCliam: analyzeClaim,
    fetchAnalysis,
    fetchHistory,
  };
}
