import uuid
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.errors import AppError

REQUEST_ID_HEADER = "X-Request-ID"


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex)


def _error_response(
    request: Request, *, status_code: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "request_id": _request_id(request),
            "details": details or {},
        },
    )
    response.headers[REQUEST_ID_HEADER] = _request_id(request)
    return response


def _validation_errors(errors: Sequence[Any]) -> list[dict[str, Any]]:
    return [{key: value for key, value in error.items() if key != "ctx"} for error in errors]


def install_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request.state.request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response


def install_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            code = str(exc.detail.get("code", "HTTP_ERROR"))
            message = str(exc.detail.get("message", "请求失败"))
            details = exc.detail.get("details", {})
        elif exc.status_code == 404:
            code, message, details = "NOT_FOUND", "请求的资源不存在", {}
        elif exc.status_code == 401:
            code, message, details = "UNAUTHORIZED", "身份认证失败", {}
        elif exc.status_code == 403:
            code, message, details = "FORBIDDEN", "没有执行此操作的权限", {}
        else:
            code, message, details = "HTTP_ERROR", str(exc.detail), {}
        return _error_response(request, status_code=exc.status_code, code=code, message=message, details=details)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="请求参数校验失败",
            details={"errors": _validation_errors(exc.errors())},
        )
