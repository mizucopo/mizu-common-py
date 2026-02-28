"""Discord Embedデータクラスモジュール."""

from dataclasses import dataclass
from typing import Any


@dataclass
class DiscordEmbed:
    """Discord Embedデータクラス.

    Attributes:
        title: 埋め込みのタイトル
        description: 埋め込みの説明
        color: 埋め込みの色（10進数）
        url: タイトルのリンク先URL
    """

    title: str
    description: str | None = None
    color: int | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Embedを辞書形式に変換する.

        Returns:
            Discord API用のEmbed辞書
        """
        embed: dict[str, Any] = {"title": self.title}
        if self.description is not None:
            embed["description"] = self.description
        if self.color is not None:
            embed["color"] = self.color
        if self.url is not None:
            embed["url"] = self.url
        return embed
