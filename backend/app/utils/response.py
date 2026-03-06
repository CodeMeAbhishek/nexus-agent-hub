from typing import Any, Optional
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

def standard_response(
    data: Any = None,
    message: str = "Success",
    success: bool = True,
    status_code: int = 200,
) -> JSONResponse:
    """
    Returns a standardized JSON response.
    Format:
    {
        "success": bool,
        "message": str,
        "data": Any,
        "error": None
    }
    """
    content = {
        "success": success,
        "message": message,
        "data": jsonable_encoder(data) if data is not None else None,
        "error": None,
    }
    return JSONResponse(content=content, status_code=status_code)


def error_response(
    message: str,
    status_code: int = 400,
    error_code: Optional[str] = None,
    details: Any = None
) -> JSONResponse:
    """
    Returns a standardized Error response.
    Format:
    {
        "success": bool,
        "message": str,
        "data": None,
        "error": {
            "code": str,
            "details": Any
        }
    }
    """
    content = {
        "success": False,
        "message": message,
        "data": None,
        "error": {
            "code": error_code or str(status_code),
            "details": details
        }
    }
    return JSONResponse(content=content, status_code=status_code)
