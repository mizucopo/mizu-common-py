"""ログ設定管理ユーティリティ.

アプリケーション全体のログ設定を提供する。
"""

import logging
import sys
from typing import TextIO


class LoggingConfigurator:
    """ログ設定管理クラス."""

    _initialized: bool = False

    def __init__(
        self,
        level: int = logging.INFO,
        stream: TextIO | None = None,
        *,
        force: bool = False,
    ) -> None:
        """ログ設定を初期化する.

        Args:
            level: ログレベル
            stream: 出力ストリーム（デフォルトはstderr）
            force: 既に初期化済みでも強制的に再初期化する
        """
        if LoggingConfigurator._initialized and not force:
            return

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
        root_logger.handlers.clear()
        root_logger.setLevel(level)
        root_logger.addHandler(handler)

        LoggingConfigurator._initialized = True

    @classmethod
    def reset(cls) -> None:
        """初期化状態をリセットする."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        cls._initialized = False

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """ロガーを取得する.

        Args:
            name: ロガー名

        Returns:
            設定済みのロガー
        """
        return logging.getLogger(name)
