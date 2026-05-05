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


def test_adjust_assets_deposit_distributed(
    service: AssetService,
    sample_assets: tuple[Asset, ...],
) -> None:
    """入金額がwater-fillingで各資産に配分されること

    Arrange
    - 入金額100,000円のデータを準備
    Act
    - adjust_assetsを実行
    Assert
    - 各資産への配分額が正の値であること
    - 入金額の合計がadjustment_amountと一致すること
    """
    # Arrange
    calculated_assets = _create_calculated_assets(sample_assets)

    # Act
    result = service.adjust_assets(calculated_assets, Decimal("100000"))

    # Assert
    assert result.calculated_assets[0].flow_amount >= Decimal("0")
    assert result.calculated_assets[1].flow_amount >= Decimal("0")
    total_flow = (
        result.calculated_assets[0].flow_amount
        + result.calculated_assets[1].flow_amount
    )
    assert total_flow == Decimal("100000")


def test_adjust_assets_withdrawal_distributed(
    service: AssetService,
    sample_assets: tuple[Asset, ...],
) -> None:
    """出金額がwater-fillingで各資産から減額されること

    Arrange
    - 出金額100,000円のデータを準備
    Act
    - adjust_assetsを実行
    Assert
    - 各資産からの減額額が負の値であること
    - 出金額の合計がadjustment_amountと一致すること
    """
    # Arrange
    calculated_assets = _create_calculated_assets(sample_assets)

    # Act
    result = service.adjust_assets(calculated_assets, Decimal("-100000"))

    # Assert
    assert result.calculated_assets[0].flow_amount <= Decimal("0")
    assert result.calculated_assets[1].flow_amount <= Decimal("0")
    total_flow = (
        result.calculated_assets[0].flow_amount
        + result.calculated_assets[1].flow_amount
    )
    assert total_flow == Decimal("-100000")


def test_adjust_assets_zero_adjustment_returns_unchanged(
    service: AssetService,
    sample_assets: tuple[Asset, ...],
) -> None:
    """調整額がゼロの場合は資産が変更されないこと

    Arrange
    - 調整額ゼロを準備
    Act
    - adjust_assetsを実行
    Assert
    - 全アセットのflow_amountが0であること
    """
    # Arrange
    calculated_assets = _create_calculated_assets(sample_assets)
    original_amounts = tuple(calc.asset.amount for calc in calculated_assets)

    # Act
    result = service.adjust_assets(calculated_assets, Decimal("0"))

    # Assert
    for calc in result.calculated_assets:
        assert calc.flow_amount == Decimal("0")
    result_amounts = tuple(asset.amount for asset in result.assets)
    assert result_amounts == original_amounts


def test_adjust_assets_zero_adjustment_empty_calculated_ok(
    service: AssetService,
) -> None:
    """adjustment_amount=0かつ空calculated_assetsでエラーにならないこと

    Arrange
    - 空のcalculated_assetsとゼロ調整額を準備
    Act
    - adjust_assetsを実行
    Assert
    - エラーにならず結果が返ること
    """
    # Arrange
    # Act
    result = service.adjust_assets((), Decimal("0"))

    # Assert
    assert result.assets == ()
    assert result.calculated_assets == ()
    assert result.adjustment_amount == Decimal("0")


def test_adjust_assets_empty_calculated_with_flow_raises(
    service: AssetService,
) -> None:
    """入出金時に空calculated_assetsでValueErrorが送出されること

    Arrange
    - 空のcalculated_assetsと非ゼロ調整額を準備
    Act & Assert
    - ValueErrorが送出されること
    """
    # Arrange
    # Act & Assert
    with pytest.raises(
        ValueError, match="calculated_assets is empty"
    ):
        service.adjust_assets((), Decimal("100000"))


def test_adjust_assets_final_total_negative_raises(
    service: AssetService,
    sample_assets: tuple[Asset, ...],
) -> None:
    """final_totalが0以下になる場合はValueErrorが送出されること

    Arrange
    - 出金額が総資産を超えるデータを準備
    Act & Assert
    - ValueErrorが送出されること
    """
    # Arrange
    calculated_assets = _create_calculated_assets(sample_assets)

    # Act & Assert
    with pytest.raises(ValueError, match="final total would be negative"):
        service.adjust_assets(calculated_assets, Decimal("-200000000"))


def test_adjust_assets_single_asset_deposit(
    service: AssetService,
) -> None:
    """単一資産ポートフォリオで入金が正しく動作すること

    Arrange
    - 単一資産を準備
    Act
    - adjust_assetsを実行
    Assert
    - 全額がその資産に追加されること
    """
    # Arrange
    assets = (Asset(name="株式", amount=Decimal("50000000"), rate=Decimal("1")),)
    calculated_assets = _create_calculated_assets(assets)

    # Act
    result = service.adjust_assets(calculated_assets, Decimal("10000"))

    # Assert
    assert result.calculated_assets[0].flow_amount == Decimal("10000")
    assert result.assets[0].amount == Decimal("50010000")
