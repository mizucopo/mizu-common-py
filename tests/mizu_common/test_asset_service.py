"""資産調整ロジックモジュールのテスト"""

from decimal import Decimal
from typing import Any

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
    with pytest.raises(ValueError, match="calculated_assets is empty"):
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


# テストケースのデータ定義
TEST_CASES_01_07 = [
    # test_case_01: 入金_ちょうど目標に一致するケース
    {
        "id": "test_case_01",
        "name": "入金_ちょうど目標に一致するケース",
        "current": {
            "stocks": 30000,
            "bonds": 10000,
            "reit": 5000,
            "gold": 5000,
        },
        "target": {
            "stocks": 0.60,
            "bonds": 0.20,
            "reit": 0.10,
            "gold": 0.10,
        },
        "flow": 0,
        "expected_delta": {
            "stocks": 0,
            "bonds": 0,
            "reit": 0,
            "gold": 0,
        },
        "expected_final": {
            "stocks": 30000,
            "bonds": 10000,
            "reit": 5000,
            "gold": 5000,
        },
        "expected_error": None,
    },
    # test_case_02: 不足額を埋めれば完全一致
    {
        "id": "test_case_02",
        "name": "入金_不足額を埋めれば完全一致",
        "current": {
            "stocks": 20000,
            "bonds": 5000,
            "reit": 5000,
            "gold": 0,
        },
        "target": {
            "stocks": 0.50,
            "bonds": 0.20,
            "reit": 0.20,
            "gold": 0.10,
        },
        "flow": 20000,
        "expected_delta": {
            "stocks": 5000,
            "bonds": 5000,
            "reit": 5000,
            "gold": 5000,
        },
        "expected_final": {
            "stocks": 25000,
            "bonds": 10000,
            "reit": 10000,
            "gold": 5000,
        },
        "expected_error": None,
    },
    # test_case_03: 入金_不足額比例配分_端数切り捨てあり
    {
        "id": "test_case_03",
        "name": "入金_不足額比例配分_端数切り捨てあり",
        "current": {
            "stocks": 10000,
            "bonds": 10000,
            "reit": 10000,
            "gold": 10000,
        },
        "target": {
            "stocks": 0.70,
            "bonds": 0.20,
            "reit": 0.05,
            "gold": 0.05,
        },
        "flow": 10000,
        "expected_delta": {
            "stocks": 10000,
            "bonds": 0,
            "reit": 0,
            "gold": 0,
        },
        "expected_final": {
            "stocks": 20000,
            "bonds": 10000,
            "reit": 10000,
            "gold": 10000,
        },
        "expected_error": None,
    },
    # test_case_04: 入金_複数資産water-filling_最大余剰法あり
    {
        "id": "test_case_04",
        "name": "入金_複数資産water-filling_最大余剰法あり",
        "current": {
            "stocks": 10000,
            "bonds": 10000,
            "reit": 10000,
            "gold": 10000,
        },
        "target": {
            "stocks": 0.50,
            "bonds": 0.30,
            "reit": 0.15,
            "gold": 0.05,
        },
        "flow": 10001,
        "expected_delta": {
            "stocks": 8751,
            "bonds": 1250,
            "reit": 0,
            "gold": 0,
        },
        "expected_final": {
            "stocks": 18751,
            "bonds": 11250,
            "reit": 10000,
            "gold": 10000,
        },
        "expected_error": None,
    },
    # test_case_05: 出金_ちょうど目標に一致するケース
    {
        "id": "test_case_05",
        "name": "出金_ちょうど目標に一致するケース",
        "current": {
            "stocks": 40000,
            "bonds": 20000,
            "reit": 10000,
            "gold": 10000,
        },
        "target": {
            "stocks": 0.60,
            "bonds": 0.20,
            "reit": 0.10,
            "gold": 0.10,
        },
        "flow": -30000,
        "expected_delta": {
            "stocks": -10000,
            "bonds": -10000,
            "reit": -5000,
            "gold": -5000,
        },
        "expected_final": {
            "stocks": 30000,
            "bonds": 10000,
            "reit": 5000,
            "gold": 5000,
        },
        "expected_error": None,
    },
    # test_case_06: 出金_最も水位の高いアセットから優先引出
    {
        "id": "test_case_06",
        "name": "出金_最も水位の高いアセットから優先引出",
        "current": {
            "stocks": 50000,
            "bonds": 10000,
            "reit": 10000,
            "gold": 10000,
        },
        "target": {
            "stocks": 0.40,
            "bonds": 0.30,
            "reit": 0.20,
            "gold": 0.10,
        },
        "flow": -10000,
        "expected_delta": {
            "stocks": -10000,
            "bonds": 0,
            "reit": 0,
            "gold": 0,
        },
        "expected_final": {
            "stocks": 40000,
            "bonds": 10000,
            "reit": 10000,
            "gold": 10000,
        },
        "expected_error": None,
    },
    # test_case_07: 出金_複数超過のwater-filling_最大余剰法
    {
        "id": "test_case_07",
        "name": "出金_複数超過のwater-filling_最大余剰法",
        "current": {
            "stocks": 30000,
            "bonds": 30000,
            "reit": 30000,
            "gold": 10000,
        },
        "target": {
            "stocks": 0.50,
            "bonds": 0.20,
            "reit": 0.20,
            "gold": 0.10,
        },
        "flow": -10001,
        "expected_delta": {
            "stocks": 0,
            "bonds": -5001,
            "reit": -5000,
            "gold": 0,
        },
        "expected_final": {
            "stocks": 30000,
            "bonds": 24999,
            "reit": 25000,
            "gold": 10000,
        },
        "expected_error": None,
    },
]


TEST_CASES_08_12 = [
    # test_case_08: 入金_最も水位の低いアセットに全額配分
    {
        "id": "test_case_08",
        "name": "入金_最も水位の低いアセットに全額配分",
        "current": {
            "stocks": 10000,
            "bonds": 50000,
            "reit": 10000,
            "gold": 10000,
        },
        "target": {
            "stocks": 0.50,
            "bonds": 0.20,
            "reit": 0.20,
            "gold": 0.10,
        },
        "flow": 10000,
        "expected_delta": {
            "stocks": 10000,
            "bonds": 0,
            "reit": 0,
            "gold": 0,
        },
        "expected_final": {
            "stocks": 20000,
            "bonds": 50000,
            "reit": 10000,
            "gold": 10000,
        },
        "expected_error": None,
    },
    # test_case_09: 出金_超過アセット2つのwater-filling
    {
        "id": "test_case_09",
        "name": "出金_超過アセット2つのwater-filling",
        "current": {
            "stocks": 10000,
            "bonds": 10000,
            "reit": 50000,
            "gold": 30000,
        },
        "target": {
            "stocks": 0.40,
            "bonds": 0.30,
            "reit": 0.20,
            "gold": 0.10,
        },
        "flow": -20000,
        "expected_delta": {
            "stocks": 0,
            "bonds": 0,
            "reit": -10000,
            "gold": -10000,
        },
        "expected_final": {
            "stocks": 10000,
            "bonds": 10000,
            "reit": 40000,
            "gold": 20000,
        },
        "expected_error": None,
    },
    # test_case_10: 2資産_入金
    {
        "id": "test_case_10",
        "name": "2資産_入金",
        "current": {"risky": 10000, "safe": 30000},
        "target": {"risky": 0.50, "safe": 0.50},
        "flow": 10000,
        "expected_delta": {"risky": 10000, "safe": 0},
        "expected_final": {"risky": 20000, "safe": 30000},
        "expected_error": None,
    },
    # test_case_11: 2資産_出金
    {
        "id": "test_case_11",
        "name": "2資産_出金",
        "current": {"risky": 40000, "safe": 10000},
        "target": {"risky": 0.50, "safe": 0.50},
        "flow": -10000,
        "expected_delta": {"risky": -10000, "safe": 0},
        "expected_final": {"risky": 30000, "safe": 10000},
        "expected_error": None,
    },
    # test_case_12: 全額出金（final_total=0）はValueError
    {
        "id": "test_case_12",
        "name": "境界値_全額出金はValueError",
        "current": {
            "stocks": 15000,
            "bonds": 10000,
            "reit": 5000,
            "gold": 20000,
        },
        "target": {
            "stocks": 0.40,
            "bonds": 0.30,
            "reit": 0.20,
            "gold": 0.10,
        },
        "flow": -50000,
        "expected_delta": None,
        "expected_final": None,
        "expected_error": "final total would be negative",
    },
]


TEST_CASES_13 = [
    # test_case_13: 異常系_最終総額が負
    {
        "id": "test_case_13",
        "name": "異常系_最終総額が負",
        "current": {
            "stocks": 10000,
            "bonds": 10000,
            "reit": 10000,
            "gold": 10000,
        },
        "target": {
            "stocks": 0.25,
            "bonds": 0.25,
            "reit": 0.25,
            "gold": 0.25,
        },
        "flow": -50000,
        "expected_delta": None,
        "expected_final": None,
        "expected_error": "final total would be negative",
    },
]


def _build_test_data_from_case(
    case: dict[str, Any],
) -> tuple[tuple[AssetCalculation, ...], Decimal]:
    """テストケースからテストデータを構築するヘルパー関数

    Args:
        case: テストケースデータ

    Returns:
        (calculated_assets, adjustment_amount)のタプル
    """
    assets = tuple(
        Asset(
            name=name,
            amount=Decimal(str(amount)),
            rate=Decimal(str(case["target"][name])),
        )
        for name, amount in case["current"].items()
    )
    calculated_assets = _create_calculated_assets(assets)
    return calculated_assets, Decimal(str(case["flow"]))


_IDS_01_07 = [str(c["id"]) for c in TEST_CASES_01_07]


@pytest.mark.parametrize("case", TEST_CASES_01_07, ids=_IDS_01_07)
def test_water_filling_allocation_cases_01_07(
    service: AssetService,
    case: dict[str, Any],
) -> None:
    """water-filling配分が正しく動作すること（ケース01-07）

    Arrange
    - テストケースのデータからテストデータを構築
    Act
    - adjust_assetsを実行
    Assert
    - 各資産のdeltaとfinalが期待値と一致すること
    """
    # Arrange
    calculated_assets, adjustment_amount = _build_test_data_from_case(case)

    # Act
    result = service.adjust_assets(calculated_assets, adjustment_amount)

    # Assert
    for calc in result.calculated_assets:
        name = calc.asset.name
        delta = calc.flow_amount
        expected_delta = Decimal(str(case["expected_delta"][name]))
        expected_final = Decimal(str(case["expected_final"][name]))

        assert delta == expected_delta, (
            f"{name}: delta {delta} != expected {expected_delta}"
        )
        assert calc.asset.amount == expected_final, (
            f"{name}: final {calc.asset.amount} != expected {expected_final}"
        )


_IDS_08_12 = [str(c["id"]) for c in TEST_CASES_08_12]


@pytest.mark.parametrize("case", TEST_CASES_08_12, ids=_IDS_08_12)
def test_water_filling_allocation_cases_08_12(
    service: AssetService,
    case: dict[str, Any],
) -> None:
    """water-filling配分が正しく動作すること（ケース08-12）

    Arrange
    - テストケースのデータからテストデータを構築
    Act
    - adjust_assetsを実行
    Assert
    - 各資産のdeltaとfinalが期待値と一致すること
    - エラー期待値がある場合はValueErrorが送出されること
    """
    # Arrange
    calculated_assets, adjustment_amount = _build_test_data_from_case(case)

    # Act & Assert
    if case["expected_error"]:
        with pytest.raises(ValueError, match=str(case["expected_error"])):
            service.adjust_assets(calculated_assets, adjustment_amount)
        return

    result = service.adjust_assets(calculated_assets, adjustment_amount)

    for calc in result.calculated_assets:
        name = calc.asset.name
        delta = calc.flow_amount
        expected_delta = Decimal(str(case["expected_delta"][name]))
        expected_final = Decimal(str(case["expected_final"][name]))

        assert delta == expected_delta, (
            f"{name}: delta {delta} != expected {expected_delta}"
        )
        assert calc.asset.amount == expected_final, (
            f"{name}: final {calc.asset.amount} != expected {expected_final}"
        )


def test_water_filling_allocation_case_13_error(
    service: AssetService,
) -> None:
    """異常系：最終総額が負になる場合はエラーが発生すること

    Arrange
    - 出金額が総資産を超えるデータを準備
    Act & Assert
    - ValueErrorが送出されること
    """
    # Arrange
    case = TEST_CASES_13[0]
    calculated_assets, adjustment_amount = _build_test_data_from_case(case)

    # Act & Assert
    with pytest.raises(ValueError, match=str(case["expected_error"])):
        service.adjust_assets(calculated_assets, adjustment_amount)


def test_deposit_waterfilling_two_underweight_assets(
    service: AssetService,
) -> None:
    """入金時のwater-fillingで水位の低いアセットが優先されること

    Arrange
    - 2つの不足アセットと2つの超過アセットを準備
    Act
    - adjust_assetsを実行
    Assert
    - 最も水位の低いアセットに多く配分されること
    - flow_amountの合計がflowと一致すること
    """
    # Arrange
    assets = (
        Asset(name="stocks", amount=Decimal("10000"), rate=Decimal("0.50")),
        Asset(name="bonds", amount=Decimal("10000"), rate=Decimal("0.30")),
        Asset(name="reit", amount=Decimal("10000"), rate=Decimal("0.15")),
        Asset(name="gold", amount=Decimal("10000"), rate=Decimal("0.05")),
    )
    calculated_assets = _create_calculated_assets(assets)

    # Act
    result = service.adjust_assets(calculated_assets, Decimal("10001"))

    # Assert
    flow_map = {calc.asset.name: calc.flow_amount for calc in result.calculated_assets}
    assert flow_map["stocks"] == Decimal("8751")
    assert flow_map["bonds"] == Decimal("1250")
    assert flow_map["reit"] == Decimal("0")
    assert flow_map["gold"] == Decimal("0")
    total = sum(calc.flow_amount for calc in result.calculated_assets)
    assert total == Decimal("10001")


def test_withdrawal_waterfilling_two_overweight_assets(
    service: AssetService,
) -> None:
    """出金時のwater-fillingで水位の高いアセットが優先されること

    Arrange
    - 2つの超過アセットと2つの不足アセットを準備
    Act
    - adjust_assetsを実行
    Assert
    - 最も水位の高いアセットから多く引出されること
    - flow_amountの合計がflowと一致すること
    """
    # Arrange
    assets = (
        Asset(name="stocks", amount=Decimal("10000"), rate=Decimal("0.40")),
        Asset(name="bonds", amount=Decimal("10000"), rate=Decimal("0.30")),
        Asset(name="reit", amount=Decimal("50000"), rate=Decimal("0.20")),
        Asset(name="gold", amount=Decimal("30000"), rate=Decimal("0.10")),
    )
    calculated_assets = _create_calculated_assets(assets)

    # Act
    result = service.adjust_assets(calculated_assets, Decimal("-20000"))

    # Assert
    flow_map = {calc.asset.name: calc.flow_amount for calc in result.calculated_assets}
    assert flow_map["gold"] == Decimal("-10000")
    assert flow_map["reit"] == Decimal("-10000")
    assert flow_map["stocks"] == Decimal("0")
    assert flow_map["bonds"] == Decimal("0")
    total = sum(calc.flow_amount for calc in result.calculated_assets)
    assert total == Decimal("-20000")


def test_all_assets_at_target_deposit_distributes_proportionally(
    service: AssetService,
) -> None:
    """全アセット目標通りで入金がrate比例配分されること

    Arrange
    - 全アセットが目標比率どおりのデータを準備
    Act
    - adjust_assetsを実行
    Assert
    - 各アセットにrate比例で配分されること
    - flow_amountの合計がflowと一致すること
    """
    # Arrange
    assets = (
        Asset(name="stocks", amount=Decimal("30000"), rate=Decimal("0.50")),
        Asset(name="bonds", amount=Decimal("18000"), rate=Decimal("0.30")),
        Asset(name="reit", amount=Decimal("12000"), rate=Decimal("0.20")),
    )
    calculated_assets = _create_calculated_assets(assets)

    # Act
    result = service.adjust_assets(calculated_assets, Decimal("10000"))

    # Assert
    flow_map = {calc.asset.name: calc.flow_amount for calc in result.calculated_assets}
    assert flow_map["stocks"] == Decimal("5000")
    assert flow_map["bonds"] == Decimal("3000")
    assert flow_map["reit"] == Decimal("2000")
    total = sum(calc.flow_amount for calc in result.calculated_assets)
    assert total == Decimal("10000")


def test_public_api_includes_asset_classes() -> None:
    """__all__にAssetService関連クラスが含まれること

    Arrange
    - mizu_commonパッケージをインポート
    Act & Assert
    - __all__に必要なクラスが含まれること
    """
    # Arrange
    import mizu_common

    # Act & Assert
    assert "AssetService" in mizu_common.__all__
    assert "Asset" in mizu_common.__all__
    assert "AssetCalculation" in mizu_common.__all__
    assert "AssetAdjustmentResult" in mizu_common.__all__
    assert "OperationType" in mizu_common.__all__


def test_adjustment_result_operation_type_deposit() -> None:
    """正のadjustment_amountでDEPOSITが返されること"""
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
    assert result.operation_type == OperationType.DEPOSIT


def test_adjustment_result_operation_type_withdrawal() -> None:
    """負のadjustment_amountでWITHDRAWALが返されること"""
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
    assert result.operation_type == OperationType.WITHDRAWAL


def test_adjustment_result_operation_type_none() -> None:
    """ゼロのadjustment_amountでNONEが返されること"""
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
    assert result.operation_type == OperationType.NONE
