import asyncio
from functools import wraps
from typing import Callable, TypeVar
from src.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """指数バックオフでリトライするデコレータ

    Args:
        max_retries: 最大リトライ回数
        base_delay: 初回遅延時間（秒）

    Returns:
        デコレータ関数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise

                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                        f"after {delay}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)

        return wrapper

    return decorator
