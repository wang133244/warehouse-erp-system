"""Application runtime logging: console, rotating files, and request_id context."""
from __future__ import annotations  # 允许前置注解

import logging  # 标准库日志
import sys  # 判断是否在 pytest 内、写 stdout
from contextvars import ContextVar  # 按请求隔离 request_id，协程安全
from logging.handlers import TimedRotatingFileHandler  # 按天滚动日志文件
from pathlib import Path  # 解析日志目录

_REQUEST_ID: ContextVar[str | None] = ContextVar("erp_request_id", default=None)  # 当前请求 ID，中间件写入
_configured = False  # 是否已完成一次 configure_logging
_factory_installed = False  # 是否已替换 LogRecord 工厂
LOGGER_NAME = "erp"  # 业务日志根名称
QUIET_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/docs/oauth2-redirect"}  # 探活/文档路径降为 DEBUG


class RequestIdFilter(logging.Filter):  # 给每条日志补 request_id 字段
    def filter(self, record: logging.LogRecord) -> bool:  # 不过滤掉记录，只改属性
        record.request_id = current_request_id() or getattr(record, "request_id", None) or "-"  # 无请求时用短横线
        return True  # 始终放行


def current_request_id() -> str | None:  # 读取当前协程/任务上的请求 ID
    return _REQUEST_ID.get()  # ContextVar 默认可能为 None


def set_request_id(request_id: str | None) -> None:  # 中间件进入时设置、离开时清空
    _REQUEST_ID.set(request_id)  # 写入当前上下文


def get_logger(name: str = "") -> logging.Logger:  # 取 erp 或 erp.xxx 子记录器
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)  # 空名则用根 logger


def _log_level(value: str) -> int:  # 把配置字符串转成 logging 级别整数
    level = logging.getLevelName((value or "INFO").upper())  # 空值回落到 INFO
    return level if isinstance(level, int) else logging.INFO  # 未知名称时 getLevelName 返回字符串，改用 INFO


def _install_record_factory() -> None:  # 让所有 LogRecord 天生带 request_id，避免 Formatter 缺字段
    global _factory_installed  # 进程内只安装一次
    if _factory_installed:  # 已经替换过工厂
        return  # 避免层层包装
    previous = logging.getLogRecordFactory()  # 保留原工厂以便链式调用

    def record_factory(*args, **kwargs):  # 新工厂：先建记录再填 request_id
        record = previous(*args, **kwargs)  # 交给原工厂创建
        record.request_id = current_request_id() or "-"  # 无请求上下文则占位
        return record  # 返回补全后的记录

    logging.setLogRecordFactory(record_factory)  # 全局替换
    _factory_installed = True  # 标记已安装


def configure_logging(*, force: bool = False, to_file: bool | None = None) -> None:  # 给 erp logger 挂控制台与滚动文件
    """Attach handlers to the `erp` logger. Safe to call more than once."""
    global _configured  # 记住是否已配置，避免重复 handler
    if _configured and not force:  # 已配置且未强制重建
        return  # 幂等返回

    from backend.app.core.config import BACKEND_DIR, get_settings  # 延迟导入，避免循环依赖

    settings = get_settings()  # 读日志级别与目录
    level = _log_level(settings.log_level)  # 解析级别
    use_file = settings.log_to_file if to_file is None else to_file  # 参数可覆盖配置
    under_pytest = "pytest" in sys.modules  # 测试时不抢 stdout，交给 pytest caplog

    _install_record_factory()  # 确保 Formatter 总能读到 request_id
    logger = logging.getLogger(LOGGER_NAME)  # 业务根 logger
    logger.setLevel(level)  # 根级别
    logger.handlers.clear()  # 清掉旧 handler，force 重建时不会重复打印
    logger.propagate = under_pytest  # 测试时向上冒泡；运行时自己处理，避免打两遍

    formatter = logging.Formatter(  # 统一格式：时间 级别 [request_id] logger: 消息
        "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",  # 含请求关联 ID
        datefmt="%Y-%m-%d %H:%M:%S",  # 人类可读时间
    )  # Formatter 结束
    log_filter = RequestIdFilter()  # 过滤器实例可复用到多个 handler
    logger.filters.clear()  # 去掉旧过滤器
    logger.addFilter(log_filter)  # 根 logger 也打上 request_id

    if not under_pytest:  # 非正式测试才挂控制台
        stream = logging.StreamHandler(sys.stdout)  # 写标准输出，便于容器采集
        stream.setFormatter(formatter)  # 同一格式
        stream.addFilter(log_filter)  # handler 级再保证一次
        logger.addHandler(stream)  # 挂到根 logger

    if use_file:  # 需要落盘
        log_dir = Path(settings.log_dir) if settings.log_dir else BACKEND_DIR / "logs"  # 自定义目录或默认 logs
        log_dir.mkdir(parents=True, exist_ok=True)  # 目录不存在则创建
        file_handler = TimedRotatingFileHandler(  # 每天切割，保留两周
            log_dir / "app.log",  # 当前文件名
            when="midnight",  # 零点滚动
            backupCount=14,  # 保留 14 个备份
            encoding="utf-8",  # 中文日志用 UTF-8
        )  # 文件 handler 参数结束
        file_handler.setFormatter(formatter)  # 与控制台同一格式
        file_handler.addFilter(log_filter)  # 补 request_id
        logger.addHandler(file_handler)  # 挂文件 handler

    _configured = True  # 标记已完成
    get_logger("runtime").info(  # 启动一条就绪日志，确认级别与是否写文件
        "logging ready level=%s file=%s",  # 便于对照配置
        logging.getLevelName(level),  # 级别名
        "on" if use_file else "off",  # 文件开关
    )  # info 调用结束
