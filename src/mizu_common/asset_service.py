"""資産調整ロジックモジュール"""

from dataclasses import replace
from decimal import ROUND_FLOOR, Decimal

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
                またはrateが正でない場合、
                またはrateの合計が1でない場合、
                または資産合計額が0以下の場合
        """
        if not assets:
            raise ValueError("assets must not be empty")

        if any(asset.rate <= 0 for asset in assets):
            raise ValueError("all rates must be positive")

        if sum(asset.rate for asset in assets) != Decimal("1"):
            raise ValueError("rates must sum to 1")

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
        """操作タイプに応じて資産を調整する

        Args:
            calculated_assets: 計算結果の資産リスト
            adjustment_amount: 調整額（正: 入金、負: 出金）

        Returns:
            調整結果

        Raises:
            ValueError: adjustment_amountが整数でない場合、
                または入出金時にcalculated_assetsが空の場合、
                またはrateが正でない場合、
                またはrateの合計が1でない場合、
                またはfinal_totalが0以下の場合、
                または配分対象アセットが存在しない場合
        """
        if adjustment_amount == 0:
            assets = tuple(calc.asset for calc in calculated_assets)
            return AssetAdjustmentResult(
                assets=assets,
                calculated_assets=calculated_assets,
                adjustment_amount=adjustment_amount,
            )

        if not calculated_assets:
            raise ValueError(
                "calculated_assets is empty. Run calculate_current_rates first."
            )

        if any(calc.asset.rate <= 0 for calc in calculated_assets):
            raise ValueError("all rates must be positive")

        if sum(calc.asset.rate for calc in calculated_assets) != Decimal("1"):
            raise ValueError("rates must sum to 1")

        if adjustment_amount != adjustment_amount.to_integral_value():
            raise ValueError("adjustment_amount must be an integer")

        return self._allocate(calculated_assets, adjustment_amount)

    def _allocate(
        self,
        calculated_assets: tuple[AssetCalculation, ...],
        adjustment_amount: Decimal,
    ) -> AssetAdjustmentResult:
        """water-fillingで資産配分を調整する

        Args:
            calculated_assets: 計算結果の資産リスト
            adjustment_amount: 調整額

        Returns:
            調整結果

        Raises:
            ValueError: final_totalが0以下の場合、
                または配分対象アセットが存在しない場合
        """
        assets = tuple(calc.asset for calc in calculated_assets)
        current_total = sum(asset.amount for asset in assets)
        flow = adjustment_amount
        final_total = current_total + flow

        if final_total <= 0:
            raise ValueError("final total would be negative")

        direction = 1 if flow > 0 else -1
        exact_amounts = self._water_filling(assets, flow, final_total, direction)
        rounded_amounts = self._apply_largest_remainder(exact_amounts, flow)

        new_calculated_assets = []
        new_assets = []
        for calc, amount in zip(calculated_assets, rounded_amounts, strict=True):
            new_calc = self._update_asset(calc, amount)
            new_calculated_assets.append(new_calc)
            new_assets.append(new_calc.asset)

        return AssetAdjustmentResult(
            assets=tuple(new_assets),
            calculated_assets=tuple(new_calculated_assets),
            adjustment_amount=adjustment_amount,
        )

    def _water_filling(
        self,
        assets: tuple[Asset, ...],
        flow: Decimal,
        final_total: Decimal,
        direction: int,
    ) -> list[Decimal]:
        """water-fillingで各アセットの正確なflow_amountを計算する"""
        items: list[tuple[int, Asset, Decimal]] = []
        for idx, asset in enumerate(assets):
            level = asset.amount / asset.rate
            is_target = (direction == 1 and level < final_total) or (
                direction == -1 and level > final_total
            )
            if is_target:
                items.append((idx, asset, level))

        if not items:
            msg = (
                "no underweight assets for deposit"
                if direction == 1
                else "no overweight assets for withdrawal"
            )
            raise ValueError(msg)

        items.sort(key=lambda x: direction * x[2])

        flow_amounts = [Decimal("0")] * len(assets)
        remaining = abs(flow)
        current_level = items[0][2]
        group_rate_sum = items[0][1].rate

        for i, (_idx, asset, _level) in enumerate(items):
            if i > 0:
                group_rate_sum += asset.rate

            next_level = items[i + 1][2] if i + 1 < len(items) else final_total
            level_delta = abs(next_level - current_level)
            cost = level_delta * group_rate_sum

            if cost <= remaining:
                for j in range(i + 1):
                    item_idx, item_asset, _ = items[j]
                    flow_amounts[item_idx] += direction * level_delta * item_asset.rate
                remaining -= cost
                current_level = next_level
            else:
                partial_delta = remaining / group_rate_sum
                for j in range(i + 1):
                    item_idx, item_asset, _ = items[j]
                    flow_amounts[item_idx] += (
                        direction * partial_delta * item_asset.rate
                    )
                break

        return flow_amounts

    def _apply_largest_remainder(
        self,
        exact_amounts: list[Decimal],
        flow: Decimal,
    ) -> list[Decimal]:
        """最大余剰法で端数処理を行う"""
        abs_amounts = [abs(a) for a in exact_amounts]
        floored = [a.to_integral_value(rounding=ROUND_FLOOR) for a in abs_amounts]

        total_floored = sum(floored)
        remainder = abs(flow) - total_floored

        fracs = [(i, abs_amounts[i] - floored[i]) for i in range(len(abs_amounts))]
        fracs.sort(key=lambda x: -x[1])

        result = list(floored)
        for k in range(int(remainder)):
            idx, _ = fracs[k]
            result[idx] += Decimal("1")

        sign = Decimal("1") if flow > 0 else Decimal("-1")
        return [sign * r for r in result]

    @staticmethod
    def _update_asset(calc: AssetCalculation, amount: Decimal) -> AssetCalculation:
        """アセットの金額とflow_amountを更新する"""
        new_asset = replace(calc.asset, amount=calc.asset.amount + amount)
        return replace(calc, asset=new_asset, flow_amount=amount)
