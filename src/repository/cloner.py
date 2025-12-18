import shutil
from pathlib import Path
from git import Repo
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryCloner:
    """Gitリポジトリのクローン・更新を管理"""

    def __init__(self):
        self.clone_dir = Path(settings.CLONE_DIR)
        self.clone_dir.mkdir(parents=True, exist_ok=True)

    async def clone_or_update(self, repo_url: str, branch: str = "main") -> Path:
        """リポジトリをクローンまたは更新

        Args:
            repo_url: GitリポジトリURL
            branch: ブランチ名（デフォルト: main）

        Returns:
            Path: クローンされたリポジトリのパス

        Raises:
            Exception: クローンまたは更新に失敗した場合
        """
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = self.clone_dir / repo_name

        try:
            if repo_path.exists():
                logger.info(f"Updating existing repo: {repo_path}")
                repo = Repo(repo_path)
                origin = repo.remotes.origin
                origin.fetch()
                repo.git.reset("--hard", f"origin/{branch}")
            else:
                logger.info(f"Cloning repo: {repo_url}")
                Repo.clone_from(
                    repo_url, repo_path, depth=settings.CLONE_DEPTH, branch=branch
                )

            logger.info(f"Repository ready at: {repo_path}")
            return repo_path

        except Exception as e:
            logger.error(f"Failed to clone/update repo: {e}", exc_info=True)
            raise

    def cleanup(self, repo_path: Path):
        """クローンしたリポジトリを削除

        Args:
            repo_path: 削除するリポジトリのパス
        """
        try:
            if repo_path.exists():
                shutil.rmtree(repo_path)
                logger.info(f"Cleaned up repo: {repo_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup repo: {e}", exc_info=True)
