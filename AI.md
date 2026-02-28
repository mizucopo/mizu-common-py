# mizu-common-py AI向けリファレンス

mizu-common-py は個人/私設プロジェクトで再利用することを目的としたPython共通ライブラリです。
本ドキュメントは、最小のコンテキストでライブラリを正しく使用するための技術リファレンスを提供します。

---

## インストール (uv)

`pyproject.toml` に追加:

```toml
[tool.uv.sources]
mizu-common = { git = "https://github.com/mizu-mizu/mizu-common-py.git", tag = "2.0.0" }
```

```bash
uv add mizu-common
```

---

## 公開API (stable)

### BackupManager

ディレクトリをzipアーカイブにバックアップします。

```python
from mizu_common import BackupManager

manager = BackupManager(src_dirpath="/path/to/source")
manager.backup(destination_path="/path/to/backup.zip")  # backup.zipを作成
```

- `__init__(src_dirpath: str)` - バックアップ対象のソースディレクトリパス
- `backup(destination_path: str) -> None` - zipアーカイブを作成（.zip拡張子を含む）

---

### LoggingConfigurator

アプリケーション全体のログ設定を行います。

```python
import logging
from mizu_common import LoggingConfigurator

LoggingConfigurator(level=logging.DEBUG)  # アプリ起動時に一度だけ初期化
logger = LoggingConfigurator.get_logger(__name__)
```

- `__init__(level: int = logging.INFO, stream: TextIO | None = None, *, force: bool = False)` - ログ設定を初期化
  - `force=True` で再初期化
- `reset() -> None` (クラスメソッド) - 初期化状態をリセット
- `get_logger(name: str) -> logging.Logger` (静的メソッド) - 設定済みロガーを取得

**注意**: シングルトンパターン。`force=True` なしの2回目以降の呼び出しは無視されます。

---

### LockManager

二重起動防止のためのファイルベースのロック機能を提供します。

```python
from pathlib import Path
from mizu_common import LockManager, AlreadyRunningError, StaleLockError

lock = LockManager(lock_dir=Path("/tmp"), lock_filename="app.lock", stale_hours=3)

try:
    with lock.acquire():
        # クリティカルセクション - 1つのインスタンスのみ実行可能
        pass
except AlreadyRunningError as e:
    print(f"他のインスタンスが実行中: {e.lock_path}")
except StaleLockError as e:
    print(f"古いロックファイルを検出: {e}")
```

- `__init__(lock_dir: Path, lock_filename: str = ".app.lock", stale_hours: int = 3)`
- `acquire() -> Iterator[None]` (コンテキストマネージャ) - 排他ロックを取得
  - 他のプロセスがロック中の場合 `AlreadyRunningError` を送出
  - ロックファイルが `stale_hours` 時間より古い場合 `StaleLockError` を送出
- `release() -> bool` - ロックファイルを削除（削除された場合Trueを返す）
- `is_locked() -> bool` - ロックファイルが存在するか確認
- `lock_path` (プロパティ) - ロックファイルのパス

**警告**: 必ず `acquire()` をコンテキストマネージャとして使用すること。手動での `release()` はロックのセマンティクスを回避します。

---

### GoogleOAuthClient

リフレッシュトークンを使用したOAuth 2.0認証を提供します。

```python
from mizu_common import GoogleOAuthClient, GoogleScope

client = GoogleOAuthClient(
    oauth_client_id="YOUR_CLIENT_ID",
    refresh_token="YOUR_REFRESH_TOKEN",
    scopes=[GoogleScope.YOUTUBE_READONLY],
)

access_token = client.get_access_token()
headers = client.get_headers()  # {"Authorization": "Bearer <token>"}
```

- `__init__(oauth_client_id: str, refresh_token: str, scopes: Sequence[str])`
- `get_access_token(force_refresh: bool = False) -> str` - アクセストークンを取得（キャッシュあり）
  - 失敗時 `RuntimeError` を送出
- `get_headers() -> dict[str, str]` - Authorizationヘッダーを含む辞書を返す
- `refresh_on_unauthorized(api_call: Callable[[], Any]) -> Any` - 401エラー時にトークンを更新してリトライ

**初期設定用ファクトリメソッド:**

```python
refresh_token = GoogleOAuthClient.authenticate(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    scopes=[GoogleScope.YOUTUBE_READONLY],
    output_handler=print,  # オプション
)
# 表示された指示に従ってデバイスフローを完了
```

- `authenticate(client_id, client_secret, scopes, output_handler=None) -> str | None` (クラスメソッド)
  - 成功時はリフレッシュトークン、失敗時はNoneを返す

---

### GoogleDriveProvider

OAuth認証を使用したGoogle Driveファイルアップロードを提供します。

```python
from mizu_common import GoogleDriveProvider

# ファクトリメソッドを使用
provider = GoogleDriveProvider.from_credentials(
    folder_id="GOOGLE_DRIVE_FOLDER_ID",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    refresh_token="YOUR_REFRESH_TOKEN",
)

provider.upload(source_path="/local/file.zip", destination_filename="backup.zip")
```

- `__init__(folder_id: str, credentials: Credentials, drive_service: Any | None = None)`
- `from_credentials(folder_id, client_id, client_secret, refresh_token) -> GoogleDriveProvider` (クラスメソッド)
- `upload(source_path: str, destination_filename: str) -> None` - ファイルをアップロード
  - 同名ファイルが存在する場合は更新、存在しない場合は新規作成
  - 失敗時 `RuntimeError` を送出
  - チャンクアップロードとリトライを実装（100MBチャンク、5回リトライ）

**必要なスコープ**: `GoogleScope.DRIVE_FILE`

---

### YouTubeClient

ライブアーカイブ向けのYouTube Data API v3クライアントです。

```python
from mizu_common import YouTubeClient, GoogleOAuthClient, GoogleScope

oauth = GoogleOAuthClient(
    oauth_client_id="YOUR_CLIENT_ID",
    refresh_token="YOUR_REFRESH_TOKEN",
    scopes=[GoogleScope.YOUTUBE_READONLY],
)
client = YouTubeClient(oauth)

# 全ライブアーカイブを取得（遅延イテレータ）
for video in client.iter_live_archives(channel_id="CHANNEL_ID"):
    print(f"{video.title} - {video.video_id}")

# またはリストとして取得
videos = client.get_live_archives(channel_id="CHANNEL_ID")
```

- `__init__(oauth_client: GoogleOAuthClient)`
- `iter_live_archives(channel_id: str) -> Iterator[YouTubeVideoInfo]` - 遅延イテレータ
  - ネットワークエラー時 `YouTubeNetworkError` を送出
  - HTTPエラー時 `YouTubeHttpError` を送出（`status_code` 属性付き）
- `get_live_archives(channel_id: str) -> list[YouTubeVideoInfo]` - 即時リスト取得
- `get_video_details(video_id: str) -> YouTubeVideoInfo | None` - 単一動画の取得

**必要なスコープ**: `GoogleScope.YOUTUBE_READONLY`

---

### YouTubeVideoInfo (frozen dataclass)

```python
@dataclass(frozen=True)
class YouTubeVideoInfo:
    video_id: str        # YouTube動画ID
    title: str           # 動画タイトル
    published_at: datetime  # ISO 8601形式の日時（タイムゾーン付き）
    duration: str        # ISO 8601形式の長さ（例: "PT1H30M"）
```

---

### GoogleScope (str, Enum)

```python
from mizu_common import GoogleScope

GoogleScope.YOUTUBE_READONLY  # "https://www.googleapis.com/auth/youtube.readonly"
GoogleScope.DRIVE_FILE        # "https://www.googleapis.com/auth/drive.file"
```

---

### 例外クラス

| 例外 | 送出タイミング | 属性 |
|------|---------------|------|
| `YouTubeApiError` | YouTubeエラーの基底例外 | - |
| `YouTubeHttpError` | YouTube APIからのHTTP 4xx/5xx | `status_code: int` |
| `YouTubeNetworkError` | ネットワーク/タイムアウトエラー | - |
| `StaleLockError` | ロックファイルが `stale_hours` 時間より古い | - |
| `AlreadyRunningError` | 他のプロセスがロックを保持 | `lock_path: Path \| None` |
| `DiscordWebhookError` | Discord Webhookへのリクエストが失敗 | - |

---

### DiscordClient

Discord Webhookを使用したメッセージ送信機能を提供します。

```python
from mizu_common import DiscordClient, DiscordEmbed

client = DiscordClient(webhook_url="https://discord.com/api/webhooks/...")

# テキストメッセージを送信
client.send_message("処理が完了しました")

# Embedメッセージを送信
embed = DiscordEmbed(
    title="バックアップ完了",
    description="データのバックアップが正常に完了しました",
    color=0x00FF00,  # 緑色
)
client.send_embed(embed)
```

- `__init__(webhook_url: str)` - Webhook URLでクライアントを初期化
- `send_message(content, username=None, avatar_url=None) -> None` - テキストメッセージを送信
  - 失敗時 `DiscordWebhookError` を送出
- `send_embed(embed, username=None, avatar_url=None) -> None` - Embedメッセージを送信
  - 失敗時 `DiscordWebhookError` を送出
- `send_embeds(embeds, username=None, avatar_url=None) -> None` - 複数のEmbedを送信
  - Embed数が10を超える場合 `ValueError` を送出
  - 失敗時 `DiscordWebhookError` を送出

---

### DiscordEmbed (dataclass)

```python
from mizu_common import DiscordEmbed

embed = DiscordEmbed(
    title="タイトル",           # 必須
    description="説明文",       # オプション
    color=0x00FF00,            # オプション: 色（10進数）
    url="https://example.com", # オプション: タイトルのリンク先
)
```

---

## よく使うレシピ

### 1. バックアップとGoogle Driveアップロード

```python
import logging
from datetime import datetime
from pathlib import Path
from mizu_common import (
    BackupManager,
    GoogleDriveProvider,
    LoggingConfigurator,
)

LoggingConfigurator(level=logging.INFO)
logger = LoggingConfigurator.get_logger(__name__)

# バックアップを作成
backup = BackupManager(src_dirpath="/data/project")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"/tmp/backup_{timestamp}.zip"
backup.backup(backup_path)

# Google Driveにアップロード
drive = GoogleDriveProvider.from_credentials(
    folder_id="DRIVE_FOLDER_ID",
    client_id="CLIENT_ID",
    client_secret="CLIENT_SECRET",
    refresh_token="REFRESH_TOKEN",
)
drive.upload(backup_path, f"backup_{timestamp}.zip")
logger.info("バックアップをアップロードしました")
```

### 2. 二重起動防止付きバッチ処理

```python
import sys
from pathlib import Path
from mizu_common import LockManager, LoggingConfigurator, AlreadyRunningError

LoggingConfigurator()
lock = LockManager(lock_dir=Path("/tmp/myapp"), stale_hours=1)

try:
    with lock.acquire():
        # バッチ処理ロジックをここに記述
        print("処理中...")
except AlreadyRunningError:
    sys.exit("他のインスタンスが既に実行中です")
```

### 3. YouTubeライブアーカイブの取得

```python
from mizu_common import YouTubeClient, GoogleOAuthClient, GoogleScope

oauth = GoogleOAuthClient(
    oauth_client_id="CLIENT_ID",
    refresh_token="REFRESH_TOKEN",
    scopes=[GoogleScope.YOUTUBE_READONLY],
)
client = YouTubeClient(oauth)

for video in client.iter_live_archives("CHANNEL_ID"):
    print(f"[{video.video_id}] {video.title}")
    print(f"  公開日時: {video.published_at}")
    print(f"  長さ: {video.duration}")
```

### 4. OAuth Device Flowでリフレッシュトークンを取得

```python
from mizu_common import GoogleOAuthClient, GoogleScope

refresh_token = GoogleOAuthClient.authenticate(
    client_id="CLIENT_ID",
    client_secret="CLIENT_SECRET",
    scopes=[GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE],
)

if refresh_token:
    print(f"リフレッシュトークン: {refresh_token}")
    # 安全な場所に保存
else:
    print("認証に失敗しました")
```

### 5. カスタムログ設定

```python
import logging
import sys
from mizu_common import LoggingConfigurator

# DEBUGレベルとカスタムストリームで初期化
LoggingConfigurator(
    level=logging.DEBUG,
    stream=sys.stdout,
    force=True,  # 必要に応じて再初期化
)

logger = LoggingConfigurator.get_logger("myapp")
logger.debug("デバッグメッセージ")
logger.info("情報メッセージ")
```

### 6. Discord通知

```python
from mizu_common import DiscordClient, DiscordEmbed

client = DiscordClient(webhook_url="https://discord.com/api/webhooks/...")

# テキストメッセージ
client.send_message("処理が完了しました", username="通知ボット")

# Embedメッセージ
embed = DiscordEmbed(
    title="バックアップ完了",
    description="データのバックアップが正常に完了しました",
    color=0x00FF00,
)
client.send_embed(embed)
```

---

## アンチパターン / 落とし穴

### LockManager: コンテキストマネージャ外でのrelease()使用

```python
# 誤り: ロックのセマンティクスを回避
lock = LockManager(...)
lock.release()  # ロックを取得していない！

# 正しい: コンテキストマネージャを使用
with lock.acquire():
    pass
```

### LoggingConfigurator: forceなしでの複数回初期化

```python
# 最初の呼び出しで初期化
LoggingConfigurator(level=logging.INFO)

# これは無視される（シングルトンパターン）
LoggingConfigurator(level=logging.DEBUG)  # レベルはINFOのまま

# 再初期化するにはforce=Trueを使用
LoggingConfigurator(level=logging.DEBUG, force=True)
```

### iter_live_archives: 遅延例外の伝播

```python
# 例外は呼び出し時ではなく、イテレーション中に送出される可能性がある
for video in client.iter_live_archives(channel_id):
    # 2ページ目以降の取得に失敗した場合、
    # ここでYouTubeHttpError/YouTubeNetworkErrorが送出される
    pass
```

### GoogleScope: 文字列を直接指定しない

```python
# 誤り: タイポの原因
scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

# 正しい: Enumを使用
from mizu_common import GoogleScope
scopes = [GoogleScope.YOUTUBE_READONLY]
```

---

## テストとデバッグ

### インポートの確認

```bash
uv run python -c "from mizu_common import *; print('All imports successful!')"
```

### テスト実行

```bash
uv run task test
```

### 型チェック

```bash
uv run mypy examples/
```

### サンプルの実行（認証不要）

```bash
uv run python examples/example_logging.py
uv run python examples/example_backup.py
uv run python examples/example_lock.py
```

### サンプルの実行（環境変数が必要）

```bash
# Discord通知
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
uv run python examples/example_discord.py
```
