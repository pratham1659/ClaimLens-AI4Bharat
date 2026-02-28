class ClaimLensReasoningError(Exception):
    """
    Base exception class for all reasoning-layer errors.
    """
    pass

class ReasoningValidationError(ClaimLensReasoningError):
    """
    Raised when LLM output fails JSON parsing or schema validation
    even after retry attempts.
    """
    pass