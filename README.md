# mizu-common-py

Python用共通ライブラリ。

## 機能

- **Google Drive連携**: Google Drive APIを使用したファイル操作
- **ディレクトリバックアップ**: ディレクトリのバックアップ機能

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
