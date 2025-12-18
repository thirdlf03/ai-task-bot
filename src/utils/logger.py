import logging
from pathlib import Path
from src.config import settings


def get_logger(name: str) -> logging.Logger:
    """ロガーインスタンスを取得

    Args:
        name: ロガー名（通常は__name__を渡す）

    Returns:
        logging.Logger: 設定済みロガーインスタンス
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    if not logger.handlers:
        # ファイルハンドラ
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)

        # コンソールハンドラ
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # フォーマッタ
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


class StructuredLogger:
    """構造化ログ出力用のヘルパークラス"""

    @staticmethod
    def log_command_execution(
        command_name: str,
        user: str,
        success: bool,
        duration_ms: float,
        metadata: dict = None,
    ):
        """コマンド実行ログを記録

        Args:
            command_name: コマンド名
            user: 実行ユーザー
            success: 成功フラグ
            duration_ms: 実行時間（ミリ秒）
            metadata: 追加メタデータ
        """
        import json
        from datetime import datetime

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "command_execution",
            "command": command_name,
            "user": user,
            "success": success,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
        }

        logger = get_logger(__name__)
        logger.info(json.dumps(log_entry))
