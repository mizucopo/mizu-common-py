"""ログ設定ユーティリティ.

アプリケーション全体のログ設定を提供する。
"""

import logging
import sys
from typing import TextIO


class LoggingConfig:
    """ログ設定管理クラス."""

    def __init__(
        self,
        level: int = logging.INFO,
        stream: TextIO | None = None,
    ) -> None:
        """ログ設定を初期化する.

        Args:
            level: ログレベル
            stream: 出力ストリーム（デフォルトはstderr）
        """
        if stream is None:
            stream = sys.stderr

        handler = logging.StreamHandler(stream)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(handler)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """ロガーを取得する.

        Args:
            name: ロガー名

        Returns:
            設定済みのロガー
        """
        return logging.getLogger(name)
