class NexusException(Exception):
    """Base exception for Nexus Agent Hub."""
    def __init__(self, message: str, status_code: int = 400, error_code: str = "ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)

class NotFoundException(NexusException):
    def __init__(self, item_name: str):
        super().__init__(f"{item_name} not found.", status_code=404, error_code="NOT_FOUND")

class AuthenticationException(NexusException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED")

class BadRequestException(NexusException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_code="BAD_REQUEST")

class ExternalServiceException(NexusException):
    def __init__(self, service_name: str, details: str):
        super().__init__(f"Error communicating with {service_name}: {details}", status_code=502, error_code="EXTERNAL_SERVICE_ERROR")
