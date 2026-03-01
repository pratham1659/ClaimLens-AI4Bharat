// frontend/src/utils/error.js
/**
 * Centralized frontend API/network error normalization.
 */

export function getErrorMessage(error, fallback = "Something went wrong") {
  if (!error) return fallback;
  if (typeof error === "string") return error;

  const responseData = error.response?.data;

  if (typeof responseData === "string") return responseData;

  if (responseData?.details?.errors?.[0]?.message) {
    return responseData.details.errors[0].message;
  }

  return (
    responseData?.message ||
    responseData?.error ||
    responseData?.detail ||
    error.userMessage ||
    error.message ||
    fallback
  );
}

export function isNotFoundError(error) {
  return error?.response?.status === 404;
}
