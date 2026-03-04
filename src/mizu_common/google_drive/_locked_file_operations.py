"""Google Drive ファイル操作の内部モジュール。"""

import logging
from typing import TYPE_CHECKING, Any

from googleapiclient.http import MediaFileUpload

if TYPE_CHECKING:
    from mizu_common.google_drive.provider import GoogleDriveProvider

logger = logging.getLogger(__name__)


class _LockedFileOperations:
    """ロック内でのみ実行可能なファイル操作を提供する内部クラス。

    このクラスのインスタンスは upload() 内でのみ作成され、
    ロックの外側からはアクセスできない設計。
    """

    def __init__(self, provider: "GoogleDriveProvider") -> None:
        """ファイル操作インスタンスを初期化する。

        Args:
            provider: 親となる GoogleDriveProvider インスタンス
        """
        self._provider = provider

    def _parse_path(self, filepath: str) -> tuple[str, list[str]]:
        """ファイルパスを解析してファイル名とフォルダパーツに分割する。

        Args:
            filepath: ファイルパス（パス区切り含む場合あり）

        Returns:
            (ファイル名, フォルダパーツのリスト) のタプル
        """
        path_parts = filepath.split("/")
        actual_filename = self._provider.sanitize_name(path_parts[-1])
        folder_parts = path_parts[:-1]
        return actual_filename, folder_parts

    def search_for_file(self, filename: str) -> str | None:
        """Google Drive フォルダ内で同名ファイルを検索する。

        Args:
            filename: 検索するファイル名（パス区切り含む場合は適切なフォルダ内で検索）

        Returns:
            ファイル ID（存在する場合）、None（存在しない場合）

        Raises:
            Exception: 検索 API 呼び出し失敗時（元の例外がそのまま伝播）
        """
        # パス解析
        actual_filename, folder_parts = self._parse_path(filename)

        # 親フォルダIDの決定
        if folder_parts:
            parent_id = self._provider._find_folder_path(folder_parts)
            if parent_id is None:
                # フォルダが存在しない = ファイルも存在しない
                logger.debug(f"Folder path not found: {'/'.join(folder_parts)}")
                return None
        else:
            parent_id = self._provider.folder_id

        # ファイル名をエスケープしてクエリインジェクションを防ぐ
        escaped_name = actual_filename.replace("\\", "\\\\").replace("'", "\\'")

        query = (
            f"name = '{escaped_name}' and '{parent_id}' in parents and trashed = false"
        )

        try:
            results = (
                self._provider.service.files()
                .list(q=query, spaces="drive", fields="files(id, name)")
                .execute()
            )
            files = results.get("files", [])

            if not files:
                logger.debug(f"No existing file found with name: {filename}")
                return None

            if len(files) > 1:
                logger.warning(
                    f"Found {len(files)} files with name '{filename}', "
                    f"updating the first one (ID: {files[0]['id']})"
                )

            file_id = str(files[0]["id"])
            logger.info(f"Found existing file: {filename} (ID: {file_id})")
            return file_id

        except Exception as e:
            logger.error(f"Failed to search for existing file '{filename}': {str(e)}")
            raise

    def create_file(self, source_path: str, destination_filename: str) -> None:
        """新規ファイルを作成してアップロードする。

        Args:
            source_path: ローカルファイルパス
            destination_filename: Google Drive 上のファイル名
                （パス区切り含む場合は適切なフォルダを作成）

        Raises:
            RuntimeError: アップロード失敗時
        """
        logger.info(f"Creating new file: {destination_filename}")

        # パス解析
        actual_filename, folder_parts = self._parse_path(destination_filename)

        # 親フォルダIDの決定
        if folder_parts:
            parent_folder_id = self._provider._ensure_folder_path(folder_parts)
        else:
            parent_folder_id = self._provider.folder_id

        media = MediaFileUpload(
            source_path, resumable=True, chunksize=self._provider.CHUNK_SIZE
        )
        file_metadata = {"name": actual_filename, "parents": [parent_folder_id]}

        request = self._provider.service.files().create(
            body=file_metadata,  # type: ignore[arg-type]
            media_body=media,
            fields="id",
        )

        self.execute_upload(request, source_path)

    def update_file(self, file_id: str, source_path: str) -> None:
        """既存ファイルを更新する。

        Args:
            file_id: 更新するファイルの ID
            source_path: ローカルファイルパス

        Raises:
            RuntimeError: アップロード失敗時
        """
        logger.info(f"Updating existing file (ID: {file_id})")

        # MediaFileUpload の作成（チャンキング有効）
        media = MediaFileUpload(
            source_path, resumable=True, chunksize=self._provider.CHUNK_SIZE
        )

        # files().update() リクエストの構築
        request = self._provider.service.files().update(
            fileId=file_id, media_body=media, fields="id"
        )

        # チャンク単位のアップロード実行（リトライ付き）
        self.execute_upload(request, source_path)

    def execute_upload(self, request: Any, source_path: str) -> None:
        """チャンク単位でアップロードを実行する。

        Args:
            request: Google Drive API リクエストオブジェクト
            source_path: アップロードするファイルパス

        Raises:
            Exception: アップロード失敗時（元の例外がそのまま伝播）
        """
        response = None
        status = None

        try:
            while response is None:
                status, response = request.next_chunk(
                    num_retries=self._provider.MAX_RETRIES
                )

            file_id = str(response.get("id"))
            logger.info(f"Upload complete. File ID: {file_id}")

        except Exception as e:
            logger.error(
                f"Google Drive upload failed for {source_path}. "
                f"Last status: {status}, Last response: {response}. "
                f"Error details: {str(e)}"
            )
            raise
