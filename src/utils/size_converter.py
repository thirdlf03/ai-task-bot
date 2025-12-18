from typing import Dict, Any


def convert_effort_to_size(estimated_effort: str) -> str:
    """Geminiのestimated_effort (S/M/L) をGitHub ProjectsのSize (XS/S/M/L/XL)に変換

    Args:
        estimated_effort: S, M, L のいずれか

    Returns:
        XS, S, M, L, XL のいずれか
    """
    mapping = {
        "S": "S",  # Small → S
        "M": "M",  # Medium → M
        "L": "L",  # Large → L
    }
    return mapping.get(estimated_effort, "M")  # デフォルトはM


def get_size_option_id(field_options: list[Dict[str, Any]], size_value: str) -> str | None:
    """Sizeフィールドのオプションリストから指定サイズのIDを取得

    Args:
        field_options: フィールドのoptionsリスト
        size_value: サイズ値（XS/S/M/L/XL）

    Returns:
        オプションID、見つからない場合はNone
    """
    for option in field_options:
        if option.get("name") == size_value:
            return option.get("id")
    return None
