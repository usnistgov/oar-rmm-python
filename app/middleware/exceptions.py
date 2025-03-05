from fastapi import HTTPException, Request
from typing import Optional, Dict, Any

class ErrorInfo:
    """
    Error information structure to be used in the response
    """
    def __init__(self, url: str, message: str, http_status: str):
        self.url = url
        self.message = message
        self.http_status = http_status
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "message": self.message,
            "httpStatus": self.http_status
        }


class RMMException(Exception):
    """Base exception for RMM application"""
    def __init__(self, request_url: Optional[str] = None, message: Optional[str] = None):
        self.request_url = request_url
        self.message = message or "Resource you are looking for is not available."
        super().__init__(self.message)


class GeneralException(RMMException):
    """General exception for the application"""
    def __init__(self, request_url: Optional[str] = None, message: Optional[str] = None):
        default_message = "Exception thrown for this request."
        super().__init__(request_url, message or default_message)


class IllegalArgumentException(RMMException):
    """Exception raised when arguments are invalid"""
    def __init__(self, message: str = None, request_url: Optional[str] = None):
        msg = message or "Parameters are misplaced or values are missing."
        super().__init__(request_url, msg)


class ResourceNotFoundException(RMMException):
    """Exception raised when a resource is not found"""
    def __init__(self, message: str = None, request_url: Optional[str] = None):
        msg = message or "Resource you are looking for is not available."
        super().__init__(request_url, msg)


class KeyWordNotFoundException(RMMException):
    """Exception raised when keywords are not found"""
    def __init__(self, message: str = None, request_url: Optional[str] = None):
        msg = message or "Keywords you are looking for are not available."
        super().__init__(request_url, msg)


class InternalServerException(RMMException):
    """Exception raised for internal server errors"""
    def __init__(self, message: str = None, request_url: Optional[str] = None):
        msg = message or "There is an error running your query on the server."
        super().__init__(request_url, msg)