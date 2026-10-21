import base64
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from app.config import settings
from app.database.repositories.oauth_repo import OAuthRepository
from app.database.session import get_db_session
from app.logging_config import get_logger

logger = get_logger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


class GmailService:
    @property
    def client_id(self) -> str:
        return settings.GOOGLE_CLIENT_ID

    @property
    def client_secret(self) -> str:
        return settings.GOOGLE_CLIENT_SECRET

    @property
    def redirect_uri(self) -> str:
        return settings.GOOGLE_REDIRECT_URI

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def generate_auth_url(self, user_id: int) -> str:
        """Generates Google OAuth 2.0 authorization URL with CSRF state bound to user_id."""
        if not self.is_configured():
            raise RuntimeError("Gmail integration is not configured. Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET.")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": str(user_id),
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def exchange_code_for_tokens(self, user_id: int, code: str) -> None:
        """Exchanges authorization code for access and refresh tokens, encrypting them in DB."""
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(token_url, data=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Token exchange failed ({resp.status_code}): {resp.text}")
            data = resp.json()

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        async with get_db_session() as session:
            repo = OAuthRepository(session)
            await repo.save_credentials(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=token_expiry,
                scopes=" ".join(GMAIL_SCOPES),
                provider="google_gmail",
            )
        logger.info(f"Successfully authenticated Gmail account for user {user_id}")

    async def _get_valid_access_token(self, user_id: int) -> str:
        """Retrieves and refreshes the user's access token if expired."""
        async with get_db_session() as session:
            repo = OAuthRepository(session)
            creds = await repo.get_credentials(user_id=user_id, provider="google_gmail")

        if not creds or not creds.get("access_token"):
            raise RuntimeError("Gmail is not connected. Use /gmail to connect your Google account.")

        token_expiry = creds.get("token_expiry")
        refresh_token = creds.get("refresh_token")
        now = datetime.now(timezone.utc)

        # Refresh if expired or expiring within 60s
        if token_expiry and token_expiry <= (now + timedelta(seconds=60)):
            if not refresh_token:
                raise RuntimeError("Gmail session expired and no refresh token is stored. Please re-authenticate.")

            logger.info(f"Refreshing expired Gmail token for user {user_id}...")
            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(token_url, data=payload)
                if resp.status_code != 200:
                    raise RuntimeError(f"Token refresh failed: {resp.text}")
                data = resp.json()

            new_access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            async with get_db_session() as session:
                repo = OAuthRepository(session)
                await repo.save_credentials(
                    user_id=user_id,
                    access_token=new_access_token,
                    refresh_token=refresh_token,
                    token_expiry=new_expiry,
                    scopes=creds.get("scopes", ""),
                    provider="google_gmail",
                )
            return new_access_token

        return creds["access_token"]

    async def search_messages(self, user_id: int, query: str = "is:unread", max_results: int = 5) -> List[Dict[str, Any]]:
        """Searches user's Gmail inbox and decodes messages safely."""
        token = await self._get_valid_access_token(user_id)
        headers = {"Authorization": f"Bearer {token}"}
        list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        params = {"q": query, "maxResults": min(max_results, 10)}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(list_url, headers=headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail list messages failed: {resp.text}")
            data = resp.json()
            message_stubs = data.get("messages", [])

            detailed_messages = []
            for stub in message_stubs:
                msg_id = stub["id"]
                msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full"
                msg_resp = await client.get(msg_url, headers=headers)
                if msg_resp.status_code == 200:
                    msg_data = msg_resp.json()
                    decoded = self._decode_message(msg_data)
                    detailed_messages.append(decoded)

        return detailed_messages

    def _decode_message(self, msg_data: Dict[str, Any]) -> Dict[str, Any]:
        """Safely extracts headers and body text from a raw Gmail API message dictionary."""
        payload = msg_data.get("payload", {})
        headers_list = payload.get("headers", [])
        headers = {h.get("name", "").lower(): h.get("value", "") for h in headers_list}

        body_text = ""
        parts = payload.get("parts")
        if parts:
            for part in parts:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body_text = base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")
                        break
        else:
            raw_body = payload.get("body", {}).get("data", "")
            if raw_body:
                body_text = base64.urlsafe_b64decode(raw_body.encode("ASCII")).decode("utf-8", errors="replace")

        # Wrap untrusted body content with safety markers
        untrusted_body = f"<<<UNTRUSTED_EMAIL_CONTENT>>>\n{body_text[:1500]}\n<<<END_UNTRUSTED_EMAIL_CONTENT>>>"

        return {
            "id": msg_data.get("id"),
            "threadId": msg_data.get("threadId"),
            "from": headers.get("from", "Unknown Sender"),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", "No Subject"),
            "date": headers.get("date", ""),
            "snippet": msg_data.get("snippet", ""),
            "body": untrusted_body,
        }

    async def create_draft(
        self,
        user_id: int,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates an email draft in the user's Gmail account. Note: NEVER sends the email."""
        token = await self._get_valid_access_token(user_id)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Construct MIME message
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw_encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ASCII")

        draft_payload: Dict[str, Any] = {"message": {"raw": raw_encoded}}
        if thread_id:
            draft_payload["message"]["threadId"] = thread_id

        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, json=draft_payload)
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Gmail create draft failed: {resp.text}")
            data = resp.json()

        logger.info(f"Created Gmail draft id={data.get('id')} to='{to}' subject='{subject}' for user={user_id}")
        return {
            "draft_id": data.get("id"),
            "to": to,
            "subject": subject,
            "thread_id": thread_id,
            "message": "Draft created successfully in Gmail.",
        }

    # CRITICAL SECURITY INVARIANT:
    # Sending emails directly is strictly disabled in this release as per requirement:
    # "Drafting is allowed; sending is not enabled in the initial release. Do not silently send, delete, archive, forward, or alter email."


gmail_service = GmailService()
