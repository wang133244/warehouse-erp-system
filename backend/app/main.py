"""应用工厂。组装日志、CORS、中间件和各业务路由；库存写入口仍在 inventory_service。"""

from fastapi import FastAPI  # 引入 FastAPI 应用类
from fastapi.middleware.cors import CORSMiddleware  # 引入跨域中间件

from backend.app.controllers import (  # 从控制器包导入各业务路由模块
    alerts,  # 预警路由
    approvals,  # 审批路由
    audit_logs,  # 审计日志路由
    auth,  # 登录鉴权路由
    catalog,  # 主数据目录路由
    followup,  # 后续运营（用户/助手/看板等）路由
    inbounds,  # 入库单路由
    inventory,  # 库存查询路由
    outbounds,  # 出库单路由
    picking_tasks,  # 拣货任务路由
    reports,  # 报表路由
    stock_counts,  # 盘点单路由
    transfers,  # 调拨单路由
)  # 控制器导入结束
from backend.app.core.config import get_settings  # 读取运行时配置
from backend.app.core.logging import configure_logging, get_logger  # 配置日志并获取记录器
from backend.app.core.middleware import install_exception_handlers, install_middleware  # 安装请求中间件与异常处理


def create_app() -> FastAPI:  # 组装并返回 FastAPI 实例
    configure_logging()  # 先初始化日志，后续启动信息才能落盘
    settings = get_settings()  # 读取环境配置（CORS、env 等）
    application = FastAPI(title="智能 ERP 仓管系统后端", version="0.2.0", description="Mega Star 仓储管理模块 API")  # 创建带标题与版本的应用
    application.add_middleware(  # 挂载 CORS，允许前端跨域带凭证访问
        CORSMiddleware,  # 使用 Starlette CORS 中间件
        allow_origins=settings.cors_origin_list,  # 允许的前端来源列表
        allow_credentials=True,  # 允许携带 Cookie/Authorization
        allow_methods=["*"],  # 允许全部 HTTP 方法
        allow_headers=["*"],  # 允许全部请求头
    )  # CORS 中间件参数结束
    install_middleware(application)  # 安装请求 ID 与访问日志中间件
    install_exception_handlers(application)  # 把业务异常转成统一 JSON 信封
    for router in (  # 逐个挂载 v1 业务路由
        auth.router,  # 认证
        catalog.router,  # 主数据
        inventory.router,  # 库存
        inbounds.router,  # 入库
        outbounds.router,  # 出库
        picking_tasks.router,  # 拣货
        stock_counts.router,  # 盘点
        transfers.router,  # 调拨
        approvals.router,  # 审批
        audit_logs.router,  # 审计
        alerts.router,  # 预警
        followup.users_router,  # 用户管理
        followup.roles_router,  # 角色管理
        followup.receivings_router,  # 收货复核相关
        followup.reviews_router,  # 复核
        followup.agents_router,  # 智能助手
        followup.exports_router,  # 导出
        followup.dashboard_router,  # 看板
        followup.system_router,  # 系统信息
        reports.router,  # 报表
    ):  # 路由元组结束
        application.include_router(router, prefix="/api/v1")  # 统一挂到 /api/v1 前缀下

    @application.get("/health", tags=["system"])  # 探活接口，不走业务鉴权
    def health() -> dict[str, str]:  # 返回简单存活状态
        return {"status": "ok"}  # 进程可响应即视为健康

    get_logger("runtime").info("app created env=%s", settings.app_env)  # 记录当前环境，便于排查启动配置
    return application  # 把组装好的应用交给 ASGI 服务器


app = create_app()  # 模块导入时创建全局 app，供 uvicorn 直接加载
