from pathlib import Path
from typing import List, Dict
import os


class RepositoryAnalyzer:
    """ローカルリポジトリの分析"""

    IGNORE_DIRS = {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        "venv",
        "env",
    }
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rb",
        ".php",
        ".swift",
        ".kt",
    }

    def __init__(self, repo_path: Path):
        """
        Args:
            repo_path: 分析対象のリポジトリパス
        """
        self.repo_path = repo_path

    def get_file_tree(self, max_depth: int = 3) -> str:
        """ファイルツリーを取得（Markdown形式）

        Args:
            max_depth: 最大探索深度

        Returns:
            Markdown形式のファイルツリー
        """
        tree_lines = []

        def walk_dir(dir_path: Path, depth: int = 0):
            if depth > max_depth:
                return

            try:
                entries = sorted(
                    dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name)
                )
                for entry in entries:
                    if entry.name in self.IGNORE_DIRS:
                        continue

                    indent = "  " * depth
                    if entry.is_dir():
                        tree_lines.append(f"{indent}- {entry.name}/")
                        walk_dir(entry, depth + 1)
                    else:
                        tree_lines.append(f"{indent}- {entry.name}")
            except PermissionError:
                pass

        walk_dir(self.repo_path)
        return "\n".join(tree_lines)

    def search_files(self, pattern: str) -> List[Path]:
        """ファイルをパターンで検索

        Args:
            pattern: Globパターン（例: "**/*.py"）

        Returns:
            マッチしたファイルパスのリスト
        """
        return list(self.repo_path.glob(pattern))

    def read_code_files(self, file_paths: List[Path], max_chars: int = 50000) -> str:
        """複数のコードファイルを読み込み、連結

        Args:
            file_paths: 読み込むファイルパスのリスト
            max_chars: 最大文字数

        Returns:
            連結されたファイル内容
        """
        content_parts = []
        total_chars = 0

        for file_path in file_paths:
            if file_path.suffix not in self.CODE_EXTENSIONS:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if total_chars + len(content) > max_chars:
                    remaining = max_chars - total_chars
                    content = content[:remaining] + "\n... (truncated)"

                relative_path = file_path.relative_to(self.repo_path)
                content_parts.append(
                    f"## File: {relative_path}\n```{file_path.suffix[1:]}\n{content}\n```\n"
                )
                total_chars += len(content)

                if total_chars >= max_chars:
                    break

            except Exception:
                continue

        return "\n".join(content_parts)

    def get_project_summary(self) -> Dict[str, any]:
        """プロジェクトのサマリー情報を取得

        Returns:
            ファイル数、行数、主要言語を含むサマリー
        """
        file_counts = {}
        total_lines = 0

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]

            for file in files:
                ext = Path(file).suffix
                if ext in self.CODE_EXTENSIONS:
                    file_counts[ext] = file_counts.get(ext, 0) + 1

                    try:
                        file_path = Path(root) / file
                        with open(file_path, "r", encoding="utf-8") as f:
                            total_lines += sum(1 for _ in f)
                    except Exception:
                        pass

        primary_language = (
            max(file_counts.items(), key=lambda x: x[1])[0] if file_counts else None
        )

        return {
            "file_counts": file_counts,
            "total_lines": total_lines,
            "primary_language": primary_language,
        }
