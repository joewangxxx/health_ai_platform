"""
Task 108: Redis Async Cache Manager
===================================
提供异步 Redis 缓存服务，用于优化 LLM 响应和高频请求。
"""
import json
import hashlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Redis 是可选依赖，优雅处理导入失败
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None


class CacheManager:
    """
    Redis 异步缓存管理器 (Singleton Pattern)
    
    Features:
    - 自动 JSON 序列化/反序列化
    - MD5 Key 生成器
    - 连接池管理
    - 优雅降级 (Redis 不可用时返回 None)
    """
    
    _instance: Optional["CacheManager"] = None
    _redis: Optional[Any] = None
    _initialized: bool = False
    _availability_warning_emitted: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def init(cls, redis_url: str = "redis://localhost:6379/0") -> bool:
        """
        初始化 Redis 连接池
        
        Args:
            redis_url: Redis 连接 URL
            
        Returns:
            bool: 是否成功连接
        """
        if not REDIS_AVAILABLE:
            if not cls._availability_warning_emitted:
                logger.warning("Redis cache unavailable; continuing without cache.")
                cls._availability_warning_emitted = True
            return False
        
        if cls._initialized:
            return True
        
        try:
            cls._redis = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # 测试连接
            await cls._redis.ping()
            cls._initialized = True
            logger.info(f"✅ Redis 缓存连接成功: {redis_url}")
            return True
        except Exception as e:
            if not cls._availability_warning_emitted:
                logger.warning("Redis cache unavailable; continuing without cache (%s).", e)
                cls._availability_warning_emitted = True
            cls._redis = None
            cls._initialized = False
            return False
    
    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """
        获取缓存值 (自动 JSON 解码)
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或 None
        """
        if not cls._redis:
            return None
        
        try:
            value = await cls._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError:
            return value  # 返回原始字符串
        except Exception as e:
            logger.error(f"Redis GET 错误 [{key}]: {e}")
            return None
    
    @classmethod
    async def set(
        cls, 
        key: str, 
        value: Any, 
        ttl: int = 3600
    ) -> bool:
        """
        设置缓存值 (自动 JSON 编码)
        
        Args:
            key: 缓存键
            value: 缓存值 (会被 JSON 序列化)
            ttl: 过期时间 (秒)，默认 1 小时
            
        Returns:
            bool: 是否成功
        """
        if not cls._redis:
            return False
        
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            await cls._redis.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis SET 错误 [{key}]: {e}")
            return False
    
    @classmethod
    async def delete(cls, key: str) -> bool:
        """删除缓存键"""
        if not cls._redis:
            return False
        
        try:
            await cls._redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 错误 [{key}]: {e}")
            return False
    
    @classmethod
    async def delete_pattern(cls, pattern: str) -> int:
        """
        Task 113: 删除匹配特定模式的所有 Key
        
        Args:
            pattern: Redis 通配符模式，例如 "diet_plan:user_123:*"
            
        Returns:
            int: 删除的 Key 数量
            
        Note:
            生产环境使用 scan_iter 避免阻塞
        """
        if not cls._redis:
            return 0
        
        try:
            keys = []
            async for key in cls._redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await cls._redis.delete(*keys)
                logger.info(f"🗑️ Invalidated {len(keys)} cache keys for pattern: {pattern}")
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN 错误 [{pattern}]: {e}")
            return 0
    
    @classmethod
    async def invalidate_user_cache(cls, user_id: int) -> dict:
        """
        Task 113: 清除指定用户的所有 AI 相关缓存
        
        当用户健康数据更新时调用，确保后续请求获取新鲜数据。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            dict: 各类型删除的 Key 数量
        """
        results = {}
        
        # 清除食谱缓存
        results["diet_plan"] = await cls.delete_pattern(f"diet_plan:{user_id}:*")
        
        # 清除聊天缓存
        results["chat_response"] = await cls.delete_pattern(f"chat_response:{user_id}:*")
        
        # 清除风险评估缓存 (预留)
        results["risk_assessment"] = await cls.delete_pattern(f"risk_assessment:{user_id}:*")
        
        total = sum(results.values())
        if total > 0:
            logger.info(f"🗑️ User {user_id} cache invalidated: {results}")
        
        return results
    
    @classmethod
    async def close(cls) -> None:
        """关闭 Redis 连接"""
        if cls._redis:
            try:
                await cls._redis.close()
                logger.info("✅ Redis 连接已关闭")
            except Exception as e:
                logger.error(f"Redis 关闭错误: {e}")
            finally:
                cls._redis = None
                cls._initialized = False
                cls._availability_warning_emitted = False
    
    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """
        生成唯一的缓存键 (基于 MD5 哈希)
        
        Args:
            prefix: 键前缀 (如 "llm", "risk")
            *args: 用于生成哈希的参数
            **kwargs: 用于生成哈希的关键字参数
            
        Returns:
            str: 格式为 "prefix:md5_hash"
            
        Example:
            >>> CacheManager.generate_key("llm", "user_123", prompt="Hello")
            "llm:a1b2c3d4e5f6..."
        """
        # 将所有参数序列化为字符串
        components = [str(arg) for arg in args]
        for k, v in sorted(kwargs.items()):
            components.append(f"{k}={v}")
        
        raw_string = ":".join(components)
        hash_value = hashlib.md5(raw_string.encode()).hexdigest()
        
        return f"{prefix}:{hash_value}"
    
    @classmethod
    def is_available(cls) -> bool:
        """检查缓存是否可用"""
        return cls._initialized and cls._redis is not None


# 单例实例 (用于直接导入)
cache_manager = CacheManager()
