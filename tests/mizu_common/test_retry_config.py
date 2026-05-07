"""RetryConfigデータクラスのテスト."""

import pytest

from mizu_common.retry_config import RetryConfig


def test_valid_config_with_positive_values() -> None:
    """正常な値でRetryConfigが生成されること.

    Arrange:
        正のcountとintervalを用意する。

    Act:
        RetryConfigを生成する。

    Assert:
        インスタンスが正しく生成されること。
    """
    # Arrange
    # Act
    config = RetryConfig(count=3, interval=10.0)

    # Assert
    assert config.count == 3
    assert config.interval == 10.0


def test_zero_count_is_valid() -> None:
    """count=0でRetryConfigが生成されること.

    Arrange:
        count=0、正のintervalを用意する。

    Act:
        RetryConfigを生成する。

    Assert:
        countが0であること。
    """
    # Arrange
    # Act
    config = RetryConfig(count=0, interval=5.0)

    # Assert
    assert config.count == 0


def test_negative_count_raises_error() -> None:
    """countが負の値の場合にValueErrorが送出されること.

    Arrange:
        count=-1、正のintervalを用意する。

    Act:
        RetryConfigを生成する。

    Assert:
        ValueErrorが送出されること。
    """
    # Arrange
    # Act
    with pytest.raises(ValueError) as exc_info:
        RetryConfig(count=-1, interval=1.0)

    # Assert
    assert "count must be >= 0" in str(exc_info.value)


def test_zero_interval_raises_error() -> None:
    """interval=0の場合にValueErrorが送出されること.

    Arrange:
        正のcount、interval=0を用意する。

    Act:
        RetryConfigを生成する。

    Assert:
        ValueErrorが送出されること。
    """
    # Arrange
    # Act
    with pytest.raises(ValueError) as exc_info:
        RetryConfig(count=2, interval=0)

    # Assert
    assert "interval must be > 0" in str(exc_info.value)


def test_negative_interval_raises_error() -> None:
    """intervalが負の値の場合にValueErrorが送出されること.

    Arrange:
        正のcount、負のintervalを用意する。

    Act:
        RetryConfigを生成する。

    Assert:
        ValueErrorが送出されること。
    """
    # Arrange
    # Act
    with pytest.raises(ValueError) as exc_info:
        RetryConfig(count=2, interval=-1.0)

    # Assert
    assert "interval must be > 0" in str(exc_info.value)
