"""Custom exceptions for the trading backend."""

from typing import Optional, Dict, Any


class TradingBackendError(Exception):
    """Base exception for trading backend errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class BrokerError(TradingBackendError):
    """Exception raised for broker-related errors."""
    pass


class AuthenticationError(BrokerError):
    """Exception raised for authentication failures."""
    pass


class OrderError(BrokerError):
    """Exception raised for order-related errors."""
    pass


class InstrumentError(BrokerError):
    """Exception raised for instrument-related errors."""
    pass


class APIError(BrokerError):
    """Exception raised for API communication errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class TelegramBotError(TradingBackendError):
    """Exception raised for Telegram bot errors."""
    pass


class ConfigurationError(TradingBackendError):
    """Exception raised for configuration errors."""
    pass


class ValidationError(TradingBackendError):
    """Exception raised for data validation errors."""
    pass 