# AI Task Bot 調査報告

調査日: 2025-12-18

## 目的

GitHub ProjectsとAI Agentを統合したタスク管理Botの実装可能性と類似実装の調査

## 要件定義

### 必要なコマンド

1. `/create-task <task内容>`
   - AI Agentがリポジトリを分析
   - タスクが実装済みかを確認
   - 未実装の場合、1PR粒度に分割してGitHub Projectsに登録

2. `/get-all-task`
   - GitHub Projectsの登録タスクを取得
   - デフォルトで完了タスクは非表示
   - 本人のみに表示

3. `/get-task <github_id>`
   - 指定したGitHub IDのユーザーのタスクを取得

## 調査結果サマリー

✅ **全機能が実装可能**

現在のプロジェクトは`discord.py`ベースのため、Discordコマンドとしての実装が最適。

## 類似実装の調査

### 1. GitHub Projects自動化Bot

#### philschatz/project-bot
- **URL**: https://github.com/philschatz/project-bot
- **機能**: IssueやPRを自動的にProject boardに追加・移動
- **特徴**: Markdown形式の設定カードで自動化ルールを定義

#### actions/add-to-project
- **URL**: https://github.com/actions/add-to-project
- **機能**: GitHub ActionsでIssue/PRをProjectsに自動追加
- **特徴**: Projects v2対応、イベントトリガー型

#### imjohnbo/issue-bot
- **URL**: https://github.com/imjohnbo/issue-bot
- **機能**: タイトル、本文、ラベル、assigneeを指定してIssueを自動作成
- **特徴**: スケジュール実行やトリガー条件設定が可能

### 2. AI Agent × リポジトリ分析

#### VoltAgent GitHub Analyzer
- **URL**: https://voltagent.dev/blog/building-first-agent-github-analyzer/
- **機能**: リポジトリのスター数や貢献者を分析するAI Agent
- **特徴**: マルチエージェントアーキテクチャのチュートリアル
- **参考度**: ★★★★★ (実装パターンとして最も参考になる)

#### Blech GitHub Bot
- **URL**: https://medium.com/@abuzar_mahmood/leveraging-ai-agents-for-automated-github-issue-response-the-blech-github-bot-0bc709d16ba4
- **機能**: マルチエージェントでIssueに自動応答
- **アーキテクチャ**:
  - File-analysis agent: リポジトリ構造・コードパターン分析
  - Code editing agent: コード変更提案・実装例生成
  - Summarizing agent: 技術的知見を明確な応答に要約
- **参考度**: ★★★★★ (タスク分割の参考になる)

#### Moderne Moddy (Multi-repo AI Agent)
- **URL**: https://www.moderne.ai/blog/introducing-moderne-multi-repo-ai-agent-for-transforming-code-at-scale
- **機能**: 複数リポジトリを横断してコードベースを理解・進化
- **特徴**: スケールでの正確な動作に特化

### 3. Slack/Discord統合事例

#### GitHub公式Slack統合
- **URL**: https://github.com/integrations/slack
- **機能**: SlackチャンネルでGitHub通知・コマンド実行
- **コマンド例**: `/github subscribe`, `/github unsubscribe`

#### Axolo
- **URL**: https://axolo.co/blog/p/top-5-github-pull-request-slack-integration
- **機能**: PR作成時に専用Slackチャンネルを自動生成
- **特徴**: レビュアーとassigneeのみを招待

#### InnGames slack-bot
- **URL**: https://github.com/innogames/slack-bot
- **機能**: Jenkins、Jira、PRの監視
- **特徴**: 開発者向けの包括的な自動化

### 4. フレームワーク・ライブラリ

#### Probot
- **URL**: https://github.com/probot/probot
- **言語**: Node.js (TypeScript)
- **機能**: GitHub Appを構築するためのフレームワーク
- **特徴**: Webhookイベントベースの自動化

#### github-projectv2 (Python)
- **URL**: https://pypi.org/project/github-projectv2/
- **言語**: Python
- **機能**: GitHub Projects v2の高レベルインターフェース
- **参考度**: ★★★☆☆ (APIラッパーとして便利)

## 技術実装詳細

### GitHub Projects API v2の使い方

#### 重要な制約

⚠️ **Assignee、Label、Milestone、Repositoryは`updateProjectV2ItemFieldValue`では変更不可**

これらはissue/PRのプロパティであり、Project itemのプロパティではない。
代わりに以下のmutationを使用:
- `addAssigneesToAssignable`: Assignee追加
- `addLabelsToLabelable`: Label追加

参考: https://github.com/orgs/community/discussions/75201

#### 基本的な実装フロー

```python
import requests

GITHUB_API = 'https://api.github.com/graphql'
headers = {
    'Authorization': f'Bearer {GITHUB_TOKEN}',
    'Content-Type': 'application/json'
}

# 1. Issueを作成
create_issue_mutation = '''
mutation($repoId: ID!, $title: String!, $body: String!) {
  createIssue(input: {
    repositoryId: $repoId
    title: $title
    body: $body
  }) {
    issue {
      id
      number
      url
    }
  }
}
'''

# 2. ProjectにIssueを追加
add_to_project_mutation = '''
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {
    projectId: $projectId
    contentId: $contentId
  }) {
    item {
      id
    }
  }
}
'''

# 3. Assigneeを設定（別mutation）
assign_mutation = '''
mutation($issueId: ID!, $assigneeIds: [ID!]!) {
  addAssigneesToAssignable(input: {
    assignableId: $issueId
    assigneeIds: $assigneeIds
  }) {
    assignable {
      ... on Issue {
        id
        assignees(first: 10) {
          nodes {
            login
          }
        }
      }
    }
  }
}
'''

# 4. Custom fieldを更新（Status等）
update_field_mutation = '''
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: $value
  }) {
    projectV2Item {
      id
    }
  }
}
'''
```

参考:
- https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects
- https://devopsjournal.io/blog/2022/11/28/github-graphql-queries

### 各コマンドの実装設計

#### `/create-task <task内容>`

**フロー**:
1. AI Agentがリポジトリをクローン/分析
2. タスク内容に関連するコード検索（Grep/Read）
3. 実装状況を判定
4. 未実装の場合:
   - タスクを1PR粒度に分解（AI Agent）
   - 各サブタスクをIssue化
   - GitHub Projectsに追加
5. Discord/Slackに結果を返信

**必要なAPI**:
- GitHub GraphQL (createIssue, addProjectV2ItemById)
- AI Agent API (Claude/OpenAI/Gemini)
- Git操作 (リポジトリクローン・分析)

**参考実装**: Blech GitHub Botのマルチエージェント構造

#### `/get-all-task`

**フロー**:
1. GitHub Projects GraphQL APIでProject取得
2. Status != "Done"でフィルタリング
3. Discordのephemeralメッセージで本人のみに返信

**GraphQL Query例**:
```graphql
query($projectNumber: Int!, $owner: String!) {
  organization(login: $owner) {
    projectV2(number: $projectNumber) {
      items(first: 100) {
        nodes {
          id
          content {
            ... on Issue {
              title
              url
              number
              assignees(first: 10) {
                nodes {
                  login
                }
              }
            }
          }
          fieldValues(first: 10) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field {
                  ... on ProjectV2SingleSelectField {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### `/get-task <github_id>`

**フロー**:
1. 指定したユーザーのopen issuesを取得
2. Project所属でフィルタリング
3. 結果をDiscordに返信

**GraphQL Query例**:
```graphql
query($login: String!) {
  user(login: $login) {
    issues(first: 100, filterBy: {states: OPEN}) {
      nodes {
        title
        url
        number
        repository {
          nameWithOwner
        }
        projectItems(first: 10) {
          nodes {
            project {
              title
              number
            }
          }
        }
      }
    }
  }
}
```

## 推奨技術スタック

### 現在インストール済み
- `discord.py` (v2.6.4+): Discordコマンド処理
- `python-dotenv` (v1.2.1+): 環境変数管理
- `ruff`: Linter/Formatter

### 追加が必要
- `requests`: GitHub GraphQL API通信
- `anthropic` / `openai` / `google-generativeai`: AI Agent統合（いずれか）
- `PyGithub` (オプション): REST API操作の簡略化

### インストールコマンド
```bash
# Claude API
uv add requests anthropic

# OpenAI API
uv add requests openai

# Gemini API (推奨)
uv add requests google-generativeai
```

## 実装優先度

### Phase 1: 基本機能（MVP）
1. GitHub GraphQL API接続テスト
2. `/get-all-task`実装（最もシンプル）
3. `/get-task <github_id>`実装

### Phase 2: AI統合
4. AI Agent統合（コード分析）
5. タスク分解ロジック実装

### Phase 3: 高度な機能
6. `/create-task`実装（最も複雑）
7. エラーハンドリング・リトライロジック
8. ログ・モニタリング

## リスクと注意点

### API Rate Limit
- GitHub GraphQL API: 5,000 points/hour
- 複雑なqueryは多くのpointを消費
- 対策: キャッシング、バッチ処理

### AI Agent実装の複雑性
- リポジトリ分析の精度向上が課題
- タスク分解の粒度調整が必要
- 誤判定時のフォールバック設計

### セキュリティ
- GitHub Token管理（`.env`、環境変数）
- Discord Bot Tokenの適切な保管
- 権限スコープの最小化（principle of least privilege）

## 参考リンク

### 公式ドキュメント
- [GitHub Projects API Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
- [GitHub GraphQL API](https://docs.github.com/en/graphql)
- [discord.py Documentation](https://discordpy.readthedocs.io/)

### チュートリアル・ブログ
- [GitHub GraphQL Queries Examples](https://devopsjournal.io/blog/2022/11/28/github-graphql-queries)
- [GraphQL Intro with GitHub Projects](https://some-natalie.dev/blog/graphql-intro/)
- [Python GraphQL Tutorial](https://gist.github.com/gbaman/b3137e18c739e0cf98539bf4ec4366ad)

### オープンソースプロジェクト
- [Probot Framework](https://github.com/probot/probot)
- [philschatz/project-bot](https://github.com/philschatz/project-bot)
- [actions/add-to-project](https://github.com/actions/add-to-project)
- [imjohnbo/issue-bot](https://github.com/imjohnbo/issue-bot)

### AI Agent参考実装
- [VoltAgent GitHub Analyzer](https://voltagent.dev/blog/building-first-agent-github-analyzer/)
- [Blech GitHub Bot](https://medium.com/@abuzar_mahmood/leveraging-ai-agents-for-automated-github-issue-response-the-blech-github-bot-0bc709d16ba4)
- [500 AI Agents Projects](https://github.com/ashishpatel26/500-AI-Agents-Projects)
- [NirDiamant/GenAI_Agents](https://github.com/NirDiamant/GenAI_Agents)

## AI APIの選択: Gemini API追加調査

### Gemini APIの可能性 (追加調査: 2025-12-18)

✅ **Gemini APIでのAgent実装は完全に可能**

Gemini APIは、特に**コスト効率**と**コンテキストウィンドウの大きさ**で優位性があり、本プロジェクトに非常に適している。

### Gemini API の主要機能

#### 1. Function Calling & Tool Use
- **公式ドキュメント**: https://ai.google.dev/gemini-api/docs/function-calling
- **特徴**:
  - 外部ツール・APIとの接続が可能
  - Built-in tools（Google Search、Code Execution）が利用可能
  - Custom toolsを定義してカスタム関数を呼び出せる
  - **Model Context Protocol (MCP)のサポート**: MCPは外部ツール・データとAIアプリを接続する標準規格

#### 2. マルチエージェントシステム
- **参考実装**: https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/agents/research-multi-agents/intro_research_multi_agents_gemini_2_0.ipynb
- **アーキテクチャ**:
  - ExecutionAgentが複数の専門エージェントを統括
  - 各エージェントが特定のタスク（分析、コード生成、要約など）を担当
  - Pythonでの実装例が豊富

#### 3. コード分析能力
- **Gemini 2.0 Flash のベンチマーク**:
  - **SWE-bench Verified**: 51.8%達成（実世界のソフトウェアエンジニアリングタスク）
  - Code execution toolsを使用して数百の解決策をサンプリング可能
  - ユニットテストとモデル自身の判断で最適解を選択
- **特徴**:
  - コードベース全体を分析し、必要なファイル・フォルダーを要求
  - フルプロジェクトコンテキストで正確なコード補完・提案・リファクタリング
  - **1M tokenのコンテキストウィンドウ**（約75万単語）

#### 4. フレームワーク統合
- **LangGraph**: ステートフルなマルチアクターAI Agentをグラフ構造で構築
- **LangChain**: Gemini modelsを直接活用可能
- **Pydantic AI**: 型安全なAgentをPythonで構築（Gemini対応）
- **CrewAI**: タスク分担型のマルチエージェントシステム

### Gemini vs Claude vs OpenAI 比較

| 項目 | Gemini 2.5 Flash | Claude 4 Sonnet | OpenAI GPT-4 |
|------|------------------|-----------------|--------------|
| **コスト** | ⭐⭐⭐⭐⭐ | ⭐ (20x Gemini) | ⭐⭐ |
| **速度** | ⭐⭐⭐⭐⭐ 高速 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **コンテキスト** | 1M tokens | 200K tokens | 128K tokens |
| **コード品質** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **複雑な推論** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **トークン効率** | 432K input | 260.8K input | - |
| **プロジェクト完了時間** | 2h 2min | 1h 17min | - |

**参考**: https://composio.dev/blog/gemini-cli-vs-claude-code-the-better-coding-agent

### 本プロジェクトでの推奨: Gemini 2.0 Flash

#### 推奨理由
1. **コスト効率**: Claude 4の1/20のコストで実行可能
2. **大規模コンテキスト**: 1M tokensで小規模プロジェクト全体を一度に処理可能
3. **Function Calling**: GitHub APIとの統合が容易
4. **マルチエージェント対応**: 公式のマルチエージェント実装例が豊富
5. **日本語対応**: 自然な日本語処理が可能

#### 実装例: Gemini Function Calling

```python
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)

# Function定義
tools = [
    {
        "function_declarations": [
            {
                "name": "search_code",
                "description": "Search for code in a repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "File pattern to search"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_github_issue",
                "description": "Create a new GitHub issue",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"}
                    },
                    "required": ["title", "body"]
                }
            }
        ]
    }
]

# モデル初期化
model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    tools=tools
)

# Agent実行
chat = model.start_chat(enable_automatic_function_calling=True)
response = chat.send_message(
    "このリポジトリに認証機能が実装されているか確認し、なければタスクを作成して"
)
```

**参考**: https://www.philschmid.de/gemini-function-calling

#### 推奨フレームワーク: LangGraph + Gemini

```python
from langgraph.graph import StateGraph, END
from google.generativeai import GenerativeModel

# 各ノード（Agent）の定義
def analyze_repo(state):
    """リポジトリ分析Agent"""
    # コード分析ロジック
    pass

def breakdown_task(state):
    """タスク分解Agent"""
    # Geminiでタスク分解
    pass

def create_issues(state):
    """Issue作成Agent"""
    # GitHub API呼び出し
    pass

# グラフ構築
workflow = StateGraph()
workflow.add_node("analyze", analyze_repo)
workflow.add_node("breakdown", breakdown_task)
workflow.add_node("create", create_issues)

workflow.add_edge("analyze", "breakdown")
workflow.add_edge("breakdown", "create")
workflow.add_edge("create", END)

app = workflow.compile()
```

### Gemini API 実装リソース

#### 公式ドキュメント
- [Using Tools & Agents with Gemini API](https://ai.google.dev/gemini-api/docs/tools)
- [Function Calling Guide](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gemini Models Overview](https://ai.google.dev/gemini-api/docs/models)

#### チュートリアル
- [Building Agents with Gemini 3 and Open Source Frameworks](https://developers.googleblog.com/building-ai-agents-with-google-gemini-3-and-open-source-frameworks/)
- [Function Calling Codelabs](https://codelabs.developers.google.com/codelabs/gemini-function-calling)
- [Practical Guide: Building an Agent from Scratch](https://www.philschmid.de/building-agents)

#### サンプルコード
- [Google Gemini Cookbook](https://github.com/google-gemini/cookbook)
- [GoogleCloudPlatform Multi-Agent Research](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/agents/research-multi-agents/intro_research_multi_agents_gemini_2_0.ipynb)
- [Zero to MCP Hero: Building Multi-Tool AI Agents](https://timtech4u.medium.com/zero-to-mcp-hero-building-multi-tool-ai-agents-in-python-gemini-c181fbb047b7)

#### フレームワーク統合
- [Pydantic AI + Gemini Tutorial](https://medium.com/google-cloud/how-i-built-an-agent-with-pydantic-ai-and-google-gemini-4887e5dd041d)
- [LangGraph + Gemini 3 API Tutorial](https://www.datacamp.com/tutorial/gemini-3-api-tutorial)
- [ADK Framework for Agent Building](https://developers.googleblog.com/en/simplify-agent-building-adk-gemini-cli/)

### 使い分けの指針

#### Gemini 2.0 Flashを選ぶべきケース（本プロジェクト該当）
- ✅ コスト重視のプロダクト
- ✅ 大規模なコードベース分析が必要
- ✅ 速度とスループットが重要
- ✅ 小〜中規模のリポジトリ（1M token以内）

#### Claude 4 Sonnetを選ぶべきケース
- 複雑な推論・プランニングが必要
- 本番環境レベルのコード品質が必須
- コストよりも品質優先
- 詳細な分析とフォールバック戦略が必要

#### 複合戦略（推奨）
1. **Phase 1-2**: Gemini 2.0 Flash（MVP開発、コスト削減）
2. **Phase 3**: 必要に応じてClaude 4を部分的に導入（複雑なタスク分解のみ）

### Geminiの新機能（2025年対応）

#### Gemini 3 Flash以降の機能
- **Multimodal Function Response**: 画像やPDFを含むfunction responseが可能
- **Streaming Function Call Arguments**: 関数呼び出し引数のストリーミング生成
- **Built-in Code Execution**: サーバー側でPythonコード実行
- **Live API**: リアルタイムツール使用

#### Agent Mode（Gemini Code Assist）
- IDEに統合されたAgent機能
- コードベース全体の分析
- 目標ベースのファイル・フォルダー要求
- 完全なプロジェクトコンテキストでの提案

## 結論

GitHub ProjectsとAI Agentを統合したタスク管理Botは**完全に実装可能**。

類似の実装例が多数存在し、特にBlech GitHub BotやVoltAgentのマルチエージェントアーキテクチャは本プロジェクトの参考になる。

**AI APIの選択**では、**Gemini 2.0 Flash**が本プロジェクトに最適：
- コスト効率が高い（Claude 4の1/20）
- 1M tokenの大規模コンテキスト
- マルチエージェント実装例が豊富
- Function Callingで外部API統合が容易

Phase 1から段階的に実装することで、リスクを最小化しながら機能を拡充できる。
