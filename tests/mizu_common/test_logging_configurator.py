"""ログ設定管理ユーティリティのテスト."""

import logging
from io import StringIO

from mizu_common.logging_configurator import LoggingConfigurator


def test_init_adds_handler_to_root_logger() -> None:
    """LoggingConfiguratorの初期化でルートロガーにハンドラーが追加されること.

    Arrange:
        出力先としてStringIOを準備する。

    Act:
        LoggingConfiguratorを初期化する。

    Assert:
        ルートロガーにハンドラーが追加されていること。
    """
    # Arrange
    stream = StringIO()

    # Act
    LoggingConfigurator(level=logging.DEBUG, stream=stream)

    # Assert
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0
