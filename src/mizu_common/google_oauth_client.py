"""Google OAuth認証クライアントモジュール.

Google APIへのアクセスに必要なアクセストークンの取得・管理を提供する。
"""

from collections.abc import Sequence

import requests


class GoogleOAuthClient:
    """Google OAuth認証クライアント.

    OAuth Client IDとRefresh Tokenを使用してアクセストークンを取得する。
    スコープは外部から注入され、使用するGoogle APIに応じて柔軟に設定可能。
    """

    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(
        self, oauth_client_id: str, refresh_token: str, scopes: Sequence[str]
    ) -> None:
        """クライアントを初期化する.

        Args:
            oauth_client_id: Google OAuth Client ID
            refresh_token: OAuth Refresh Token
            scopes: 要求するGoogle APIスコープのリスト
        """
        self._oauth_client_id = oauth_client_id
        self._refresh_token = refresh_token
        self._scopes = scopes
        self._access_token: str | None = None

    def get_access_token(self) -> str:
        """アクセストークンを取得する.

        必要に応じてリフレッシュトークンを使用して新しいトークンを取得する。

        Returns:
            アクセストークン

        Raises:
            RuntimeError: アクセストークンの取得に失敗した場合
        """
        if self._access_token is None:
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
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(f"アクセストークンの取得に失敗しました: {response.text}")

        data = response.json()
        self._access_token = data["access_token"]
