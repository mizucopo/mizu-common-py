"""資産調整操作タイプのEnum"""

from enum import Enum


class AssetAdjustmentType(str, Enum):
    """資産調整の操作タイプ"""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    NONE = "none"
