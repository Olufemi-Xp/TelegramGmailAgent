import pytest
from app.database.repositories.job_repo import JobRepository, generate_job_fingerprint


def test_job_fingerprint_deterministic():
    fp1 = generate_job_fingerprint(
        url="https://jobs.example.com/roles/ai-eng?ref=google",
        title="Senior AI Engineer",
        employer="Acme Corp",
    )
    # Different query param, casing, whitespace
    fp2 = generate_job_fingerprint(
        url="https://jobs.example.com/roles/ai-eng/",
        title="senior ai engineer ",
        employer="acme corp",
    )
    assert fp1 == fp2


@pytest.mark.asyncio
async def test_job_deduplication_lifecycle(db_session):
    repo = JobRepository(db_session)
    user_id = 123456789

    # 1. Save new job
    job1 = await repo.save_job(
        user_id=user_id,
        title="Full Stack AI Engineer",
        source_link="https://jobs.example.com/1",
        source_domain="example.com",
        employer="TechCorp",
        work_arrangement="remote",
    )
    assert job1 is not None

    # 2. Try saving identical job - should return None (deduplicated)
    dup = await repo.save_job(
        user_id=user_id,
        title="full stack ai engineer",
        source_link="https://jobs.example.com/1",
        source_domain="example.com",
        employer="TechCorp",
    )
    assert dup is None

    # 3. List jobs
    jobs = await repo.list_jobs(user_id=user_id, arrangement="remote")
    assert len(jobs) == 1
    assert jobs[0].title == "Full Stack AI Engineer"
