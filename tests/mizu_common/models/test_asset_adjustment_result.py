"""AssetAdjustmentResultのテスト."""

from decimal import Decimal

from mizu_common.constants.asset_adjustment_type import AssetAdjustmentType
from mizu_common.models.asset import Asset
from mizu_common.models.asset_adjustment_result import AssetAdjustmentResult
from mizu_common.models.asset_calculation import AssetCalculation


def _create_calculated_assets(
    assets: tuple[Asset, ...],
) -> tuple[AssetCalculation, ...]:
    """テスト用AssetCalculationタプルを生成すること."""
    return tuple(AssetCalculation(asset=asset) for asset in assets)


def test_operation_type_is_deposit_for_positive_amount() -> None:
    """正のadjustment_amountでDEPOSITが返されること.

    Arrange:
        正のadjustment_amountを持つAssetAdjustmentResultを準備する。

    Act:
        operation_typeプロパティにアクセスする。

    Assert:
        DEPOSITが返されること。
    """
    # Arrange
    assets = (Asset(name="株式", amount=Decimal("10000"), rate=Decimal("1")),)
    calculated_assets = _create_calculated_assets(assets)

    # Act
    result = AssetAdjustmentResult(
        assets=assets,
        calculated_assets=calculated_assets,
        adjustment_amount=Decimal("10000"),
    )

    # Assert
    assert result.operation_type == AssetAdjustmentType.DEPOSIT


def test_operation_type_is_withdrawal_for_negative_amount() -> None:
    """負のadjustment_amountでWITHDRAWALが返されること.

    Arrange:
        負のadjustment_amountを持つAssetAdjustmentResultを準備する。

    Act:
        operation_typeプロパティにアクセスする。

    Assert:
        WITHDRAWALが返されること。
    """
    # Arrange
    assets = (Asset(name="株式", amount=Decimal("10000"), rate=Decimal("1")),)
    calculated_assets = _create_calculated_assets(assets)

    # Act
    result = AssetAdjustmentResult(
        assets=assets,
        calculated_assets=calculated_assets,
        adjustment_amount=Decimal("-10000"),
    )

    # Assert
    assert result.operation_type == AssetAdjustmentType.WITHDRAWAL


def test_operation_type_is_none_for_zero_amount() -> None:
    """ゼロのadjustment_amountでNONEが返されること.

    Arrange:
        ゼロのadjustment_amountを持つAssetAdjustmentResultを準備する。

    Act:
        operation_typeプロパティにアクセスする。

    Assert:
        NONEが返されること。
    """
    # Arrange
    assets = (Asset(name="株式", amount=Decimal("10000"), rate=Decimal("1")),)
    calculated_assets = _create_calculated_assets(assets)

    # Act
    result = AssetAdjustmentResult(
        assets=assets,
        calculated_assets=calculated_assets,
        adjustment_amount=Decimal("0"),
    )

    # Assert
    assert result.operation_type == AssetAdjustmentType.NONE
