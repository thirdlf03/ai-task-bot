# Project v2のアイテム取得（完了タスク除外可能）
GET_PROJECT_ITEMS = """
query GetProjectItems($org: String!, $projectNumber: Int!) {
  organization(login: $org) {
    projectV2(number: $projectNumber) {
      id
      title
      items(first: 100) {
        nodes {
          id
          content {
            ... on Issue {
              id
              title
              url
              number
              state
              assignees(first: 10) {
                nodes {
                  login
                  id
                }
              }
              repository {
                nameWithOwner
              }
            }
          }
          fieldValues(first: 20) {
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
"""

# ユーザーのタスク取得
GET_USER_TASKS = """
query GetUserTasks($login: String!, $org: String!, $projectNumber: Int!) {
  user(login: $login) {
    issues(first: 100, filterBy: {states: OPEN}) {
      nodes {
        id
        title
        url
        number
        state
        repository {
          nameWithOwner
        }
        projectItems(first: 10) {
          nodes {
            project {
              ... on ProjectV2 {
                title
                number
              }
            }
          }
        }
      }
    }
  }
  organization(login: $org) {
    projectV2(number: $projectNumber) {
      id
      title
    }
  }
}
"""

# リポジトリIDとProject ID取得
GET_REPOSITORY_AND_PROJECT_IDS = """
query GetIDs($org: String!, $repo: String!, $projectNumber: Int!) {
  repository(owner: $org, name: $repo) {
    id
  }
  organization(login: $org) {
    projectV2(number: $projectNumber) {
      id
    }
  }
}
"""

# レート制限チェック
CHECK_RATE_LIMIT = """
query {
  rateLimit {
    limit
    remaining
    resetAt
  }
}
"""

# トークン検証
VALIDATE_TOKEN = """
query {
  viewer {
    login
  }
}
"""
