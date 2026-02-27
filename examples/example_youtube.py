"""YouTubeClientの使用例.

この例は以下を示します:
- GoogleOAuthClientとYouTubeClientの連携
- ライブアーカイブの一覧取得
- YouTubeVideoInfoデータクラスの使用

実行方法:
    export GOOGLE_CLIENT_ID="your-client-id"
    export GOOGLE_REFRESH_TOKEN="your-refresh-token"
    export YOUTUBE_CHANNEL_ID="channel-id"
    uv run python examples/example_youtube.py

前提条件:
    - Google Cloud プロジェクトでYouTube Data API v3を有効化
    - OAuth 2.0 クライアント ID（デスクトップアプリ）
    - YouTube読み取りスコープのリフレッシュトークン

リフレッシュトークンの取得方法:
    from mizu_common import GoogleOAuthClient, GoogleScope

    refresh_token = GoogleOAuthClient.authenticate(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        scopes=[GoogleScope.YOUTUBE_READONLY],
    )
"""

import os
import sys

from mizu_common import (
    GoogleOAuthClient,
    GoogleScope,
    YouTubeClient,
    YouTubeHttpError,
    YouTubeNetworkError,
)


def main() -> None:
    """YouTube APIのデモを実行する."""
    # 環境変数から認証情報を取得
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    channel_id = os.environ.get("YOUTUBE_CHANNEL_ID")

    if not all([client_id, refresh_token, channel_id]):
        print("エラー: 以下の環境変数を設定してください:")
        print("  GOOGLE_CLIENT_ID")
        print("  GOOGLE_REFRESH_TOKEN")
        print("  YOUTUBE_CHANNEL_ID")
        sys.exit(1)

    # 型チェッカー用のアサーション
    assert client_id is not None
    assert refresh_token is not None
    assert channel_id is not None

    # OAuth クライアントを初期化
    oauth_client = GoogleOAuthClient(
        oauth_client_id=client_id,
        refresh_token=refresh_token,
        scopes=[GoogleScope.YOUTUBE_READONLY],
    )

    # YouTube クライアントを初期化
    youtube = YouTubeClient(oauth_client)

    try:
        # ライブアーカイブを取得（イテレータを使用）
        print(f"チャンネル {channel_id} のライブアーカイブを取得中...\n")

        count = 0
        for video in youtube.iter_live_archives(channel_id):
            count += 1
            print(f"[{video.video_id}] {video.title}")
            dt_str = video.published_at.strftime("%Y-%m-%d %H:%M:%S %Z")
            print(f"    公開日時: {dt_str}")
            print(f"    長さ: {video.duration}")
            print()

            # デモ用に最初の5件のみ表示
            if count >= 5:
                print("... （最初の5件のみ表示）")
                break

        if count == 0:
            print("ライブアーカイブが見つかりませんでした")

    except YouTubeHttpError as e:
        print(f"HTTP エラーが発生しました (status={e.status_code}): {e}")
        sys.exit(1)
    except YouTubeNetworkError as e:
        print(f"ネットワークエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
