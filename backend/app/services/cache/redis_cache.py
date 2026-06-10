"""
Redis Cache — graceful fallback when Redis is unavailable.
Caches query embeddings and RAG results to reduce latency.
"""
import json
import hashlib
import logging
from typing import Optional, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600  # 1 hour default
_redis_client = None
_redis_available = None


async def _get_redis():
    global _redis_client, _redis_available

    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        import aioredis
        _redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await _redis_client.ping()
        _redis_available = True
        logger.info("✅ Redis cache connected")
        return _redis_client
    except Exception as e:
        _redis_available = False
        logger.warning(f"⚠️ Redis unavailable — running without cache: {e}")
        return None


def _make_key(prefix: str, value: str) -> str:
    """Create a short Redis key from prefix + hashed value."""
    h = hashlib.md5(value.encode()).hexdigest()[:16]
    return f"insightflow:{prefix}:{h}"


async def cache_get(prefix: str, key: str) -> Optional[Any]:
    """Retrieve a cached value. Returns None if not found or Redis unavailable."""
    redis = await _get_redis()
    if not redis:
        return None
    try:
        raw = await redis.get(_make_key(prefix, key))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug(f"Cache get error: {e}")
    return None


async def cache_set(prefix: str, key: str, value: Any, ttl: int = CACHE_TTL_SECONDS):
    """Store a value in cache. Silently skips if Redis unavailable."""
    redis = await _get_redis()
    if not redis:
        return
    try:
        await redis.setex(_make_key(prefix, key), ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.debug(f"Cache set error: {e}")


async def cache_embedding(text: str, embedding: List[float]):
    """Cache a text embedding."""
    await cache_set("emb", text, embedding, ttl=86400)  # 24h


async def get_cached_embedding(text: str) -> Optional[List[float]]:
    """Get a cached embedding."""
    return await cache_get("emb", text)


async def cache_query_result(question: str, department: str, result: dict):
    """Cache a RAG query result."""
    key = f"{department}:{question}"
    await cache_set("query", key, result, ttl=CACHE_TTL_SECONDS)


async def get_cached_query_result(question: str, department: str) -> Optional[dict]:
    """Get a cached RAG result."""
    key = f"{department}:{question}"
    return await cache_get("query", key)
