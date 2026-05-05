"""資産調整ロジックモジュール"""

from dataclasses import replace
from decimal import Decimal

from mizu_common.models.asset import Asset
from mizu_common.models.asset_adjustment_result import AssetAdjustmentResult
from mizu_common.models.asset_calculation import AssetCalculation


class AssetService:
    """資産の配分調整を行う"""

    def calculate_current_rates(
        self, assets: tuple[Asset, ...]
    ) -> tuple[AssetCalculation, ...]:
        """各資産の現在配分比率を計算する

        Args:
            assets: 資産リスト

        Returns:
            各資産の計算結果

        Raises:
            ValueError: assetsが空の場合、
                または資産合計額が0以下の場合
        """
        if not assets:
            raise ValueError("assets must not be empty")

        sum_amount = sum(asset.amount for asset in assets)
        if sum_amount <= 0:
            raise ValueError("total amount must be positive")

        return tuple(
            AssetCalculation(
                asset=asset,
                current_rate=asset.amount / sum_amount,
            )
            for asset in assets
        )

    def adjust_assets(
        self,
        calculated_assets: tuple[AssetCalculation, ...],
        adjustment_amount: Decimal,
    ) -> AssetAdjustmentResult:
        raise NotImplementedError
