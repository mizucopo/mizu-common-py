"""資産調整結果データクラス"""

from dataclasses import dataclass
from decimal import Decimal

from mizu_common.constants.operation_type import OperationType
from mizu_common.models.asset import Asset
from mizu_common.models.asset_calculation import AssetCalculation


@dataclass(frozen=True)
class AssetAdjustmentResult:
    """資産調整の結果

    Attributes:
        assets: 更新後の資産
        calculated_assets: 更新後の計算結果
        adjustment_amount: 入出金額（正: 入金、負: 出金）
    """

    assets: tuple[Asset, ...]
    calculated_assets: tuple[AssetCalculation, ...]
    adjustment_amount: Decimal

    @property
    def operation_type(self) -> OperationType:
        """操作タイプを返す"""
        if self.adjustment_amount > 0:
            return OperationType.DEPOSIT
        if self.adjustment_amount < 0:
            return OperationType.WITHDRAWAL
        return OperationType.NONE
