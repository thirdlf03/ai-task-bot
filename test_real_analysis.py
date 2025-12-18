#!/usr/bin/env python
"""実際のリポジトリ分析をシミュレート"""

import asyncio
from pathlib import Path
from src.repository.analyzer import RepositoryAnalyzer
from src.ai.agents.task_breaker import TaskBreakdownAgent
from src.config import settings


async def test_real_repository_analysis():
    """実際のリポジトリを分析してみる"""

    # テストタスク例
    test_tasks = [
        "READMEに環境構築手順を追加する",
        "Discord botのエラーハンドリングを改善する",
        "GitHub APIのレート制限処理を実装する",
    ]

    print("="*80)
    print("実際のリポジトリ分析テスト")
    print("="*80)

    for task_num, task_description in enumerate(test_tasks, 1):
        print(f"\n{'='*80}")
        print(f"テスト {task_num}: {task_description}")
        print(f"{'='*80}")

        # Step 1: キーワード抽出
        print("\n[Step 1] キーワード抽出")
        print("-" * 40)

        try:
            breakdown_agent = TaskBreakdownAgent()
            keywords = await breakdown_agent.extract_keywords(task_description)
            print(f"✓ 抽出されたキーワード: {keywords}")
        except Exception as e:
            print(f"⚠ Gemini APIエラー（スキップ）: {e}")
            # フォールバック: 手動でキーワードを設定
            if "README" in task_description:
                keywords = ["readme", "doc", "setup"]
            elif "Discord" in task_description:
                keywords = ["discord", "bot", "error", "command"]
            elif "GitHub" in task_description:
                keywords = ["github", "api", "rate", "limit"]
            else:
                keywords = ["config", "main"]
            print(f"✓ フォールバックキーワード: {keywords}")

        # Step 2: リポジトリ分析
        print("\n[Step 2] リポジトリ分析")
        print("-" * 40)

        analyzer = RepositoryAnalyzer(Path("."))

        # ファイルツリー
        file_tree = analyzer.get_file_tree(max_depth=2)
        print(f"✓ ファイルツリー取得完了 ({len(file_tree)} 文字)")

        # プロジェクトサマリー
        summary = analyzer.get_project_summary()
        print(f"✓ プロジェクトサマリー:")
        print(f"  - ファイル数: {summary['file_counts']}")
        print(f"  - 総行数: {summary['total_lines']}")
        print(f"  - 主要言語: {summary['primary_language']}")

        # Step 3: ripgrep検索
        print("\n[Step 3] ripgrepでファイル検索")
        print("-" * 40)

        matched_files = analyzer.ripgrep_search(keywords)
        print(f"✓ マッチしたファイル数: {len(matched_files)}")

        for i, file_path in enumerate(matched_files[:10], 1):
            print(f"  {i}. {file_path}")

        if len(matched_files) > 10:
            print(f"  ... 他 {len(matched_files) - 10} ファイル")

        # Step 4: 賢いコード抽出
        print("\n[Step 4] tree-sitterで関数/クラス抽出")
        print("-" * 40)

        code_content = analyzer.read_code_intelligently(
            keywords, max_functions=10, max_chars=10000
        )

        print(f"✓ 抽出されたコンテンツ:")
        print(f"  - 文字数: {len(code_content)}")
        print(f"  - 行数: {code_content.count(chr(10))}")

        # コンテンツのプレビュー
        print("\n[コンテンツプレビュー（最初の30行）]")
        print("-" * 40)
        lines = code_content.split('\n')[:30]
        for line in lines:
            print(line)

        if len(code_content.split('\n')) > 30:
            print("...")
            print(f"（残り {len(code_content.split(chr(10))) - 30} 行）")

        # Step 5: 最終的なコンテキスト
        print("\n[Step 5] Geminiに渡す最終コンテキスト")
        print("-" * 40)

        repo_context = f"""
# Project Structure
{file_tree}

# Project Summary
{summary}

# Related Code
{code_content if code_content else "No relevant code files found."}
"""

        print(f"✓ 最終コンテキスト:")
        print(f"  - 総文字数: {len(repo_context)}")
        print(f"  - 総行数: {repo_context.count(chr(10))}")

        # トークン数の概算（おおよそ4文字=1トークン）
        estimated_tokens = len(repo_context) // 4
        print(f"  - 推定トークン数: ~{estimated_tokens} tokens")

        # コスト概算（Gemini 2.0 Flash: $0.075 / 1M input tokens）
        estimated_cost = (estimated_tokens / 1_000_000) * 0.075
        print(f"  - 推定コスト: ${estimated_cost:.6f} (input only)")

        # 比較: 旧方式での推定
        print("\n[比較] 旧方式（ファイル全体読み込み）との違い")
        print("-" * 40)

        # 旧方式をシミュレート
        old_total_chars = 0
        for file_path in matched_files[:10]:
            if file_path.suffix == ".py":
                try:
                    old_total_chars += len(file_path.read_text())
                except:
                    pass

        old_estimated_tokens = old_total_chars // 4
        old_estimated_cost = (old_estimated_tokens / 1_000_000) * 0.075

        print(f"  旧方式:")
        print(f"    - 文字数: {old_total_chars}")
        print(f"    - 推定トークン: ~{old_estimated_tokens} tokens")
        print(f"    - 推定コスト: ${old_estimated_cost:.6f}")

        print(f"  新方式:")
        print(f"    - 文字数: {len(code_content)}")
        print(f"    - 推定トークン: ~{estimated_tokens} tokens")
        print(f"    - 推定コスト: ${estimated_cost:.6f}")

        if old_total_chars > 0:
            reduction = ((old_total_chars - len(code_content)) / old_total_chars) * 100
            print(f"  💰 削減率: {reduction:.1f}%")
        else:
            print(f"  💰 削減率: N/A")

        print("\n" + "="*80)
        print("次のテストまで2秒待機...")
        print("="*80)
        await asyncio.sleep(2)

    print("\n" + "="*80)
    print("✅ 全テスト完了")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_real_repository_analysis())
