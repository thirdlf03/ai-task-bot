"""
Issue title validation and formatting utilities.
Ensures all issue titles follow Conventional Commits format.
"""

import re
from typing import Tuple, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Conventional Commits types
VALID_TYPES = {
    "feat",      # New feature
    "fix",       # Bug fix
    "docs",      # Documentation changes
    "style",     # Code style changes (formatting, etc.)
    "refactor",  # Code refactoring
    "perf",      # Performance improvements
    "test",      # Adding or updating tests
    "chore",     # Maintenance tasks
    "ci",        # CI/CD changes
    "build",     # Build system changes
}

# GitHub title length limit
MAX_TITLE_LENGTH = 256
RECOMMENDED_LENGTH = 72  # Conventional Commits recommendation

# Regex pattern for Conventional Commits
CONVENTIONAL_PATTERN = re.compile(
    r'^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)'
    r'(\([a-z0-9\-]+\))?'
    r'!?:\s+'
    r'.{1,}'
    r'$'
)


def is_conventional_format(title: str) -> bool:
    """
    Check if title follows Conventional Commits format.

    Args:
        title: Issue title to validate

    Returns:
        True if title matches format, False otherwise
    """
    if not title or len(title) > MAX_TITLE_LENGTH:
        return False

    return bool(CONVENTIONAL_PATTERN.match(title))


def parse_title_components(title: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse title into components: (type, scope, description).

    Args:
        title: Issue title to parse

    Returns:
        Tuple of (type, scope, description) or (None, None, None) if invalid
    """
    match = re.match(
        r'^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)'
        r'(?:\(([a-z0-9\-]+)\))?'
        r'!?:\s*'
        r'(.+)$',
        title
    )

    if match:
        type_, scope, description = match.groups()
        return type_, scope, description.strip()

    return None, None, None


def infer_type_from_description(description: str) -> str:
    """
    Infer commit type from description text.

    Args:
        description: Description text

    Returns:
        Inferred type (defaults to 'feat')
    """
    description_lower = description.lower()

    # Keyword-based inference
    if any(word in description_lower for word in ["fix", "bug", "error", "issue"]):
        return "fix"
    elif any(word in description_lower for word in ["docs", "documentation", "readme"]):
        return "docs"
    elif any(word in description_lower for word in ["test", "testing"]):
        return "test"
    elif any(word in description_lower for word in ["refactor", "cleanup", "reorganize"]):
        return "refactor"
    elif any(word in description_lower for word in ["performance", "optimize", "speed"]):
        return "perf"
    elif any(word in description_lower for word in ["style", "format", "lint"]):
        return "style"
    elif any(word in description_lower for word in ["ci", "pipeline", "deploy"]):
        return "ci"
    elif any(word in description_lower for word in ["build", "compile", "dependency"]):
        return "build"
    elif any(word in description_lower for word in ["chore", "maintenance"]):
        return "chore"
    else:
        # Default to feat for new features
        return "feat"


def extract_scope_from_description(description: str) -> Optional[str]:
    """
    Attempt to extract scope from description.

    Args:
        description: Description text

    Returns:
        Extracted scope or None
    """
    # Look for common patterns like "api: ...", "ui: ...", etc.
    match = re.match(r'^([a-z0-9\-]+):\s*', description)
    if match:
        return match.group(1)

    # Look for keywords that might indicate scope
    description_lower = description.lower()
    if "api" in description_lower:
        return "api"
    elif "ui" in description_lower or "frontend" in description_lower:
        return "ui"
    elif "backend" in description_lower:
        return "backend"
    elif "database" in description_lower or "db" in description_lower:
        return "db"
    elif "auth" in description_lower:
        return "auth"

    return None


def format_title(type_: str, scope: Optional[str], description: str) -> str:
    """
    Format title in Conventional Commits format.

    Args:
        type_: Commit type (feat, fix, etc.)
        scope: Optional scope
        description: Description text

    Returns:
        Formatted title
    """
    # Ensure description starts with lowercase
    description = description[0].lower() + description[1:] if description else ""

    # Build title
    if scope:
        title = f"{type_}({scope}): {description}"
    else:
        title = f"{type_}: {description}"

    # Truncate if too long
    if len(title) > MAX_TITLE_LENGTH:
        available = MAX_TITLE_LENGTH - len(f"{type_}({scope}): " if scope else f"{type_}: ") - 3
        description = description[:available] + "..."
        title = f"{type_}({scope}): {description}" if scope else f"{type_}: {description}"

    return title


def validate_and_format_title(title: str, auto_fix: bool = True) -> Tuple[str, bool]:
    """
    Validate and optionally auto-fix issue title.

    Args:
        title: Original title
        auto_fix: Whether to attempt automatic formatting

    Returns:
        Tuple of (formatted_title, was_modified)
    """
    # Check if already valid
    if is_conventional_format(title):
        logger.info(f"✓ Title already in Conventional Commits format: {title}")
        return title, False

    if not auto_fix:
        logger.warning(f"⚠️ Title not in Conventional Commits format: {title}")
        return title, False

    logger.info(f"🔧 Auto-formatting title: {title}")

    # Try to parse components from malformed title
    type_, scope, description = parse_title_components(title)

    if not type_:
        # Title doesn't follow format at all, try to infer
        description = title
        scope = extract_scope_from_description(description)
        type_ = infer_type_from_description(description)

        # Remove scope prefix from description if it was there
        if scope:
            description = re.sub(r'^' + scope + r':\s*', '', description, flags=re.IGNORECASE)

    formatted = format_title(type_, scope, description)
    logger.info(f"✓ Formatted to: {formatted}")

    return formatted, True


def validate_title_length(title: str) -> bool:
    """
    Check if title is within acceptable length.

    Args:
        title: Title to check

    Returns:
        True if length is acceptable
    """
    if len(title) > MAX_TITLE_LENGTH:
        logger.error(f"❌ Title exceeds {MAX_TITLE_LENGTH} characters: {len(title)}")
        return False

    if len(title) > RECOMMENDED_LENGTH:
        logger.warning(f"⚠️ Title exceeds recommended {RECOMMENDED_LENGTH} characters: {len(title)}")

    return True
