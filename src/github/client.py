import requests
import asyncio
from typing import Dict, Any
from datetime import datetime
from src.config import settings
from src.utils.logger import get_logger
from src.utils.retry import retry_with_backoff
from src.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)


class GitHubAuthError(Exception):
    """GitHub認証エラー"""

    pass


class GitHubClient:
    """GitHub GraphQL APIクライアント"""

    API_URL = "https://api.github.com/graphql"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }
        self.rate_limiter = RateLimiter(
            max_requests=settings.GITHUB_API_MAX_REQUESTS,
            window_seconds=settings.GITHUB_API_WINDOW_SECONDS,
        )

    @retry_with_backoff(max_retries=3)
    async def execute_query(
        self, query: str, variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """GraphQLクエリを実行

        Args:
            query: GraphQLクエリ文字列
            variables: クエリ変数

        Returns:
            Dict[str, Any]: クエリ結果

        Raises:
            Exception: GraphQLエラーまたはHTTPエラー
        """
        await self.rate_limiter.acquire()

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        # requestsは同期ライブラリなので、非同期コンテキストで実行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                self.API_URL, json=payload, headers=self.headers, timeout=30
            ),
        )
        response.raise_for_status()

        data = response.json()
        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            raise Exception(f"GraphQL errors: {data['errors']}")

        return data["data"]

    async def check_rate_limit(self) -> Dict[str, Any]:
        """現在のレート制限状況を取得

        Returns:
            Dict containing limit, remaining, and resetAt
        """
        from src.github.queries import CHECK_RATE_LIMIT

        result = await self.execute_query(CHECK_RATE_LIMIT)
        return result["rateLimit"]

    async def wait_for_rate_limit_reset(self):
        """レート制限リセットまで待機"""
        rate_limit = await self.check_rate_limit()

        if rate_limit["remaining"] < 100:  # 残り100未満で警告
            logger.warning(
                f"GitHub API rate limit low: {rate_limit['remaining']}/{rate_limit['limit']}"
            )

            if rate_limit["remaining"] == 0:
                reset_time = datetime.fromisoformat(
                    rate_limit["resetAt"].replace("Z", "+00:00")
                )
                wait_seconds = (reset_time - datetime.now()).total_seconds()

                logger.warning(f"Rate limit exceeded. Waiting {wait_seconds}s")
                await asyncio.sleep(wait_seconds + 10)

    async def validate_token(self) -> bool:
        """トークンの有効性を検証

        Returns:
            bool: トークンが有効ならTrue

        Raises:
            GitHubAuthError: トークンが無効な場合
        """
        from src.github.queries import VALIDATE_TOKEN

        try:
            result = await self.execute_query(VALIDATE_TOKEN)
            logger.info(f"GitHub token valid for user: {result['viewer']['login']}")
            return True
        except Exception as e:
            logger.error(f"GitHub token validation failed: {e}")
            raise GitHubAuthError("Invalid GitHub token") from e
