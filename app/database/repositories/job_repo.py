import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlparse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Job, utc_now
from app.logging_config import get_logger

logger = get_logger(__name__)


def generate_job_fingerprint(url: str, title: str, employer: Optional[str] = None) -> str:
    """Creates a deterministic SHA-256 fingerprint from normalized URL, title, and employer."""
    parsed = urlparse(url.lower().strip())
    # Normalize URL: strip trailing slash, query params, scheme
    norm_url = f"{parsed.netloc}{parsed.path}".rstrip("/")
    norm_title = "".join(ch for ch in title.lower() if ch.isalnum())
    norm_emp = "".join(ch for ch in (employer or "").lower() if ch.isalnum())
    raw = f"{norm_url}::{norm_title}::{norm_emp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_duplicate(self, fingerprint: str) -> bool:
        stmt = select(Job.id).where(Job.fingerprint == fingerprint).limit(1)
        res = await self.session.execute(stmt)
        return res.scalars().first() is not None

    async def save_job(
        self,
        user_id: int,
        title: str,
        source_link: str,
        source_domain: str,
        employer: Optional[str] = None,
        location: Optional[str] = None,
        work_arrangement: Optional[str] = "remote",
        compensation: Optional[str] = None,
        date_posted: Optional[str] = None,
        summary: Optional[str] = None,
        match_rationale: Optional[str] = None,
    ) -> Optional[Job]:
        fingerprint = generate_job_fingerprint(source_link, title, employer)
        if await self.is_duplicate(fingerprint):
            logger.debug(f"Skipping duplicate job: {title} ({source_link})")
            return None

        parsed = urlparse(source_link)
        normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        job = Job(
            id=str(uuid.uuid4()),
            user_id=user_id,
            normalized_url=normalized_url,
            source_domain=source_domain,
            title=title.strip(),
            employer=employer.strip() if employer else None,
            location=location.strip() if location else None,
            work_arrangement=work_arrangement,
            compensation=compensation,
            date_posted=date_posted,
            date_discovered=utc_now(),
            summary=summary,
            source_link=source_link,
            match_rationale=match_rationale,
            application_status="discovered",
            fingerprint=fingerprint,
        )
        self.session.add(job)
        await self.session.flush()
        logger.info(f"Recorded new opportunity: {title} at {employer or 'Unknown'} [{work_arrangement}]")
        return job

    async def list_jobs(
        self,
        user_id: int,
        days_back: int = 14,
        arrangement: Optional[str] = None,
        limit: int = 20,
    ) -> List[Job]:
        since = datetime.now(timezone.utc) - timedelta(days=days_back)
        stmt = (
            select(Job)
            .where(Job.user_id == user_id, Job.date_discovered >= since)
        )
        if arrangement and arrangement.lower() != "all":
            stmt = stmt.where(Job.work_arrangement.ilike(f"%{arrangement}%"))
        stmt = stmt.order_by(desc(Job.date_discovered)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
