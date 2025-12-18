import asyncio
import time
from collections import deque


class RateLimiter:
    """シンプルなレート制限実装

    スライディングウィンドウ方式でAPIリクエストのレート制限を管理します。
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """RateLimiterの初期化

        Args:
            max_requests: ウィンドウ内での最大リクエスト数
            window_seconds: ウィンドウの長さ（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """リクエストを実行する許可を取得

        レート制限に達している場合は、リセットまで待機します。
        """
        async with self._lock:
            now = time.time()

            # ウィンドウ外のリクエストを削除
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            # レート制限チェック
            if len(self.requests) >= self.max_requests:
                oldest = self.requests[0]
                sleep_time = (oldest + self.window_seconds) - now
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()

            self.requests.append(now)

    def get_remaining(self) -> int:
        """残りのリクエスト可能数を取得

        Returns:
            int: 残りのリクエスト数
        """
        now = time.time()
        # ウィンドウ内のリクエストをカウント
        valid_requests = [r for r in self.requests if r >= now - self.window_seconds]
        return max(0, self.max_requests - len(valid_requests))
