"""
Duplicate issue detection utilities.
Uses similarity matching to identify potential duplicate issues.
"""

from typing import List, Dict, Any, Tuple, Optional
from difflib import SequenceMatcher
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default similarity threshold (0.0 - 1.0)
DEFAULT_SIMILARITY_THRESHOLD = 0.8


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity ratio between two strings.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity ratio (0.0 - 1.0)
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def normalize_title(title: str) -> str:
    """
    Normalize title for comparison.

    Args:
        title: Original title

    Returns:
        Normalized title
    """
    # Remove conventional commit prefix for comparison
    import re
    normalized = re.sub(
        r'^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)'
        r'(\([a-z0-9\-]+\))?'
        r'!?:\s*',
        '',
        title,
        flags=re.IGNORECASE
    )

    # Convert to lowercase and strip whitespace
    normalized = normalized.lower().strip()

    return normalized


def find_similar_issues(
    new_title: str,
    existing_issues: List[Dict[str, Any]],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    max_results: int = 5
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Find issues similar to the new title.

    Args:
        new_title: Title of new issue to check
        existing_issues: List of existing issues with 'title' field
        threshold: Minimum similarity threshold (0.0 - 1.0)
        max_results: Maximum number of similar issues to return

    Returns:
        List of (issue, similarity) tuples, sorted by similarity descending
    """
    normalized_new = normalize_title(new_title)
    similar = []

    for issue in existing_issues:
        existing_title = issue.get("title", "")
        normalized_existing = normalize_title(existing_title)

        similarity = calculate_similarity(normalized_new, normalized_existing)

        if similarity >= threshold:
            similar.append((issue, similarity))

    # Sort by similarity descending
    similar.sort(key=lambda x: x[1], reverse=True)

    return similar[:max_results]


def check_for_duplicates(
    new_title: str,
    existing_issues: List[Dict[str, Any]],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD
) -> Tuple[bool, List[Tuple[Dict[str, Any], float]]]:
    """
    Check if new title is a duplicate of existing issues.

    Args:
        new_title: Title of new issue
        existing_issues: List of existing issues
        threshold: Similarity threshold

    Returns:
        Tuple of (is_duplicate, similar_issues)
    """
    similar_issues = find_similar_issues(new_title, existing_issues, threshold)

    is_duplicate = len(similar_issues) > 0

    if is_duplicate:
        logger.warning(f"⚠️ Potential duplicate detected for: {new_title}")
        for issue, similarity in similar_issues:
            logger.warning(f"   Similar ({similarity:.1%}): {issue.get('title')} - {issue.get('url')}")

    return is_duplicate, similar_issues


def filter_existing_issues(
    issues: List[Dict[str, Any]],
    include_closed: bool = False,
    exclude_states: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Filter issues for duplicate checking.

    Args:
        issues: List of all issues
        include_closed: Whether to include closed issues
        exclude_states: List of states to exclude

    Returns:
        Filtered list of issues
    """
    if exclude_states is None:
        exclude_states = []

    filtered = []

    for issue in issues:
        state = issue.get("state", "OPEN")

        # Skip closed issues if not included
        if not include_closed and state == "CLOSED":
            continue

        # Skip explicitly excluded states
        if state in exclude_states:
            continue

        filtered.append(issue)

    return filtered


def format_duplicate_warning(
    new_title: str,
    similar_issues: List[Tuple[Dict[str, Any], float]]
) -> str:
    """
    Format a user-friendly duplicate warning message.

    Args:
        new_title: Title of new issue
        similar_issues: List of similar issues

    Returns:
        Formatted warning message
    """
    lines = [
        f"⚠️ **Potential Duplicate Detected**",
        f"",
        f"New issue: **{new_title}**",
        f"",
        f"Similar existing issues:",
    ]

    for issue, similarity in similar_issues:
        title = issue.get("title")
        url = issue.get("url")
        state = issue.get("state", "UNKNOWN")
        lines.append(f"- [{similarity:.0%} similar] [{state}] {title}")
        lines.append(f"  {url}")

    lines.extend([
        f"",
        f"Action: Skipping creation to avoid duplicate. Review existing issues.",
    ])

    return "\n".join(lines)
