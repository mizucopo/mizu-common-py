"""テスト共通フィクスチャ."""

from collections.abc import Generator

import pytest

from mizu_common.logging_configurator import LoggingConfigurator


@pytest.fixture(autouse=True)
def reset_logging() -> Generator[None, None, None]:
    """各テスト前後でログ設定をリセットする.

    Arrange:
        テスト実行前にLoggingConfiguratorの状態をリセットする。

    Teardown:
        テスト実行後にLoggingConfiguratorの状態をリセットする。
    """
    LoggingConfigurator.reset()
    yield
    LoggingConfigurator.reset()
