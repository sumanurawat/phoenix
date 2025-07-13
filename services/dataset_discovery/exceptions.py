"""
Custom exceptions for dataset discovery service.
Provides clear error messages and appropriate error codes.
"""


class DatasetDiscoveryError(Exception):
    """Base exception for dataset discovery service."""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", details: str = None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        result = {
            "code": self.error_code,
            "message": self.message
        }
        if self.details:
            result["details"] = self.details
        return result


class KaggleAuthenticationError(DatasetDiscoveryError):
    """Raised when Kaggle authentication fails."""
    
    def __init__(self, message: str = "Failed to authenticate with Kaggle API", details: str = None):
        super().__init__(
            message=message,
            error_code="KAGGLE_AUTH_ERROR",
            details=details or "Please ensure KAGGLE_USERNAME and KAGGLE_KEY are set correctly"
        )


class KaggleAPIError(DatasetDiscoveryError):
    """Raised when Kaggle API returns an error."""
    
    def __init__(self, message: str = "Kaggle API request failed", details: str = None, status_code: int = None):
        self.status_code = status_code
        super().__init__(
            message=message,
            error_code="KAGGLE_API_ERROR",
            details=details
        )


class SearchValidationError(DatasetDiscoveryError):
    """Raised when search parameters are invalid."""
    
    def __init__(self, message: str = "Invalid search parameters", details: str = None):
        super().__init__(
            message=message,
            error_code="SEARCH_VALIDATION_ERROR",
            details=details
        )


class ConfigurationError(DatasetDiscoveryError):
    """Raised when service configuration is invalid."""
    
    def __init__(self, message: str = "Service configuration is invalid", details: str = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details
        )


class DatasetNotFoundError(DatasetDiscoveryError):
    """Raised when a requested dataset is not found."""
    
    def __init__(self, dataset_ref: str, details: str = None):
        super().__init__(
            message=f"Dataset '{dataset_ref}' not found",
            error_code="DATASET_NOT_FOUND",
            details=details
        )


class RateLimitError(DatasetDiscoveryError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(self, message: str = "API rate limit exceeded", details: str = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=details or "Please wait before making more requests"
        )


class TimeoutError(DatasetDiscoveryError):
    """Raised when API requests timeout."""
    
    def __init__(self, message: str = "Request timed out", details: str = None):
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            details=details or "The request took too long to complete"
        )