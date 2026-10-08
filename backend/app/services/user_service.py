"""管理员创建用户、绑定角色与仓库范围。"""

from __future__ import annotations  # 启用延后求值注解，支持前向引用类型

from sqlalchemy import select  # 导入查询构造器
from sqlalchemy.orm import Session  # 导入 ORM 会话类型

from backend.app.core.errors import AppError  # 导入业务异常
from backend.app.core.security import hash_password  # 导入密码哈希函数
from backend.app.models import Role, UserAccount, UserRole, UserWarehouseScope, Warehouse  # 导入用户、角色与仓库模型
from backend.app.schemas.followup import UserCreate, UserUpdate  # 导入用户创建/更新入参
from backend.app.services.inventory_service import (  # 从库存服务导入幂等与审计辅助
    existing_idempotent_response,  # 查询已缓存的幂等响应
    record_idempotent_response,  # 写入幂等响应缓存
    require_idempotency_key,  # 校验幂等键必填
    write_audit,  # 写审计日志
)  # 结束 inventory_service 导入

ALLOWED_ROLES = frozenset({"warehouse_manager", "warehouse_operator", "admin", "operator", "viewer"})  # 允许绑定的角色编码集合
ROLE_ALIASES = {"operator": "warehouse_operator", "warehouse_operator": "operator"}  # 角色编码别名映射


def account_name(db: Session, user_id: int | None) -> str | None:  # 按用户 ID 解析用户名
    if not user_id:  # 未提供用户 ID 则无法解析
        return None  # 返回空表示匿名/未知
    user = db.get(UserAccount, user_id)  # 按主键读取用户账号
    return user.username if user else None  # 账号存在则返回用户名，否则为空


def account_names(db: Session, user_ids: set[int]) -> dict[int, str]:  # 批量把用户 ID 映射为用户名
    if not user_ids:  # 空集合无需查库
        return {}  # 直接返回空映射
    return {  # 构造 user_id -> username 字典
        user.user_id: user.username  # 以用户主键为键、用户名为值
        for user in db.scalars(select(UserAccount).where(UserAccount.user_id.in_(user_ids)))  # 仅查询传入的用户 ID
    }  # 结束批量用户名映射


def _roles_for(db: Session, user_id: int) -> list[str]:  # 查询指定用户已绑定的角色编码
    return list(  # 把标量结果转成列表
        db.scalars(  # 执行查询并取标量列
            select(Role.role_code)  # 只要角色编码
            .join(UserRole, UserRole.role_id == Role.role_id)  # 通过用户角色关联表连接
            .where(UserRole.user_id == user_id)  # 限定当前用户
            .order_by(Role.role_code)  # 按角色编码排序，保证稳定输出
        )  # 结束 scalars 查询
    )  # 结束角色编码列表


def _warehouses_for(db: Session, user_id: int) -> list[int]:  # 查询指定用户授权仓库 ID
    return list(  # 把标量结果转成列表
        db.scalars(  # 执行查询并取标量列
            select(UserWarehouseScope.warehouse_id)  # 只要仓库 ID
            .where(UserWarehouseScope.user_id == user_id)  # 限定当前用户
            .order_by(UserWarehouseScope.warehouse_id)  # 按仓库 ID 排序
        )  # 结束 scalars 查询
    )  # 结束仓库 ID 列表


def serialize_user(db: Session, user: UserAccount) -> dict:  # 把用户实体序列化为接口字典
    return {  # 组装用户详情
        "user_id": user.user_id,  # 用户主键
        "username": user.username,  # 登录名
        "display_name": user.display_name,  # 显示名
        "is_active": user.is_active,  # 是否启用
        "roles": _roles_for(db, user.user_id),  # 已绑定角色编码
        "warehouse_ids": _warehouses_for(db, user.user_id),  # 已授权仓库
    }  # 结束用户序列化


def list_users(db: Session, keyword: str | None = None) -> dict:  # 列出用户，可选关键字过滤
    users = list(db.scalars(select(UserAccount).order_by(UserAccount.user_id)))  # 按 ID 取出全部用户
    items = [serialize_user(db, user) for user in users]  # 逐条序列化
    if keyword:  # 传入关键字则做前端友好的本地过滤
        needle = keyword.strip().lower()  # 去掉空白并转小写便于包含匹配
        items = [  # 按用户名、显示名、角色或启用状态过滤
            item  # 保留命中的用户项
            for item in items  # 遍历已序列化列表
            if needle in item["username"].lower()  # 用户名包含关键字
            or needle in item["display_name"].lower()  # 显示名包含关键字
            or any(needle in role.lower() for role in item["roles"])  # 任一角色编码包含关键字
            or needle in ("启用" if item["is_active"] else "停用")  # 也支持按启用/停用中文状态搜
        ]  # 结束过滤列表
    return {"total": len(items), "items": items}  # 返回总数与列表


def list_roles(db: Session) -> dict:  # 列出全部角色供下拉选择
    roles = list(db.scalars(select(Role).order_by(Role.role_id)))  # 按角色 ID 取出全部角色
    return {  # 组装角色列表响应
        "items": [  # 角色项数组
            {"role_id": role.role_id, "role_code": role.role_code, "role_name": role.role_name}  # 输出角色主键、编码与名称
            for role in roles  # 遍历全部角色
        ]  # 结束角色项数组
    }  # 结束角色列表响应


def _resolve_roles(db: Session, role_codes: list[str]) -> list[Role]:  # 把角色编码解析成 Role 实体
    unique_codes = list(dict.fromkeys(role_codes))  # 保序去重，避免重复绑定
    if any(code not in ALLOWED_ROLES for code in unique_codes):  # 存在不在白名单中的编码
        raise AppError("ROLE_INVALID", "角色不合法", 422, {"roles": unique_codes})  # 拒绝非法角色
    roles: list[Role] = []  # 收集解析到的角色实体
    found: set[str] = set()  # 记录已加入的角色编码，防止别名重复
    for code in unique_codes:  # 逐个解析编码
        role = db.scalar(select(Role).where(Role.role_code == code))  # 先按原编码查角色
        if role is None:  # 原编码未命中则尝试别名
            alias = ROLE_ALIASES.get(code)  # 取出别名编码
            role = db.scalar(select(Role).where(Role.role_code == alias)) if alias else None  # 有别名再查一次
        if role is None:  # 原编码与别名都找不到
            raise AppError("ROLE_INVALID", "角色不合法", 422, {"roles": [code]})  # 报该编码非法
        if role.role_code not in found:  # 尚未加入过该实际角色
            roles.append(role)  # 加入结果列表
            found.add(role.role_code)  # 标记该编码已处理
    return roles  # 返回去重后的角色实体


def _replace_roles(db: Session, user_id: int, roles: list[Role]) -> None:  # 用新角色集合覆盖用户角色
    existing = list(db.scalars(select(UserRole).where(UserRole.user_id == user_id)))  # 查出当前绑定行
    for row in existing:  # 逐条删除旧绑定
        db.delete(row)  # 删除用户角色关联
    for role in roles:  # 写入新绑定
        db.add(UserRole(user_id=user_id, role_id=role.role_id))  # 新增用户与角色关联


def _replace_warehouses(db: Session, user_id: int, warehouse_ids: list[int]) -> None:  # 用新仓库范围覆盖用户授权
    unique_ids = list(dict.fromkeys(warehouse_ids))  # 保序去重仓库 ID
    if unique_ids:  # 有仓库才校验是否存在
        found = set(db.scalars(select(Warehouse.warehouse_id).where(Warehouse.warehouse_id.in_(unique_ids))))  # 查出真实存在的仓库
        missing = [warehouse_id for warehouse_id in unique_ids if warehouse_id not in found]  # 找出不存在的 ID
        if missing:  # 存在无效仓库
            raise AppError("WAREHOUSE_NOT_FOUND", "仓库不存在", 404, {"warehouse_ids": missing})  # 拒绝绑定不存在的仓库
    existing = list(  # 查出当前仓库范围行
        db.scalars(select(UserWarehouseScope).where(UserWarehouseScope.user_id == user_id))  # 按用户过滤范围
    )  # 结束现有范围查询
    for row in existing:  # 逐条删除旧范围
        db.delete(row)  # 删除用户仓库范围
    for warehouse_id in unique_ids:  # 写入新范围
        db.add(UserWarehouseScope(user_id=user_id, warehouse_id=warehouse_id))  # 新增用户仓库授权


def create_user(db: Session, payload: UserCreate, actor_id: int, key: str | None) -> dict:  # 管理员创建用户
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, actor_id, key)  # 查是否已成功创建过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    if db.scalar(select(UserAccount).where(UserAccount.username == payload.username)):  # 用户名已占用
        raise AppError("USERNAME_EXISTS", "用户名已存在", 409)  # 拒绝重复用户名
    user = UserAccount(  # 构造新用户实体
        username=payload.username,  # 登录名
        password_hash=hash_password(payload.password),  # 密码入库前先哈希
        display_name=payload.display_name,  # 显示名
        is_active=payload.is_active,  # 初始启用状态
    )  # 结束用户实体构造
    db.add(user)  # 加入会话
    db.flush()  # 刷盘拿到 user_id
    _replace_roles(db, user.user_id, _resolve_roles(db, payload.roles))  # 绑定角色
    _replace_warehouses(db, user.user_id, payload.warehouse_ids)  # 绑定仓库范围
    db.flush()  # 刷盘角色与范围
    body = serialize_user(db, user)  # 序列化创建结果
    record_idempotent_response(  # 缓存创建响应，防止重复提交再建账号
        db,  # 当前会话
        user_id=actor_id,  # 操作者 ID
        key=key,  # 幂等键
        method="POST",  # 创建接口方法
        path="/api/v1/users",  # 创建接口路径
        body=body,  # 响应体
        status=201,  # 创建成功状态码
    )  # 结束幂等缓存
    write_audit(  # 记录创建审计
        db,  # 当前会话
        user_id=actor_id,  # 操作者
        action="user_create",  # 审计动作
        entity_type="user_account",  # 实体类型
        entity_id=user.user_id,  # 新用户 ID
        after=body,  # 创建后快照
    )  # 结束审计写入
    db.commit()  # 提交事务
    return body  # 返回创建结果


def update_user(db: Session, user_id: int, payload: UserUpdate, actor_id: int, key: str | None) -> dict:  # 管理员更新用户
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, actor_id, key)  # 查是否已成功更新过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    user = db.get(UserAccount, user_id)  # 按主键读取用户
    if user is None:  # 用户不存在
        raise AppError("NOT_FOUND", "用户不存在", 404)  # 返回 404
    if payload.display_name is not None:  # 入参带了显示名
        user.display_name = payload.display_name  # 更新显示名
    if payload.password is not None:  # 入参带了新密码
        user.password_hash = hash_password(payload.password)  # 重新哈希后覆盖
    if payload.is_active is not None:  # 入参带了启用状态
        user.is_active = payload.is_active  # 更新启用/停用
    if payload.roles is not None:  # 入参带了角色列表
        _replace_roles(db, user_id, _resolve_roles(db, payload.roles))  # 覆盖角色
    if payload.warehouse_ids is not None:  # 入参带了仓库范围
        _replace_warehouses(db, user_id, payload.warehouse_ids)  # 覆盖仓库授权
    db.flush()  # 刷盘变更
    body = serialize_user(db, user)  # 序列化更新结果
    record_idempotent_response(  # 缓存更新响应
        db,  # 当前会话
        user_id=actor_id,  # 操作者 ID
        key=key,  # 幂等键
        method="PATCH",  # 更新接口方法
        path=f"/api/v1/users/{user_id}",  # 更新接口路径
        body=body,  # 响应体
        status=200,  # 更新成功状态码
    )  # 结束幂等缓存
    write_audit(  # 记录更新审计
        db,  # 当前会话
        user_id=actor_id,  # 操作者
        action="user_update",  # 审计动作
        entity_type="user_account",  # 实体类型
        entity_id=user_id,  # 被改用户 ID
        after=body,  # 更新后快照
    )  # 结束审计写入
    db.commit()  # 提交事务
    return body  # 返回更新结果


def delete_user(db: Session, user_id: int, actor_id: int, key: str | None) -> dict:  # 停用用户（逻辑删除）
    key = require_idempotency_key(key)  # 强制要求幂等键
    prior = existing_idempotent_response(db, actor_id, key)  # 查是否已成功删除过
    if prior:  # 命中幂等缓存
        return prior  # 直接回放上次响应
    if user_id == actor_id:  # 禁止删自己
        raise AppError("USER_SELF_DELETE", "不能删除当前登录账号", 409)  # 避免把自己锁出系统
    user = db.get(UserAccount, user_id)  # 按主键读取用户
    body = {"user_id": user_id, "deleted": True}  # 统一删除响应体，即使用户已不存在也幂等成功
    if user is not None:  # 用户仍存在才做停用
        roles = _roles_for(db, user_id)  # 读取当前角色
        if "admin" in roles:  # 目标是管理员时要保护最后一个管理员
            admin_ids = list(  # 查出所有仍启用的管理员
                db.scalars(  # 取用户 ID 标量
                    select(UserRole.user_id)  # 从用户角色关联取用户
                    .join(Role, Role.role_id == UserRole.role_id)  # 连接角色表
                    .join(UserAccount, UserAccount.user_id == UserRole.user_id)  # 连接账号表以过滤启用状态
                    .where(Role.role_code == "admin", UserAccount.is_active.is_(True))  # 只要启用中的 admin
                )  # 结束 scalars 查询
            )  # 结束管理员 ID 列表
            if len(set(admin_ids)) <= 1:  # 只剩一个启用管理员
                raise AppError("LAST_ADMIN", "不能删除最后一个管理员", 409)  # 禁止删光管理员
        user.is_active = False  # 逻辑删除：停用账号
        db.flush()  # 刷盘停用状态
        write_audit(  # 记录删除审计
            db,  # 当前会话
            user_id=actor_id,  # 操作者
            action="user_delete",  # 审计动作
            entity_type="user_account",  # 实体类型
            entity_id=user_id,  # 被删用户 ID
            after=body,  # 删除后快照
        )  # 结束审计写入
    record_idempotent_response(  # 缓存删除响应
        db,  # 当前会话
        user_id=actor_id,  # 操作者 ID
        key=key,  # 幂等键
        method="DELETE",  # 删除接口方法
        path=f"/api/v1/users/{user_id}",  # 删除接口路径
        body=body,  # 响应体
    )  # 结束幂等缓存
    db.commit()  # 提交事务
    return body  # 返回删除结果
