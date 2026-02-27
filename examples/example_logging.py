"""LoggingConfiguratorの使用例.

この例は以下を示します:
- LoggingConfiguratorの初期化
- ロガーの取得と使用
- force=Trueによる再初期化

実行方法:
    uv run python examples/example_logging.py

前提条件:
    なし（認証不要）
"""

import logging

from mizu_common import LoggingConfigurator


def main() -> None:
    """ログ設定のデモを実行する."""
    # 1. 基本的な初期化（INFOレベル）
    LoggingConfigurator()
    logger = LoggingConfigurator.get_logger("myapp")

    logger.debug("これは表示されません（INFOレベルのため）")
    logger.info("アプリケーションを開始します")
    logger.warning("警告メッセージの例")
    logger.error("エラーメッセージの例")

    # 2. 再初期化なし（シングルトンパターン）
    print("\n--- 2回目の初期化（変更されない） ---")
    LoggingConfigurator(level=logging.DEBUG)  # レベルはINFOのまま
    logger.debug("やはり表示されません")

    # 3. force=Trueで強制再初期化
    print("\n--- force=Trueで再初期化 ---")
    LoggingConfigurator(level=logging.DEBUG, force=True)
    logger = LoggingConfigurator.get_logger("myapp")
    logger.debug("DEBUGレベルなので表示されます")
    logger.info("INFOレベルのメッセージ")

    # 4. リセット
    print("\n--- リセット後の再初期化 ---")
    LoggingConfigurator.reset()
    LoggingConfigurator(level=logging.WARNING)
    logger = LoggingConfigurator.get_logger("myapp")
    logger.debug("表示されません")
    logger.info("表示されません")
    logger.warning("WARNING以上のみ表示されます")


if __name__ == "__main__":
    main()
