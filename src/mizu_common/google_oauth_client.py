"""Google OAuth認証クライアントモジュール.

Google APIへのアクセスに必要なアクセストークンの取得・管理を提供する。
"""

import logging
import time
from collections.abc import Callable, Sequence
from typing import Any

import requests

logger = logging.getLogger(__name__)


class GoogleOAuthClient:
    """Google OAuth認証クライアント.

    OAuth Client IDとRefresh Tokenを使用してアクセストークンを取得する。
    スコープは外部から注入され、使用するGoogle APIに応じて柔軟に設定可能。
    """

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"

    def __init__(
        self,
        oauth_client_id: str,
        oauth_client_secret: str,
        refresh_token: str,
        scopes: Sequence[str],
    ) -> None:
        """クライアントを初期化する.

        Args:
            oauth_client_id: Google OAuth Client ID
            oauth_client_secret: Google OAuth Client Secret
            refresh_token: OAuth Refresh Token
            scopes: 要求するGoogle APIスコープのリスト
        """
        self._oauth_client_id = oauth_client_id
        self._oauth_client_secret = oauth_client_secret
        self._refresh_token = refresh_token
        self._scopes = scopes
        self._access_token: str | None = None

    def get_access_token(self, force_refresh: bool = False) -> str:
        """アクセストークンを取得する.

        必要に応じてリフレッシュトークンを使用して新しいトークンを取得する。

        Args:
            force_refresh: Trueの場合、強制的にトークンを更新する

        Returns:
            アクセストークン

        Raises:
            RuntimeError: アクセストークンの取得に失敗した場合
        """
        if self._access_token is None or force_refresh:
            self._refresh_access_token()
        return self._access_token  # type: ignore[return-value]

    def get_headers(self) -> dict[str, str]:
        """Authorizationヘッダーを返す.

        Returns:
            Authorizationヘッダーを含む辞書
        """
        return {"Authorization": f"Bearer {self.get_access_token()}"}

    def _refresh_access_token(self) -> None:
        """リフレッシュトークンを使用してアクセストークンを更新する.

        Raises:
            RuntimeError: トークン更新に失敗した場合
        """
        response = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self._oauth_client_id,
                "client_secret": self._oauth_client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(f"アクセストークンの取得に失敗しました: {response.text}")

        data = response.json()
        self._access_token = data["access_token"]

    def refresh_on_unauthorized(self, api_call: Callable[[], Any]) -> Any:
        """トークン期限切れ時に自動リフレッシュしてAPI呼び出しを再試行する.

        Args:
            api_call: API呼び出し関数（get_headers()を使用してリクエストを行う）

        Returns:
            API呼び出しの結果

        Raises:
            Exception: リフレッシュ後も失敗した場合、または401以外のエラー
        """
        try:
            return api_call()
        except requests.exceptions.HTTPError as e:
            if self._is_unauthorized_error(e):
                self.get_access_token(force_refresh=True)
                return api_call()
            raise

    def _is_unauthorized_error(self, error: requests.exceptions.HTTPError) -> bool:
        """エラーが401 Unauthorizedかどうかを判定する."""
        return error.response is not None and error.response.status_code == 401

    @classmethod
    def authenticate(
        cls,
        client_id: str,
        client_secret: str,
        scopes: Sequence[str],
        output_handler: Callable[[str], None] | None = None,
    ) -> str | None:
        """OAuth 2.0 Device Flowを実行してリフレッシュトークンを取得する.

        Args:
            client_id: OAuth クライアント ID
            client_secret: OAuth クライアントシークレット
            scopes: 要求するGoogle APIスコープのリスト
            output_handler: 出力ハンドラー（デフォルト: print）

        Returns:
            リフレッシュトークン（成功時）、None（失敗時）
        """
        _output_handler = print if output_handler is None else output_handler

        device_code_data = cls._get_device_code(client_id, scopes)
        if not device_code_data:
            return None

        device_code = device_code_data["device_code"]
        user_code = device_code_data["user_code"]
        verification_url = device_code_data["verification_url"]
        interval = device_code_data.get("interval", 5)
        expires_in = device_code_data["expires_in"]

        _output_handler(f"\n1. Open your browser and go to: {verification_url}")
        _output_handler(f"2. Enter the following code: {user_code}")
        wait_msg = f"\nWaiting for authentication (expires in {expires_in} seconds)..."
        _output_handler(wait_msg)

        return cls._poll_for_token(
            device_code, client_id, client_secret, interval, expires_in
        )

    @classmethod
    def _get_device_code(
        cls,
        client_id: str,
        scopes: Sequence[str],
    ) -> dict[str, Any] | None:
        """Googleからデバイスコードを要求する.

        Args:
            client_id: OAuth クライアント ID
            scopes: 要求するスコープのリスト

        Returns:
            デバイスコードレスポンスデータ、失敗時は None
        """
        payload = {"client_id": client_id, "scope": " ".join(scopes)}
        try:
            response = requests.post(cls.DEVICE_CODE_URL, data=payload, timeout=30)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except Exception as e:
            logger.error(f"Failed to get device code: {e}")
            return None

    @classmethod
    def _poll_for_token(
        cls,
        device_code: str,
        client_id: str,
        client_secret: str,
        interval: int,
        expires_in: int,
    ) -> str | None:
        """トークンエンドポイントをポーリングする.

        Args:
            device_code: Googleのデバイスコード
            client_id: OAuth クライアント ID
            client_secret: OAuth クライアントシークレット
            interval: ポーリング間隔（秒）
            expires_in: 有効期限（秒）

        Returns:
            リフレッシュトークン（成功時）、None（失敗時）
        """
        start_time = time.time()
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        while time.time() - start_time < expires_in:
            try:
                response = requests.post(cls.TOKEN_URL, data=payload, timeout=30)
                data: dict[str, Any] = response.json()

                if response.status_code == 200:
                    refresh_token = data.get("refresh_token")
                    if refresh_token:
                        return str(refresh_token)
                    logger.error("No refresh token in successful response.")
                    return None

                error = data.get("error")
                if error == "slow_down":
                    interval += 5
                    logger.debug(f"Slow down requested, new interval: {interval}s")
                elif error == "access_denied":
                    logger.error("Authentication was denied by the user.")
                    return None
                elif error == "expired_token":
                    logger.error("The device code has expired.")
                    return None
                elif error == "authorization_pending":
                    # ユーザーがまだ承認していない、ポーリング継続
                    logger.debug(f"Polling status: {error}")
                elif error is not None:
                    # 未知のエラーは即失敗
                    logger.error(f"Authentication failed: {error}")
                    return None
            except Exception as e:
                logger.error(f"Polling failed: {e}")
                return None

            time.sleep(interval)

        logger.error("Authentication timed out.")
        return None
