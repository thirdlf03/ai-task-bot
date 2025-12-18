from pathlib import Path
from typing import List, Dict, Any
from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CodeParser:
    """tree-sitterを使ったコードパーサー"""

    def __init__(self):
        """Pythonパーサーを初期化"""
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)

    def extract_functions_and_classes(
        self, file_path: Path
    ) -> List[Dict[str, Any]]:
        """ファイルから関数とクラス定義を抽出

        Args:
            file_path: 解析するファイルのパス

        Returns:
            関数とクラス情報のリスト
        """
        try:
            with open(file_path, "rb") as f:
                code = f.read()

            tree = self.parser.parse(code)
            root_node = tree.root_node

            definitions = []

            # 関数とクラスを再帰的に探索
            self._extract_definitions(root_node, code, definitions)

            return definitions

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []

    def _extract_definitions(
        self, node: Node, code: bytes, definitions: List[Dict[str, Any]]
    ) -> None:
        """ASTから定義を再帰的に抽出

        Args:
            node: 現在のASTノード
            code: ソースコード（バイト列）
            definitions: 定義を格納するリスト
        """
        if node.type == "function_definition":
            definitions.append(self._extract_function(node, code))
        elif node.type == "class_definition":
            definitions.append(self._extract_class(node, code))

        # 子ノードを再帰的に探索
        for child in node.children:
            self._extract_definitions(child, code, definitions)

    def _extract_function(self, node: Node, code: bytes) -> Dict[str, Any]:
        """関数定義を抽出

        Args:
            node: 関数定義のASTノード
            code: ソースコード（バイト列）

        Returns:
            関数情報の辞書
        """
        name = ""
        docstring = ""

        # 関数名を取得
        for child in node.children:
            if child.type == "identifier":
                name = code[child.start_byte : child.end_byte].decode("utf-8")
            elif child.type == "block":
                # docstringを探す
                docstring = self._extract_docstring(child, code)

        # 関数全体のコード
        full_code = code[node.start_byte : node.end_byte].decode("utf-8")

        return {
            "type": "function",
            "name": name,
            "docstring": docstring,
            "code": full_code,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }

    def _extract_class(self, node: Node, code: bytes) -> Dict[str, Any]:
        """クラス定義を抽出

        Args:
            node: クラス定義のASTノード
            code: ソースコード（バイト列）

        Returns:
            クラス情報の辞書
        """
        name = ""
        docstring = ""

        # クラス名を取得
        for child in node.children:
            if child.type == "identifier":
                name = code[child.start_byte : child.end_byte].decode("utf-8")
            elif child.type == "block":
                # docstringを探す
                docstring = self._extract_docstring(child, code)

        # クラス全体のコード
        full_code = code[node.start_byte : node.end_byte].decode("utf-8")

        return {
            "type": "class",
            "name": name,
            "docstring": docstring,
            "code": full_code,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }

    def _extract_docstring(self, block_node: Node, code: bytes) -> str:
        """ブロックからdocstringを抽出

        Args:
            block_node: ブロックのASTノード
            code: ソースコード（バイト列）

        Returns:
            docstring（なければ空文字列）
        """
        # ブロックの最初の式がstring literalならdocstring
        for child in block_node.children:
            if child.type == "expression_statement":
                for expr_child in child.children:
                    if expr_child.type == "string":
                        docstring = code[expr_child.start_byte : expr_child.end_byte].decode(
                            "utf-8"
                        )
                        # 引用符を除去
                        return docstring.strip('"""').strip("'''").strip('"').strip("'")
        return ""

    def extract_relevant_code(
        self, file_path: Path, keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """キーワードに関連するコード部分を抽出

        Args:
            file_path: 解析するファイルのパス
            keywords: 検索キーワードのリスト

        Returns:
            関連する関数/クラスのリスト
        """
        definitions = self.extract_functions_and_classes(file_path)

        if not keywords:
            return definitions

        # キーワードに関連する定義をフィルタリング
        relevant = []
        for definition in definitions:
            # 名前、docstring、コードのいずれかにキーワードが含まれるか
            text = (
                f"{definition['name']} {definition['docstring']} {definition['code']}"
            ).lower()

            for keyword in keywords:
                if keyword.lower() in text:
                    relevant.append(definition)
                    break

        return relevant if relevant else definitions[:5]  # 関連がなければ最初の5つ
