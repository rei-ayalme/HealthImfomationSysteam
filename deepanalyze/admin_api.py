"""
DeepAnalyze API 服务器管理 API
处理管理端点，如线程清理和统计
"""

import time
from fastapi import APIRouter, Query

from config import CLEANUP_TIMEOUT_HOURS
from models import ThreadCleanupRequest, ThreadCleanupResponse, ThreadStatsResponse
from storage import storage


# 创建管理端点路由
router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/cleanup-threads", response_model=ThreadCleanupResponse)
async def manual_cleanup_threads(
    timeout_hours: int = Query(CLEANUP_TIMEOUT_HOURS, description="Timeout in hours for thread cleanup")
):
    """
    手动触发线程清理（管理 API）
    清理超过 timeout_hours 未访问的线程
    """
    try:
        cleaned_count = storage.cleanup_expired_threads(timeout_hours=timeout_hours)
        return ThreadCleanupResponse(
            status="success",
            cleaned_threads=cleaned_count,
            timeout_hours=timeout_hours,
            timestamp=int(time.time())
        )
    except Exception as e:
        return ThreadCleanupResponse(
            status="error",
            cleaned_threads=0,
            timeout_hours=timeout_hours,
            timestamp=int(time.time())
        )


@router.get("/threads-stats", response_model=ThreadStatsResponse)
async def get_threads_stats():
    """
    获取线程统计信息（管理 API）
    """
    with storage._lock:
        total_threads = len(storage.threads)
        now = int(time.time())

        # 按年龄类别统计线程
        recent_threads = 0  # < 1 小时
        old_threads = 0     # 1-12 小时
        expired_threads = 0 # > 12 小时

        for thread_data in storage.threads.values():
            last_accessed = thread_data.get("last_accessed_at", thread_data.get("created_at", 0))
            age_hours = (now - last_accessed) / 3600

            if age_hours < 1:
                recent_threads += 1
            elif age_hours <= CLEANUP_TIMEOUT_HOURS:
                old_threads += 1
            else:
                expired_threads += 1

    return ThreadStatsResponse(
        total_threads=total_threads,
        recent_threads=recent_threads,  # < 1 hour
        old_threads=old_threads,        # 1-12 hours
        expired_threads=expired_threads, # > 12 hours
        timeout_hours=CLEANUP_TIMEOUT_HOURS,
        timestamp=int(time.time())
    )