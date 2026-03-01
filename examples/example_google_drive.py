"""GoogleDriveProviderの使用例.

この例は以下を示します:
- GoogleDriveProviderのファクトリメソッドを使用した初期化
- Google Driveへのファイルアップロード
- tempfileを使用したテストファイルの作成

実行方法:
    export GOOGLE_CLIENT_ID="your-client-id"
    export GOOGLE_CLIENT_SECRET="your-client-secret"
    export GOOGLE_REFRESH_TOKEN="your-refresh-token"
    export GOOGLE_DRIVE_FOLDER_ID="folder-id"
    uv run python examples/example_google_drive.py

前提条件:
    - Google Cloud プロジェクトでGoogle Drive APIを有効化
    - OAuth 2.0 クライアント ID（デスクトップアプリ）
    - drive.file スコープのリフレッシュトークン
    - 書き込み先のGoogle DriveフォルダID

リフレッシュトークンの取得方法:
    from mizu_common import GoogleOAuthClient, GoogleScope

    refresh_token = GoogleOAuthClient.authenticate(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        scopes=[GoogleScope.DRIVE_FILE],
    )

フォルダIDの取得方法:
    Google Driveでフォルダを開き、URLの folders/ 以降の文字列がフォルダIDです
    例: https://drive.google.com/drive/folders/XXXXXXXXXXXXX
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from mizu_common import GoogleDriveProvider


def main() -> None:
    """Google Drive アップロードのデモを実行する."""
    # 環境変数から認証情報を取得
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

    if not all([client_id, client_secret, refresh_token, folder_id]):
        print("エラー: 以下の環境変数を設定してください:")
        print("  GOOGLE_CLIENT_ID")
        print("  GOOGLE_CLIENT_SECRET")
        print("  GOOGLE_REFRESH_TOKEN")
        print("  GOOGLE_DRIVE_FOLDER_ID")
        sys.exit(1)

    # 型チェッカー用のアサーション
    assert client_id is not None
    assert client_secret is not None
    assert refresh_token is not None
    assert folder_id is not None

    # GoogleDriveProviderを初期化（ファクトリメソッド使用）
    provider = GoogleDriveProvider.from_credentials(
        folder_id=folder_id,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
    )

    # テストファイルを作成
    with tempfile.TemporaryDirectory() as tmpdir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_file = Path(tmpdir) / f"test_upload_{timestamp}.txt"

        # テキストファイルを作成
        test_file.write_text(
            f"mizu-common-py Google Drive upload test\n"
            f"Timestamp: {timestamp}\n"
            f"This is a test file.\n"
        )

        print(f"テストファイルを作成: {test_file}")
        print(f"ファイルサイズ: {test_file.stat().st_size} bytes")

        # Google Driveにアップロード
        destination_filename = f"mizu_common_test_{timestamp}.txt"
        print("\nGoogle Driveにアップロード中...")
        print(f"  フォルダID: {folder_id}")
        print(f"  ファイル名: {destination_filename}")

        try:
            provider.upload(
                source_path=str(test_file),
                destination_filename=destination_filename,
            )
            print("\nアップロード完了!")

        except RuntimeError as e:
            print(f"\nアップロードエラー: {e}")
            sys.exit(1)

        # 同じファイル名で再度アップロード（更新のテスト）
        print("\n同じファイル名で更新アップロードを試みます...")

        # ファイルの内容を変更
        test_file.write_text(
            f"mizu-common-py Google Drive UPDATE test\n"
            f"Timestamp: {timestamp}\n"
            f"This file has been updated!\n"
        )

        try:
            provider.upload(
                source_path=str(test_file),
                destination_filename=destination_filename,
            )
            print("更新アップロード完了! (同名ファイルが更新されました)")

        except RuntimeError as e:
            print(f"更新エラー: {e}")
            sys.exit(1)

    # sanitize_name の使用例
    # Google Drive で使用できない文字を含むファイル名をサニタイズ
    raw_filename = "video:2024/01?.mp4"
    safe_filename = GoogleDriveProvider.sanitize_name(raw_filename)
    print("\nサニタイズの例:")
    print(f"  元のファイル名: {raw_filename}")
    print(f"  サニタイズ後: {safe_filename}")  # -> "video_2024/01_.mp4"


if __name__ == "__main__":
    main()
