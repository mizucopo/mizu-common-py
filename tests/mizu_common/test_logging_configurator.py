"""ログ設定管理ユーティリティのテスト."""

import logging
from io import StringIO

import pytest

from mizu_common.logging_configurator import LoggingConfigurator


@pytest.fixture
def string_stream() -> StringIO:
    """テスト用StringIOストリームを返す."""
    return StringIO()


def test_init_adds_handler_to_root_logger(string_stream: StringIO) -> None:
    """LoggingConfiguratorの初期化でルートロガーにハンドラーが追加されること.

    Arrange:
        出力先としてStringIOを準備する。

    Act:
        LoggingConfiguratorを初期化する。

    Assert:
        ルートロガーにハンドラーが1つ追加されていること。
    """
    # Act
    LoggingConfigurator(level=logging.DEBUG, stream=string_stream)

    # Assert
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1


def test_multiple_init_does_not_duplicate_handlers(string_stream: StringIO) -> None:
    """複数回初期化してもハンドラーが重複しないこと.

    Arrange:
        出力先としてStringIOを準備する。

    Act:
        LoggingConfiguratorを複数回初期化する。

    Assert:
        ルートロガーのハンドラー数が1のままであること。
    """
    # Act
    LoggingConfigurator(level=logging.INFO, stream=string_stream)
    LoggingConfigurator(level=logging.DEBUG, stream=string_stream)
    LoggingConfigurator(level=logging.WARNING, stream=string_stream)

    # Assert
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1


def test_force_parameter_allows_reinitialization(string_stream: StringIO) -> None:
    """forceパラメータで再初期化できること.

    Arrange:
        出力先としてStringIOを準備する。
        LoggingConfiguratorを初期化する。

    Act:
        force=TrueでLoggingConfiguratorを再度初期化する。

    Assert:
        ルートロガーのハンドラー数が1のままであること（クリア後に追加される）。
        ログレベルが新しい値に更新されていること。
    """
    # Arrange
    LoggingConfigurator(level=logging.INFO, stream=string_stream)

    # Act
    LoggingConfigurator(level=logging.DEBUG, stream=string_stream, force=True)

    # Assert
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1
    assert root_logger.level == logging.DEBUG


def test_reset_clears_initialization_state(string_stream: StringIO) -> None:
    """resetメソッドが初期化状態をクリアすること.

    Arrange:
        LoggingConfiguratorを初期化する。

    Act:
        resetメソッドを呼び出す。

    Assert:
        ルートロガーのハンドラーがクリアされること。
        その後再度初期化すると新しいハンドラーが追加されること。
    """
    # Arrange
    LoggingConfigurator(level=logging.INFO, stream=string_stream)
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1

    # Act
    LoggingConfigurator.reset()

    # Assert
    assert len(root_logger.handlers) == 0

    # 再度初期化すると新しいハンドラーが追加されること
    LoggingConfigurator(level=logging.DEBUG, stream=string_stream)
    assert len(root_logger.handlers) == 1
