from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from app.bot.formatting import split_message
from app.database.repositories.job_repo import JobRepository
from app.database.session import get_db_session
from app.services.job_service import job_service

router = Router(name="jobs")


@router.message(Command("jobs"))
async def handle_jobs_command(message: Message):
    query = message.text.partition(" ")[2].strip()
    if not query:
        query = "Python AI Engineer"

    status_msg = await message.answer(f"💼 _Searching for opportunities: '{query}'..._", parse_mode="Markdown")
    try:
        jobs = await job_service.find_opportunities(
            user_id=message.from_user.id,
            query=query,
            work_arrangement="remote",
        )

        if not jobs:
            # Check previously stored jobs in DB
            async with get_db_session() as session:
                repo = JobRepository(session)
                stored_jobs = await repo.list_jobs(user_id=message.from_user.id, limit=5)

            if stored_jobs:
                lines = [f"💼 *Saved Opportunities from History:*\n"]
                for j in stored_jobs:
                    lines.append(f"• *[{j.title}]({j.source_link})*")
                    if j.employer:
                        lines.append(f"  _Company: {j.employer} | {j.location}_")
                    if j.summary:
                        lines.append(f"  {j.summary[:200]}...\n")
                await status_msg.edit_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)
                return
            else:
                await status_msg.edit_text(f"No new job listings found matching *{query}*.", parse_mode="Markdown")
                return

        lines = [f"💼 *Discovered Opportunities ({len(jobs)}):*\n"]
        for j in jobs:
            lines.append(f"• *[{j['title']}]({j['url']})*")
            if j.get("employer"):
                lines.append(f"  _Company: {j['employer']} | {j.get('location')}_")
            if j.get("summary"):
                lines.append(f"  {j['summary'][:200]}...\n")

        lines.append("🔒 _Duplicates automatically filtered by persistent SHA-256 fingerprint._")
        full_text = "\n".join(lines)
        chunks = split_message(full_text)
        await status_msg.edit_text(chunks[0], parse_mode="Markdown", disable_web_page_preview=True)
        for c in chunks[1:]:
            await message.answer(c, parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as e:
        await status_msg.edit_text(f"❌ Error during job discovery: {str(e)}")


@router.callback_query(F.data == "action_jobs")
async def handle_jobs_callback(query: CallbackQuery):
    await query.message.answer(
        "💼 *Job & Gig Discovery*\n\nSend `/jobs <keywords>` or ask: _\"Find freelance Python opportunities\"_.",
        parse_mode="Markdown",
    )
    await query.answer()
