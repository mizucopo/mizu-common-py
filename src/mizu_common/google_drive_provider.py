"""Google Drive アップロードプロバイダモジュール。"""

import logging
import re
import threading
from typing import Any

from google.oauth2 import credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from mizu_common.constants.google_scope import GoogleScope

logger = logging.getLogger(__name__)


class GoogleDriveProvider:
    """OAuth 2.0 トークンを使用した Google Drive アップロードプロバイダ。

    同名ファイルが存在する場合は更新、存在しない場合は新規作成する。
    """

    CHUNK_SIZE = 100 * 1024 * 1024
    MAX_RETRIES = 5
    SCOPES = [GoogleScope.DRIVE_FILE]

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Google Drive で使用できない文字を置換する。

        パス区切り（/）は除外し、ファイル名・フォルダ名として使用できない文字のみ置換する。

        Args:
            name: 元の名前

        Returns:
            サニタイズされた名前
        """
        # 禁止文字: \ : * ? " < > | と制御文字（/ はパス区切りとして使用するため除外）
        sanitized = re.sub(r'[\\:*?"<>|\r\n\t]', "_", name)
        # 先頭・末尾のドットとスペースを削除
        sanitized = sanitized.strip(". ")
        return sanitized if sanitized else "untitled"

    def __init__(
        self,
        folder_id: str,
        credentials: credentials.Credentials,
        drive_service: Any | None = None,
    ) -> None:
        """Google Drive アップロードプロバイダを初期化する。

        Args:
            folder_id: Google Drive フォルダ ID
            credentials: OAuth 2.0 認証情報
            drive_service: Google Drive API サービス（テスト用）
        """
        self.folder_id = folder_id
        self.creds = credentials
        self.service = drive_service or build("drive", "v3", credentials=credentials)
        self._lock = threading.Lock()

    @classmethod
    def from_credentials(
        cls,
        folder_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> "GoogleDriveProvider":
        """認証情報から GoogleDriveProvider を作成（ファクトリメソッド）。

        Args:
            folder_id: Google Drive フォルダ ID
            client_id: OAuth クライアント ID
            client_secret: OAuth クライアントシークレット
            refresh_token: OAuth リフレッシュトークン

        Returns:
            GoogleDriveProvider インスタンス
        """
        creds = credentials.Credentials(
            token=None,  # 初回使用時に更新される
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=cls.SCOPES,
        )  # type: ignore[no-untyped-call]

        return cls(folder_id=folder_id, credentials=creds)

    def upload(self, source_path: str, destination_filename: str) -> None:
        """Google Drive にファイルをアップロードする。

        同名ファイルが存在する場合は上書き、存在しない場合は新規作成する。
        MediaFileUpload によるチャンキングと next_chunk によるリトライを実装。

        Args:
            source_path: ローカルファイルパス
            destination_filename: Google Drive 上のファイル名

        Raises:
            RuntimeError: アップロード失敗時
        """
        with self._lock:
            logger.info(
                f"Uploading {source_path} to Google Drive folder {self.folder_id} "
                f"as {destination_filename}..."
            )

            existing_file_id = self._search_for_file(destination_filename)

            if existing_file_id:
                self._update_file(existing_file_id, source_path)
            else:
                self._create_file(source_path, destination_filename)

    def _create_file(self, source_path: str, destination_filename: str) -> None:
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
        path_parts = destination_filename.split("/")
        actual_filename = self.sanitize_name(path_parts[-1])
        folder_parts = path_parts[:-1]

        # 親フォルダIDの決定
        if folder_parts:
            parent_folder_id = self._ensure_folder_path(folder_parts)
        else:
            parent_folder_id = self.folder_id

        media = MediaFileUpload(source_path, resumable=True, chunksize=self.CHUNK_SIZE)
        file_metadata = {"name": actual_filename, "parents": [parent_folder_id]}

        request = self.service.files().create(
            body=file_metadata,  # type: ignore[arg-type]
            media_body=media,
            fields="id",
        )

        self._execute_upload(request, source_path)

    def _update_file(self, file_id: str, source_path: str) -> None:
        """既存ファイルを更新する。

        Args:
            file_id: 更新するファイルの ID
            source_path: ローカルファイルパス

        Raises:
            RuntimeError: アップロード失敗時
        """
        logger.info(f"Updating existing file (ID: {file_id})")

        # MediaFileUpload の作成（チャンキング有効）
        media = MediaFileUpload(source_path, resumable=True, chunksize=self.CHUNK_SIZE)

        # files().update() リクエストの構築
        request = self.service.files().update(
            fileId=file_id, media_body=media, fields="id"
        )

        # チャンク単位のアップロード実行（リトライ付き）
        self._execute_upload(request, source_path)

    def _execute_upload(self, request: Any, source_path: str) -> None:
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
                status, response = request.next_chunk(num_retries=self.MAX_RETRIES)

            file_id = str(response.get("id"))
            logger.info(f"Upload complete. File ID: {file_id}")

        except Exception as e:
            logger.error(
                f"Google Drive upload failed for {source_path}. "
                f"Last status: {status}, Last response: {response}. "
                f"Error details: {str(e)}"
            )
            raise

    def _search_for_file(self, filename: str) -> str | None:
        """Google Drive フォルダ内で同名ファイルを検索する。

        Args:
            filename: 検索するファイル名（パス区切り含む場合は適切なフォルダ内で検索）

        Returns:
            ファイル ID（存在する場合）、None（存在しない場合）

        Raises:
            Exception: 検索 API 呼び出し失敗時（元の例外がそのまま伝播）
        """
        # パス解析
        path_parts = filename.split("/")
        actual_filename = self.sanitize_name(path_parts[-1])
        folder_parts = path_parts[:-1]

        # 親フォルダIDの決定
        if folder_parts:
            parent_id = self._find_folder_path(folder_parts)
            if parent_id is None:
                # フォルダが存在しない = ファイルも存在しない
                logger.debug(f"Folder path not found: {'/'.join(folder_parts)}")
                return None
        else:
            parent_id = self.folder_id

        # ファイル名をエスケープしてクエリインジェクションを防ぐ
        escaped_name = actual_filename.replace("\\", "\\\\").replace("'", "\\'")

        query = (
            f"name = '{escaped_name}' and '{parent_id}' in parents and trashed = false"
        )

        try:
            results = (
                self.service.files()
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

    def _find_folder(self, name: str, parent_id: str) -> str | None:
        """指定した親フォルダ内でフォルダを検索する。

        Args:
            name: 検索するフォルダ名
            parent_id: 親フォルダID

        Returns:
            フォルダID（存在する場合）、None（存在しない場合）
        """
        escaped_name = name.replace("\\", "\\\\").replace("'", "\\'")
        query = (
            f"name = '{escaped_name}' and "
            f"'{parent_id}' in parents and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )
        logger.debug(f"Searching for folder '{name}' in parent '{parent_id}'")
        results = (
            self.service.files()
            .list(q=query, spaces="drive", fields="files(id)")
            .execute()
        )
        files = results.get("files", [])
        if files:
            folder_id = str(files[0]["id"])
            logger.debug(f"Found folder '{name}' (ID: {folder_id})")
            return folder_id
        logger.debug(f"Folder '{name}' not found in parent '{parent_id}'")
        return None

    def _create_folder(self, name: str, parent_id: str) -> str:
        """フォルダを作成し、フォルダIDを返す。

        Args:
            name: 作成するフォルダ名
            parent_id: 親フォルダID

        Returns:
            作成されたフォルダのID
        """
        logger.info(f"Creating folder '{name}' in parent '{parent_id}'")
        file_metadata = {
            "name": name,
            "parents": [parent_id],
            "mimeType": "application/vnd.google-apps.folder",
        }
        result = (
            self.service.files()
            .create(
                body=file_metadata,  # type: ignore[arg-type]
                fields="id",
            )
            .execute()
        )
        folder_id = str(result.get("id"))
        logger.info(f"Created folder '{name}' (ID: {folder_id})")
        return folder_id

    def _ensure_folder_path(self, path_parts: list[str]) -> str:
        """フォルダパスを確保し、最終的なフォルダIDを返す。

        存在しないフォルダは新規作成する。

        Args:
            path_parts: フォルダ名のリスト（例: ["folder", "subfolder"]）

        Returns:
            最終的なフォルダID
        """
        logger.info(f"Ensuring folder path: {'/'.join(path_parts)}")
        current_parent_id = self.folder_id

        for folder_name in path_parts:
            sanitized_name = self.sanitize_name(folder_name)
            folder_id = self._find_folder(sanitized_name, current_parent_id)
            if folder_id is None:
                folder_id = self._create_folder(sanitized_name, current_parent_id)
            current_parent_id = folder_id

        logger.info(f"Folder path resolved to ID: {current_parent_id}")
        return current_parent_id

    def _find_folder_path(self, path_parts: list[str]) -> str | None:
        """フォルダパスを検索し、存在すれば最終フォルダIDを返す。

        Args:
            path_parts: フォルダ名のリスト

        Returns:
            最終フォルダID（存在する場合）、None（存在しない場合）
        """
        current_parent_id = self.folder_id

        for folder_name in path_parts:
            sanitized_name = self.sanitize_name(folder_name)
            folder_id = self._find_folder(sanitized_name, current_parent_id)
            if folder_id is None:
                return None
            current_parent_id = folder_id

        return current_parent_id
