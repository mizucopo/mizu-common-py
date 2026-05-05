"""資産調整ロジックモジュールのテスト"""

from decimal import Decimal

import pytest

from mizu_common.asset_service import AssetService
from mizu_common.constants.operation_type import OperationType
from mizu_common.models.asset import Asset
from mizu_common.models.asset_adjustment_result import AssetAdjustmentResult
from mizu_common.models.asset_calculation import AssetCalculation


@pytest.fixture
def service() -> AssetService:
    """AssetServiceのインスタンスが返されること"""
    return AssetService()


@pytest.fixture
def sample_assets() -> tuple[Asset, ...]:
    """テスト用の共通資産構成が返されること"""
    return (
        Asset(name="株式", amount=Decimal("60000000"), rate=Decimal("0.60")),
        Asset(name="債券", amount=Decimal("40000000"), rate=Decimal("0.40")),
    )


def _create_calculated_assets(
    assets: tuple[Asset, ...],
) -> tuple[AssetCalculation, ...]:
    """テスト用AssetCalculationタプルを生成すること"""
    return tuple(AssetCalculation(asset=asset) for asset in assets)


def test_calculate_current_rates_returns_correct_rates(
    service: AssetService,
    sample_assets: tuple[Asset, ...],
) -> None:
    """現在配分比率が正しく計算されること

    Arrange
    - 既知の資産構成を準備
    Act
    - calculate_current_ratesを実行
    Assert
    - 各資産の現在配分比率が正しく計算されること
    """
    # Arrange
    # Act
    result = service.calculate_current_rates(sample_assets)

    # Assert
    assert result[0].current_rate == Decimal("0.6")
    assert result[1].current_rate == Decimal("0.4")


def test_calculate_current_rates_zero_total_raises(
    service: AssetService,
) -> None:
    """資産合計がゼロの場合はValueErrorが送出されること

    Arrange
    - 金額がゼロの資産を準備
    Act & Assert
    - ValueErrorが送出されること
    """
    # Arrange
    assets = (
        Asset(name="株式", amount=Decimal("0"), rate=Decimal("0.60")),
        Asset(name="債券", amount=Decimal("0"), rate=Decimal("0.40")),
    )

    # Act & Assert
    with pytest.raises(ValueError, match="total amount must be positive"):
        service.calculate_current_rates(assets)


def test_calculate_current_rates_empty_assets_raises(
    service: AssetService,
) -> None:
    """assetsが空の場合はValueErrorが送出されること

    Arrange
    - 空のassetsを準備
    Act & Assert
    - ValueErrorが送出されること
    """
    # Arrange
    # Act & Assert
    with pytest.raises(ValueError, match="assets must not be empty"):
        service.calculate_current_rates(())


def test_calculate_current_rates_negative_total_raises(
    service: AssetService,
) -> None:
    """資産合計額が0以下の場合はValueErrorが送出されること

    Arrange
    - 金額が負の資産を準備
    Act & Assert
    - ValueErrorが送出されること
    """
    # Arrange
    assets = (
        Asset(name="株式", amount=Decimal("-1000"), rate=Decimal("0.60")),
        Asset(name="債券", amount=Decimal("500"), rate=Decimal("0.40")),
    )

    # Act & Assert
    with pytest.raises(ValueError, match="total amount must be positive"):
        service.calculate_current_rates(assets)
