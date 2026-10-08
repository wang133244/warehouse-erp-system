"""Redis 若可用则缓存看板/可用量；丢失可重建，不是库存事实源。"""

from __future__ import annotations  # 允许前置注解

import json  # JSON 序列化缓存值
import time  # TTL 过期判断与锁重试休眠
from threading import Lock  # 内存缓存互斥
from typing import Any, Protocol  # 任意 JSON 与缓存协议

DASHBOARD_SUMMARY_KEY = "erp:dashboard:summary"  # 看板摘要缓存键
DASHBOARD_CHARTS_KEY = "erp:dashboard:charts"  # 看板图表缓存键
STOCK_PREFIX = "erp:stock:"  # 库存相关键前缀（含锁）
DASHBOARD_TTL_SECONDS = 30  # 看板缓存秒数，短 TTL 避免脏读太久


class CacheBackend(Protocol):  # 内存与 Redis 共用的接口，调用方不关心后端
    def get(self, key: str) -> str | None: ...  # 取值，不存在或过期返回 None
    def set(self, key: str, value: str, ttl: int | None = None) -> None: ...  # 写入，ttl 为秒
    def set_nx(self, key: str, value: str, ttl: int | None = None) -> bool: ...  # 仅当不存在时写入，用于锁
    def delete(self, key: str) -> None: ...  # 删单个键
    def delete_prefix(self, prefix: str) -> None: ...  # 按前缀批量删除


class MemoryCache:  # 进程内字典缓存，单机开发或 Redis 不可用时使用
    def __init__(self) -> None:  # 初始化空表与锁
        self._data: dict[str, tuple[str, float | None]] = {}  # 值与过期时间戳
        self._lock = Lock()  # 保护并发读写

    def get(self, key: str) -> str | None:  # 读取并惰性删除过期项
        with self._lock:  # 持锁读
            item = self._data.get(key)  # 可能不存在
            if item is None:  # 未写入过
                return None  # 未命中
            value, expires_at = item  # 拆出值和过期点
            if expires_at is not None and expires_at < time.time():  # 已过期
                self._data.pop(key, None)  # 清掉脏键
                return None  # 视为未命中
            return value  # 仍有效

    def set(self, key: str, value: str, ttl: int | None = None) -> None:  # 覆盖写入
        expires_at = time.time() + ttl if ttl else None  # ttl 为空表示不过期
        with self._lock:  # 持锁写
            self._data[key] = (value, expires_at)  # 存值和过期时间

    def set_nx(self, key: str, value: str, ttl: int | None = None) -> bool:  # 不存在或已过期才写入
        expires_at = time.time() + ttl if ttl else None  # 新过期点
        with self._lock:  # 持锁判断+写入，避免竞态
            item = self._data.get(key)  # 现有项
            if item is not None:  # 键已存在
                _, current_exp = item  # 只关心是否仍有效
                if current_exp is None or current_exp >= time.time():  # 未过期（含永不过期）
                    return False  # 抢锁失败
            self._data[key] = (value, expires_at)  # 占用该键
            return True  # 抢锁成功

    def delete(self, key: str) -> None:  # 删除单键
        with self._lock:  # 持锁删
            self._data.pop(key, None)  # 不存在也安全

    def delete_prefix(self, prefix: str) -> None:  # 删除所有匹配前缀的键
        with self._lock:  # 先收集再删，避免迭代中修改
            for key in [item for item in self._data if item.startswith(prefix)]:  # 快照匹配键
                self._data.pop(key, None)  # 逐个删除


class RedisCache:  # Redis 实现，多进程共享
    def __init__(self, url: str) -> None:  # 连接并 ping 探活
        import redis  # 延迟导入，未装 Redis 依赖时仍可用内存后端

        self._client = redis.Redis.from_url(url, decode_responses=True)  # 返回 str 而不是 bytes
        self._client.ping()  # 连不上则抛错，外层回退内存

    def get(self, key: str) -> str | None:  # 按键读取缓存字符串
        value = self._client.get(key)  # 可能为 None
        return str(value) if value is not None else None  # 统一成 str | None

    def set(self, key: str, value: str, ttl: int | None = None) -> None:  # SET 或 SETEX
        if ttl:  # 带过期
            self._client.setex(key, ttl, value)  # 秒级 TTL
        else:  # 永不过期
            self._client.set(key, value)  # 普通 SET

    def set_nx(self, key: str, value: str, ttl: int | None = None) -> bool:  # SET NX，用于分布式锁
        if ttl:  # 带过期，避免死锁
            return bool(self._client.set(key, value, nx=True, ex=ttl))  # 不存在才写入并带过期
        return bool(self._client.set(key, value, nx=True))  # 仅 nx

    def delete(self, key: str) -> None:  # 删除单个缓存键
        self._client.delete(key)  # 忽略是否存在

    def delete_prefix(self, prefix: str) -> None:  # 扫描前缀后逐个删除
        for key in self._client.scan_iter(f"{prefix}*"):  # SCAN 避免 KEYS 阻塞
            self._client.delete(key)  # 逐键删除


_cache: CacheBackend | None = None  # 进程级单例，首次 get_cache 时选定后端
_backend_name = "memory"  # 当前后端名，供诊断接口返回


def reset_cache() -> None:  # 测试用：强制回到空的内存缓存
    global _cache, _backend_name  # 重置模块级状态
    _cache = MemoryCache()  # 新的空内存表
    _backend_name = "memory"  # 标记为内存


def get_cache() -> CacheBackend:  # 懒初始化：优先 Redis，失败则内存
    global _cache, _backend_name  # 写入单例
    if _cache is not None:  # 已经创建过
        return _cache  # 直接复用
    from backend.app.core.config import get_settings  # 延迟导入配置

    url = get_settings().redis_url  # 可能为空
    if url:  # 配置了 Redis
        try:  # 连接失败则降级
            _cache = RedisCache(url)  # ping 成功才算可用
            _backend_name = "redis"  # 标记 Redis
            return _cache  # 返回 Redis 后端
        except Exception as exc:  # 网络、认证、未安装 redis 包等
            from backend.app.core.logging import get_logger  # 延迟导入日志

            get_logger("cache").warning("redis unavailable, fallback to memory: %s", exc)  # 记录降级原因
    _cache = MemoryCache()  # 默认或降级后的内存缓存
    _backend_name = "memory"  # 标记内存
    return _cache  # 返回内存后端


def get_cache_backend() -> str:  # 供系统信息接口展示当前缓存实现
    get_cache()  # 确保已初始化
    return _backend_name  # "redis" 或 "memory"


def cache_get_json(key: str) -> Any | None:  # 读 JSON 对象
    raw = get_cache().get(key)  # 原始字符串
    if raw is None:  # 未命中
        return None  # 调用方应回源
    return json.loads(raw)  # 反序列化


def cache_set_json(key: str, value: Any, ttl: int | None = None) -> None:  # 写 JSON 对象
    get_cache().set(key, json.dumps(value, ensure_ascii=False), ttl)  # 保留中文，便于排查


def invalidate_stock_cache() -> None:  # 库存变更后丢掉看板与库存缓存
    cache = get_cache()  # 当前后端
    cache.delete(DASHBOARD_SUMMARY_KEY)  # 摘要
    cache.delete_prefix("erp:dashboard:")  # 看板全部子键
    cache.delete_prefix(STOCK_PREFIX)  # 库存键与锁前缀


def acquire_stock_lock(product_id: int, location_id: int, ttl: int = 15) -> str:  # 按商品+库位抢短锁，降低并发改库存冲突
    key = f"{STOCK_PREFIX}lock:{product_id}:{location_id}"  # 锁键
    cache = get_cache()  # 当前后端
    for _ in range(20):  # 最多重试 20 次
        if cache.set_nx(key, "1", ttl):  # 抢到锁
            return key  # 把键交给调用方，释放时用
        time.sleep(0.01)  # 10ms 后再试
    from backend.app.core.logging import get_logger  # 超时才导入日志

    get_logger("inventory").warning("stock lock timeout key=%s", key)  # 记超时，仍返回键以免调用方无法 release
    return key  # 超时也返回，调用方 finally 里会删


def release_stock_lock(key: str) -> None:  # 释放库存短锁
    get_cache().delete(key)  # 删除锁键
