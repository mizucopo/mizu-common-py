# mizu-common-py

Python用共通ライブラリ。

## 機能

### Google連携

- **GoogleOAuthClient**: OAuth 2.0 Device Flowによる認証とアクセストークン管理
- **GoogleDriveProvider**: Google Driveへのファイルアップロード（新規作成/既存更新の自動判定）
- **YouTubeClient**: YouTube Data API v3を使用したチャンネル動画情報の取得

### ユーティリティ

- **BackupManager**: ディレクトリのzipアーカイブバックアップ
- **LockManager**: ファイルロックによる二重起動防止（stale lock検出対応）
- **LoggingConfigurator**: アプリケーション全体のログ設定管理
- **RetryConfig**: リトライ設定を表すデータクラス
- **AsyncRetryable**: 非同期関数のリトライ実行クラス

### Discord連携

- **DiscordClient**: Discord Webhookを使用したメッセージ・Embed送信（2000文字超は自動分割）

### 資産管理

- **AssetService**: ウォーターフィリングアルゴリズムによる資産配分調整

### データモデル

- **YouTubeVideoInfo**: YouTube動画情報を表すデータクラス
- **DiscordEmbed**: Discord Embedメッセージを構築するデータクラス
- **Asset**: 資産データを表すデータクラス
- **AssetCalculation**: 資産の計算結果を表すデータクラス
- **AssetAdjustmentResult**: 資産調整結果を表すデータクラス
- **RetryConfig**: リトライ設定を表すデータクラス（count, interval）

### 定数

- **GoogleScope**: Google API スコープのEnum
- **AssetAdjustmentType**: 資産調整操作の種別Enum

## 要件

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

## インストール

### pip

```bash
pip install git+https://github.com/mizucopo/mizu-common-py.git
```

### uv

```bash
uv add git+https://github.com/mizucopo/mizu-common-py.git
```

## 開発用セットアップ

```bash
# 依存関係のインストール
uv sync
```

## 開発コマンド

```bash
# テスト実行（lint + 型チェック + テスト）
uv run task test
```

## 使用例

### Google Driveへのアップロード

```python
from mizu_common import GoogleDriveProvider

provider = GoogleDriveProvider.from_credentials(
    folder_id="Google Drive folder ID",
    client_id="OAuth client ID",
    client_secret="OAuth client secret",
    refresh_token="OAuth refresh token",
)
provider.upload("backup.zip", "backups/backup.zip")
```

`GoogleDriveProvider` は、ファイルやフォルダの検索・作成と resumable upload
で一時障害が発生した場合、ランダム化指数バックオフを挟んで最大5回再試行します。
対象は HTTP 429、HTTP 500–599、timeout、接続の切断・中断・拒否、EPIPE、
SSL および名前解決の一時障害です。その他の4xxやローカルファイルのエラーは
再試行されません。

再試行ログには、試行回数、待機秒数、処理段階、対象ファイルまたはフォルダ、
HTTP status または例外種別が記録されます。resumable upload の通信が途切れた場合は、
同じアップロードセッションの状態を確認して再開します。

### 非同期リトライ

```python
from mizu_common.async_retryable import AsyncRetryable
from mizu_common.retry_config import RetryConfig

retry = AsyncRetryable(
    config=RetryConfig(count=2, interval=10.0),
    transient_exceptions=(ConnectionError, TimeoutError),
)
result = await retry.execute(lambda: fetch_data())
```

### Discordメッセージ送信

```python
from mizu_common import DiscordClient


async def main() -> None:
    async with DiscordClient(
        webhook_url="https://discord.com/api/webhooks/...",
    ) as client:
        await client.send_message(
            "2000文字を超える場合は自動的に分割送信されます"
        )
```

## ライセンス

[MIT](LICENSE)
