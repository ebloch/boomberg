"""Custom exceptions for FMP API."""


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str = "API rate limit exceeded"):
        super().__init__(message, status_code=429)


class SymbolNotFoundError(APIError):
    """Raised when a symbol is not found."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"Symbol not found: {symbol}", status_code=404)
