import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import OAuthCredential, utc_now
from app.security.encryption import encryptor
from app.logging_config import get_logger

logger = get_logger(__name__)


class OAuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_credentials(
        self,
        user_id: int,
        access_token: str,
        refresh_token: Optional[str],
        token_expiry: Optional[datetime],
        scopes: str,
        provider: str = "google_gmail",
    ) -> OAuthCredential:
        encrypted_access = encryptor.encrypt(access_token)
        encrypted_refresh = encryptor.encrypt(refresh_token) if refresh_token else None

        stmt = select(OAuthCredential).where(
            OAuthCredential.user_id == user_id,
            OAuthCredential.provider == provider,
        )
        res = await self.session.execute(stmt)
        cred = res.scalars().first()

        if cred:
            cred.encrypted_access_token = encrypted_access
            if encrypted_refresh:
                cred.encrypted_refresh_token = encrypted_refresh
            cred.token_expiry = token_expiry
            cred.scopes = scopes
            cred.updated_at = utc_now()
        else:
            cred = OAuthCredential(
                id=str(uuid.uuid4()),
                user_id=user_id,
                provider=provider,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                token_expiry=token_expiry,
                scopes=scopes,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            self.session.add(cred)

        await self.session.flush()
        logger.info(f"Stored encrypted OAuth credentials for user {user_id} [{provider}]")
        return cred

    async def get_credentials(self, user_id: int, provider: str = "google_gmail") -> Optional[dict]:
        stmt = select(OAuthCredential).where(
            OAuthCredential.user_id == user_id,
            OAuthCredential.provider == provider,
        )
        res = await self.session.execute(stmt)
        cred = res.scalars().first()
        if not cred:
            return None

        access_token = encryptor.decrypt(cred.encrypted_access_token) if cred.encrypted_access_token else ""
        refresh_token = encryptor.decrypt(cred.encrypted_refresh_token) if cred.encrypted_refresh_token else ""

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": cred.token_expiry,
            "scopes": cred.scopes,
        }

    async def delete_credentials(self, user_id: int, provider: str = "google_gmail") -> bool:
        stmt = delete(OAuthCredential).where(
            OAuthCredential.user_id == user_id,
            OAuthCredential.provider == provider,
        )
        res = await self.session.execute(stmt)
        return res.rowcount > 0
