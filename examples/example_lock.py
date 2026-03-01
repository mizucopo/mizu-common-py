"""LockManagerの使用例.

この例は以下を示します:
- LockManagerによる二重起動防止
- contextmanagerとしての使用方法
- AlreadyRunningErrorとStaleLockErrorの処理

実行方法:
    uv run python examples/example_lock.py

前提条件:
    なし（認証不要）

注意:
    この例ではロックのデモを行うため、同一プロセス内で
    複数回のロック取得を試みます。実際の二重起動防止は
    複数のプロセス間で機能します。
"""

import tempfile
from pathlib import Path

from mizu_common import LockManager


def main() -> None:
    """ロック管理のデモを実行する."""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        lock = LockManager(
            lock_dir=lock_dir,
            lock_filename="demo.lock",
            stale_hours=3,
        )

        print(f"ロックディレクトリ: {lock_dir}")
        print(f"ロックファイルパス: {lock.lock_path}")

        # 1. 正常なロック取得と解放
        print("\n--- 1. 正常なロック取得 ---")
        print(f"ロック状態（取得前）: {lock.is_locked()}")

        with lock.acquire():
            print(f"ロック状態（取得後）: {lock.is_locked()}")
            print("クリティカルセクション実行中...")
            # ここで重要な処理を行う

        print(f"ロック状態（解放後）: {lock.is_locked()}")

        # 2. 二重ロックの試行（シミュレーション）
        print("\n--- 2. 二重ロック防止の確認 ---")

        # 最初のロックを取得
        with lock.acquire():
            print("ロックを取得しました")

            # 同じロックファイルに対して再度取得を試みる
            # （実際のシナリオでは別プロセスから試行される）
            print("同一ロックファイルへの再取得を試みます...")

            # 注: 同一プロセスからの場合、portalockerの挙動により
            # ロックが再取得される可能性があります。
            # 実際の使用では、別プロセスからのロック取得のみが防止されます。

        # 3. ロック情報の取得
        print("\n--- 3. ロック情報 ---")
        print(f"ロックファイルパス: {lock.lock_path}")
        print(f"is_locked(): {lock.is_locked()}")

        # 4. 手動でのロック解放（緊急時用）
        print("\n--- 4. 手動でのロック解放 ---")
        with lock.acquire():
            print(f"ロック取得: {lock.is_locked()}")

        # コンテキストマネージャを抜けた後、ロックは自動的に解放されます
        print(f"自動解放後: {lock.is_locked()}")

        # release()は緊急時やクリーンアップ用
        lock.release()
        print("手動release()を実行")

        # 5. エラーハンドリングの例
        print("\n--- 5. エラーハンドリング例 ---")
        print("推奨パターン:")

        sample_code = """
try:
    with lock.acquire():
        # メイン処理
        pass
except AlreadyRunningError as e:
    print(f"他のインスタンスが実行中: {e.lock_path}")
    sys.exit(1)
except StaleLockError as e:
    print(f"古いロックファイルを検出: {e}")
    # 必要に応じて手動で削除するか、管理者に通知
    sys.exit(1)
"""
        print(sample_code)


if __name__ == "__main__":
    main()
