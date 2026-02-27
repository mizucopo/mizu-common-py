# サンプルコード

このディレクトリには mizu_common の使用方法を示すサンプルコードが含まれています。

## サンプルの実行方法

### 認証不要

以下のサンプルはそのまま実行できます:

```bash
uv run python examples/example_logging.py
uv run python examples/example_backup.py
uv run python examples/example_lock.py
```

### 認証必要

以下のサンプルは Google OAuth 認証情報が必要です:

```bash
# 環境変数を設定
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REFRESH_TOKEN="your-refresh-token"

# サンプルを実行
uv run python examples/example_youtube.py
uv run python examples/example_google_drive.py
```

## サンプルの説明

| ファイル | 説明 | 認証 |
|---------|------|------|
| `example_logging.py` | LoggingConfigurator の使用例 | 不要 |
| `example_backup.py` | tempfile を使用した BackupManager の例 | 不要 |
| `example_lock.py` | 二重起動防止のための LockManager の例 | 不要 |
| `example_youtube.py` | ライブアーカイブ取得の YouTubeClient の例 | 必要 |
| `example_google_drive.py` | ファイルアップロードの GoogleDriveProvider の例 | 必要 |

## OAuth 認証情報の取得方法

1. Google Cloud プロジェクトを作成し、API（YouTube Data API v3、Google Drive API）を有効化
2. OAuth 同意画面を設定
3. OAuth クライアント ID（デスクトップアプリ）を作成
4. `GoogleOAuthClient.authenticate()` を使用してリフレッシュトークンを取得:

```python
from mizu_common import GoogleOAuthClient, GoogleScope

refresh_token = GoogleOAuthClient.authenticate(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    scopes=[GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE],
)
print(f"リフレッシュトークン: {refresh_token}")
```
