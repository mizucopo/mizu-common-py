"""DiscordClientの使用例.

この例は以下を示します:
- テキストメッセージの送信
- Embedメッセージの送信
- 複数Embedの送信

実行方法:
    export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
    uv run python examples/example_discord.py

前提条件:
    Discord Webhook URL（環境変数 DISCORD_WEBHOOK_URL に設定）
"""

import os
import sys

from mizu_common import DiscordClient, DiscordEmbed


def main() -> None:
    """Discord通知のデモを実行する."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        print("エラー: DISCORD_WEBHOOK_URL 環境変数が設定されていません")
        print("以下のように設定してください:")
        print('  export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."')
        sys.exit(1)

    client = DiscordClient(webhook_url=webhook_url)

    # 1. テキストメッセージを送信
    print("テキストメッセージを送信中...")
    client.send_message(
        content="テストメッセージ from mizu-common-py",
        username="通知ボット",
    )
    print("  -> 送信完了")

    # 2. Embedメッセージを送信
    print("Embedメッセージを送信中...")
    embed = DiscordEmbed(
        title="処理完了",
        description="バックアップ処理が正常に完了しました",
        color=0x00FF00,  # 緑色
    )
    client.send_embed(embed)
    print("  -> 送信完了")

    # 3. 複数のEmbedを送信
    print("複数Embedメッセージを送信中...")
    embeds = [
        DiscordEmbed(
            title="ステップ1: データ収集",
            description="完了",
            color=0x00FF00,
        ),
        DiscordEmbed(
            title="ステップ2: 圧縮",
            description="完了",
            color=0x00FF00,
        ),
        DiscordEmbed(
            title="ステップ3: アップロード",
            description="完了",
            color=0x00FF00,
        ),
    ]
    client.send_embeds(embeds)
    print("  -> 送信完了")

    print("\nすべての通知が送信されました")


if __name__ == "__main__":
    main()
