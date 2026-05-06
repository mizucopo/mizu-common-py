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

### Discord連携

- **DiscordClient**: Discord Webhookを使用したメッセージ・Embed送信

### 資産管理

- **AssetService**: ウォーターフィリングアルゴリズムによる資産配分調整

### データモデル

- **YouTubeVideoInfo**: YouTube動画情報を表すデータクラス
- **DiscordEmbed**: Discord Embedメッセージを構築するデータクラス
- **Asset**: 資産データを表すデータクラス
- **AssetCalculation**: 資産の計算結果を表すデータクラス
- **AssetAdjustmentResult**: 資産調整結果を表すデータクラス

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

## ライセンス

[MIT](LICENSE)
