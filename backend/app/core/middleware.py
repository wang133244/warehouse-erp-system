"""访问日志、AppError 与未捕获异常的 HTTP 形态。"""

import logging  # 按路径选择 INFO/DEBUG 级别
import uuid  # 生成请求 ID
from collections.abc import Awaitable, Callable, Sequence  # 中间件与校验错误类型
from time import perf_counter  # 高精度计时，算耗时毫秒
from typing import Any  # 错误 details 的宽松类型

from fastapi import FastAPI, Request  # 应用与请求对象
from fastapi.exceptions import RequestValidationError  # 请求体/参数校验失败
from fastapi.responses import JSONResponse, Response  # JSON 错误体与通用响应
from starlette.exceptions import HTTPException as StarletteHTTPException  # HTTPException 基类

from backend.app.core.errors import AppError  # 业务异常
from backend.app.core.logging import QUIET_PATHS, get_logger, set_request_id  # 静默路径、日志、请求 ID 上下文

REQUEST_ID_HEADER = "X-Request-ID"  # 对外透传的请求关联头
http_logger = get_logger("http")  # HTTP 访问与错误日志


def _request_id(request: Request) -> str:  # 优先用中间件写入的 ID，否则从头或新生成
    return getattr(request.state, "request_id", request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex)  # 保证错误响应也能带回 ID


def _error_response(  # 统一错误信封：code/message/request_id/details
    request: Request, *, status_code: int, code: str, message: str, details: dict[str, Any] | None = None  # 关键字参数避免顺序搞混
) -> JSONResponse:  # 返回 JSON 响应
    response = JSONResponse(  # 构造标准错误体
        status_code=status_code,  # HTTP 状态
        content={  # 稳定字段，前端可依赖
            "code": code,  # 机器可读错误码
            "message": message,  # 人类可读说明
            "request_id": _request_id(request),  # 便于对日志
            "details": details or {},  # 缺省空对象而不是 null
        },  # content 结束
    )  # JSONResponse 结束
    response.headers[REQUEST_ID_HEADER] = _request_id(request)  # 响应头同步带上请求 ID
    return response  # 交给异常处理器返回


def _validation_errors(errors: Sequence[Any]) -> list[dict[str, Any]]:  # 去掉 ctx，避免把异常对象序列化失败
    return [{key: value for key, value in error.items() if key != "ctx"} for error in errors]  # 逐条过滤


def _is_quiet_path(path: str) -> bool:  # 探活与文档流量不打 INFO，减少噪音
    return path in QUIET_PATHS or path.startswith("/docs")  # /docs 子路径同样静默


def install_middleware(application: FastAPI) -> None:  # 给应用挂请求 ID 与访问日志中间件
    @application.middleware("http")  # Starlette HTTP 中间件
    async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # 每个请求进出各记一次
        request.state.request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex  # 尊重客户端传入，否则自生成
        set_request_id(request.state.request_id)  # 写入 ContextVar，业务日志能带上
        started = perf_counter()  # 开始计时
        try:  # 正常走下游
            response = await call_next(request)  # 调用后续中间件与路由
        except Exception:  # 未捕获异常也要记失败访问日志
            elapsed_ms = (perf_counter() - started) * 1000  # 耗时毫秒
            http_logger.exception(  # 带堆栈的错误日志
                "%s %s failed duration_ms=%.1f",  # 方法、路径、耗时
                request.method,  # HTTP 方法
                request.url.path,  # 路径不含 query，避免敏感参数入日志
                elapsed_ms,  # 耗时
            )  # exception 调用结束
            raise  # 继续交给异常处理器
        else:  # 下游成功返回
            elapsed_ms = (perf_counter() - started) * 1000  # 成功路径耗时
            level = logging.DEBUG if _is_quiet_path(request.url.path) else logging.INFO  # 静默路径降级
            http_logger.log(  # 按级别打访问日志
                level,  # DEBUG 或 INFO
                "%s %s status=%s duration_ms=%.1f",  # 方法路径状态耗时
                request.method,  # 方法
                request.url.path,  # 路径
                response.status_code,  # 状态码
                elapsed_ms,  # 耗时
            )  # log 调用结束
            response.headers[REQUEST_ID_HEADER] = request.state.request_id  # 把 ID 回写给客户端
            return response  # 正常响应
        finally:  # 无论成败都清掉上下文，避免串请求
            set_request_id(None)  # 复位 ContextVar


def install_exception_handlers(application: FastAPI) -> None:  # 把各类异常映射成统一 JSON
    @application.exception_handler(AppError)  # 业务主动抛出的领域错误
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # 按 AppError 字段填信封
        http_logger.warning("app error code=%s status=%s message=%s", exc.code, exc.status_code, exc.message)  # 业务错误打 warning
        return _error_response(  # 转成标准 JSON
            request,  # 带上 request_id
            status_code=exc.status_code,  # 业务指定的 HTTP 状态
            code=exc.code,  # 稳定错误码
            message=exc.message,  # 说明
            details=exc.details,  # 附加信息
        )  # _error_response 结束

    @application.exception_handler(StarletteHTTPException)  # HTTPException / 404 等
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:  # 尽量抽出 code/message
        if isinstance(exc.detail, dict):  # 调用方已按信封结构传入
            code = str(exc.detail.get("code", "HTTP_ERROR"))  # 缺省通用码
            message = str(exc.detail.get("message", "请求失败"))  # 缺省文案
            details = exc.detail.get("details", {})  # 附加字段
        elif exc.status_code == 404:  # 资源不存在
            code, message, details = "NOT_FOUND", "请求的资源不存在", {}  # 统一 404 文案
        elif exc.status_code == 401:  # 未认证
            code, message, details = "UNAUTHORIZED", "身份认证失败", {}  # 统一 401 文案
        elif exc.status_code == 403:  # 无权限
            code, message, details = "FORBIDDEN", "没有执行此操作的权限", {}  # 统一 403 文案
        else:  # 其它 HTTP 错误
            code, message, details = "HTTP_ERROR", str(exc.detail), {}  # 把 detail 当 message
        log = http_logger.warning if exc.status_code < 500 else http_logger.error  # 5xx 用 error
        log("http error code=%s status=%s path=%s", code, exc.status_code, request.url.path)  # 记录路径便于定位
        return _error_response(request, status_code=exc.status_code, code=code, message=message, details=details)  # 标准信封

    @application.exception_handler(RequestValidationError)  # Pydantic/查询参数校验失败
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # 固定 422
        http_logger.warning("validation error path=%s", request.url.path)  # 记录哪条路径校验失败
        return _error_response(  # 把字段错误放进 details
            request,  # 当前请求
            status_code=422,  # 语义上不可处理的实体
            code="VALIDATION_ERROR",  # 稳定码
            message="请求参数校验失败",  # 统一文案
            details={"errors": _validation_errors(exc.errors())},  # 去掉 ctx 后的错误列表
        )  # _error_response 结束

    @application.exception_handler(Exception)  # 最后兜底：未分类异常
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:  # 避免把堆栈回给客户端
        if isinstance(exc, (StarletteHTTPException, RequestValidationError, AppError)):  # 已被专用处理器覆盖的类型
            raise exc  # 再抛出让更具体的 handler 处理（防御性）
        http_logger.exception("unhandled error path=%s", request.url.path)  # 记完整堆栈
        return _error_response(  # 对外只说内部错误
            request,  # 当前请求
            status_code=500,  # 服务器错误
            code="INTERNAL_ERROR",  # 稳定码
            message="服务器内部错误",  # 不泄露细节
        )  # _error_response 结束
