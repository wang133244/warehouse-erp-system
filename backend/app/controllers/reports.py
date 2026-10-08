"""ABC、周转、日报、周报、拣货效率。"""

from typing import Annotated  # 用于标注 FastAPI 依赖注入类型

from fastapi import APIRouter, Depends, Query  # 路由、依赖与查询参数
from sqlalchemy.orm import Session  # ORM 会话类型

from backend.app.models import UserAccount  # 当前用户实体类型
from backend.app.db.session import get_db  # 数据库会话依赖
from backend.app.dependencies import get_current_user  # 登录校验
from backend.app.services import report_service  # 报表计算服务

router = APIRouter(prefix="/reports", tags=["报表分析"])  # 报表路由，前缀 /reports


@router.get("/abc")  # GET /reports/abc，ABC 分类
def abc_report(  # 按出库量做 ABC 分析
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    days: int | None = Query(None, ge=1, le=365),  # 统计天数，可选 1–365
) -> dict:  # 返回报表字典
    return report_service.abc_report(db, days)  # 委托报表服务


@router.get("/turnover")  # GET /reports/turnover，周转分析
def turnover_report(  # 查询库存周转
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回报表字典
    return report_service.turnover_report(db)  # 委托报表服务


@router.get("/daily")  # GET /reports/daily，日报
def daily_report(  # 按天汇总作业量
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    days: int = Query(7, ge=1, le=31),  # 回溯天数，默认 7，最大 31
) -> dict:  # 返回报表字典
    return report_service.daily_report(db, days)  # 委托报表服务


@router.get("/weekly")  # GET /reports/weekly，周报
def weekly_report(  # 按周汇总作业量
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
    weeks: int = Query(4, ge=1, le=12),  # 回溯周数，默认 4，最大 12
) -> dict:  # 返回报表字典
    return report_service.weekly_report(db, weeks)  # 委托报表服务


@router.get("/picking-efficiency")  # GET /reports/picking-efficiency，拣货效率
def picking_efficiency_report(  # 查询拣货效率指标
    _: Annotated[UserAccount, Depends(get_current_user)],  # 要求已登录
    db: Annotated[Session, Depends(get_db)],  # 数据库会话
) -> dict:  # 返回报表字典
    return report_service.picking_efficiency(db)  # 委托报表服务
