"""Discord Embedデータクラスのテスト."""

from mizu_common.models.discord_embed import DiscordEmbed


def test_to_dict_returns_all_fields() -> None:
    """to_dictが全フィールドを含む辞書を返すこと.

    Arrange:
        全フィールドを設定したEmbedを用意する。

    Act:
        to_dict()を実行する。

    Assert:
        全フィールドが含まれること。
    """
    # Arrange & Act
    embed = DiscordEmbed(
        title="Test Title",
        description="Test Description",
        color=0xFF0000,
        url="https://example.com",
    )
    result = embed.to_dict()

    # Assert
    assert result == {
        "title": "Test Title",
        "description": "Test Description",
        "color": 0xFF0000,
        "url": "https://example.com",
    }


def test_to_dict_excludes_none_fields() -> None:
    """to_dictがNoneフィールドを除外すること.

    Arrange:
        タイトルのみのEmbedを用意する。

    Act:
        to_dict()を実行する。

    Assert:
        titleのみが含まれること。
        Noneのフィールドが除外されること。
    """
    # Arrange & Act
    embed = DiscordEmbed(title="Test Title")
    result = embed.to_dict()

    # Assert
    assert result == {"title": "Test Title"}
