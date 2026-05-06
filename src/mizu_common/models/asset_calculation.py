"""資産計算結果データクラス"""

from dataclasses import dataclass, field
from decimal import Decimal

from mizu_common.models.asset import Asset


@dataclass(frozen=True)
class AssetCalculation:
    """資産の計算結果（処理ごとに生成される一時的な状態）

    Attributes:
        asset: 元の資産データ
        current_rate: 現在の配分比率
        flow_amount: 入出金額（正: 入金、負: 出金、0: 変更なし）
    """

    asset: Asset
    current_rate: Decimal = field(default=Decimal("0"))
    flow_amount: Decimal = field(default=Decimal("0"))
