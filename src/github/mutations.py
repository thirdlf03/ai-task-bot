# Issue作成
CREATE_ISSUE = """
mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String!) {
  createIssue(input: {
    repositoryId: $repositoryId
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
"""

# Projectに追加
ADD_TO_PROJECT = """
mutation AddToProject($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {
    projectId: $projectId
    contentId: $contentId
  }) {
    item {
      id
    }
  }
}
"""

# Assignee追加
ADD_ASSIGNEES = """
mutation AddAssignees($issueId: ID!, $assigneeIds: [ID!]!) {
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
"""

# Custom fieldを更新（Status等）
UPDATE_PROJECT_FIELD = """
mutation UpdateField($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
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
"""
