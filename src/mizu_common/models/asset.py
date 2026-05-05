"""処理用Assetデータクラス"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Asset:
    """処理用の資産データ

    Attributes:
        name: 資産名
        amount: 現在の金額
        rate: 目標配分割合
    """

    name: str
    amount: Decimal
    rate: Decimal
