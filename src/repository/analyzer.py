from pathlib import Path
from typing import List, Dict
import os
import subprocess
import json
from src.utils.logger import get_logger

logger = get_logger(__name__)


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
        self._code_parser = None

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

    @property
    def code_parser(self):
        """CodeParserのlazy loading"""
        if self._code_parser is None:
            from src.repository.code_parser import CodeParser

            self._code_parser = CodeParser()
        return self._code_parser

    def ripgrep_search(self, keywords: List[str]) -> List[Path]:
        """ripgrepを使ってキーワードに関連するファイルを検索

        Args:
            keywords: 検索キーワードのリスト

        Returns:
            マッチしたファイルパスのリスト
        """
        if not keywords:
            return []

        logger.info(f"🔍 [File Search] Starting ripgrep keyword search: {keywords}")

        matched_files = set()

        for keyword in keywords:
            logger.info(f"   🔎 Searching: '{keyword}'...")
            try:
                # ripgrepをJSON出力モードで実行
                result = subprocess.run(
                    [
                        "rg",
                        "--json",
                        "--iglob",
                        "*.py",  # Pythonファイルのみ
                        "--iglob",
                        "!.venv",  # .venvを除外
                        "--iglob",
                        "!__pycache__",
                        keyword,
                        str(self.repo_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                # JSON出力を解析
                for line in result.stdout.splitlines():
                    try:
                        data = json.loads(line)
                        if data.get("type") == "match":
                            file_path = Path(data["data"]["path"]["text"])
                            matched_files.add(file_path)
                    except json.JSONDecodeError:
                        continue

            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                # ripgrep not found or timeout
                logger.warning(f"   ⚠️ ripgrep error, falling back to glob: {e}")
                # Fallback: glob search
                matched_files.update(self.search_files(f"**/*{keyword}*"))

        logger.info(f"✅ [Search Complete] Found {len(matched_files)} files")
        for i, file_path in enumerate(list(matched_files)[:10], 1):
            logger.info(f"   {i}. {file_path}")
        if len(matched_files) > 10:
            logger.info(f"   ... and {len(matched_files) - 10} more files")

        return list(matched_files)

    def read_code_intelligently(
        self, keywords: List[str], max_functions: int = 20, max_chars: int = 50000
    ) -> str:
        """キーワードに基づいて関連するコードを賢く抽出

        Args:
            keywords: 検索キーワードのリスト
            max_functions: 最大関数/クラス数
            max_chars: 最大文字数

        Returns:
            Markdown形式の関連コード
        """
        logger.info(f"🧠 [Smart Code Extraction] Starting (max {max_functions} functions, {max_chars} chars)")

        # Search files with ripgrep
        relevant_files = self.ripgrep_search(keywords)

        if not relevant_files:
            # Fallback: keyword-based glob search
            relevant_files = []
            for keyword in keywords:
                relevant_files.extend(self.search_files(f"**/*{keyword}*"))
            relevant_files = list(set(relevant_files))[:10]

        content_parts = []
        total_chars = 0
        function_count = 0

        logger.info(f"🌲 [tree-sitter Parse] Parsing {len(relevant_files)} files...")

        for file_path in relevant_files:
            if file_path.suffix != ".py":
                continue

            logger.info(f"   📄 Parsing: {file_path}")

            # Extract functions/classes with tree-sitter
            definitions = self.code_parser.extract_relevant_code(file_path, keywords)

            if definitions:
                logger.info(f"      ✓ Extracted {len(definitions)} functions/classes")

            if not definitions:
                continue

            relative_path = file_path.relative_to(self.repo_path)

            for definition in definitions:
                if function_count >= max_functions:
                    break

                code = definition["code"]
                if total_chars + len(code) > max_chars:
                    break

                # Markdown形式でフォーマット
                def_type = definition["type"]
                def_name = definition["name"]
                docstring = definition["docstring"]

                header = f"## File: {relative_path} - {def_type.capitalize()}: {def_name}"
                if docstring:
                    header += f"\n**Description**: {docstring[:200]}..."

                content_parts.append(f"{header}\n```python\n{code}\n```\n")

                total_chars += len(code)
                function_count += 1

            if function_count >= max_functions or total_chars >= max_chars:
                break

        if not content_parts:
            logger.warning("⚠️ [Extraction Complete] No relevant code found")
            return "No relevant code found."

        logger.info(f"✅ [Extraction Complete] Extracted {function_count} functions/classes")
        logger.info(f"   📊 Total characters: {total_chars} characters")
        logger.info(f"   💰 Estimated tokens: ~{total_chars // 4} tokens")

        return "\n".join(content_parts)
