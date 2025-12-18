from pydantic import BaseModel
from typing import List, Optional


class User(BaseModel):
    """GitHubユーザー"""

    login: str
    id: str


class Repository(BaseModel):
    """GitHubリポジトリ"""

    nameWithOwner: str


class Issue(BaseModel):
    """GitHub Issue"""

    id: str
    title: str
    url: str
    number: int
    state: str
    assignees: List[User] = []
    repository: Optional[Repository] = None


class ProjectItem(BaseModel):
    """GitHub Projectアイテム"""

    id: str
    content: Issue
    status: Optional[str] = None  # "Todo", "In Progress", "Done"


class Project(BaseModel):
    """GitHub Project"""

    id: str
    title: str
    items: List[ProjectItem] = []
