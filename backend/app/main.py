from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.v1 import alerts, audit_logs, auth, catalog, inbounds, inventory, outbounds, picking_tasks
from backend.app.core.config import get_settings
from backend.app.core.middleware import install_exception_handlers, install_middleware
from backend.app.db.models import InboundOrder, OutboundOrder, StockBalance
from backend.app.db.session import get_db


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="智能 ERP 仓管系统后端", version="0.1.0", description="Mega Star 仓储管理模块 API")
    application.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    install_middleware(application)
    install_exception_handlers(application)
    for router in (auth.router, catalog.router, inventory.router, inbounds.router, outbounds.router, picking_tasks.router, audit_logs.router, alerts.router):
        application.include_router(router, prefix="/api/v1")

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/api/v1/dashboard/summary", tags=["看板"])
    def dashboard_summary(db: Session = __import__("fastapi").Depends(get_db)) -> dict:
        total, reserved = db.execute(select(func.coalesce(func.sum(StockBalance.quantity), 0), func.coalesce(func.sum(StockBalance.reserved_quantity), 0))).one()
        return {"stock_quantity": int(total), "reserved_quantity": int(reserved), "available_quantity": int(total-reserved), "inbound_draft": db.scalar(select(func.count()).select_from(InboundOrder).where(InboundOrder.status == "draft")) or 0, "outbound_pending": db.scalar(select(func.count()).select_from(OutboundOrder).where(OutboundOrder.status.in_(("draft", "allocated")))) or 0}

    return application


app = create_app()
