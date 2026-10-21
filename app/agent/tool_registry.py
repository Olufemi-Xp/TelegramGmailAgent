import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError

from app.agent.schemas import (
    CancelReminderInput,
    CreateReminderInput,
    GenerateFileInput,
    GmailDraftReplyInput,
    GmailSearchInput,
    JobDiscoveryInput,
    ListDocumentsInput,
    ListRemindersInput,
    RememberFactInput,
    ForgetFactInput,
    SearchDocumentsInput,
    SearchMemoryInput,
    UrlReaderInput,
    WebSearchInput,
)
from app.database.repositories.audit_repo import AuditRepository
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.memory_repo import MemoryRepository
from app.database.repositories.reminder_repo import ReminderRepository
from app.database.session import get_db_session
from app.logging_config import get_logger
from app.memory.service import memory_service
from app.services.file_service import file_generator
from app.services.gmail_service import gmail_service
from app.services.job_service import job_service
from app.tools.url_reader import fetch_and_extract_url
from app.tools.web_search import web_search_tool

logger = get_logger(__name__)


class RegisteredTool:
    def __init__(
        self,
        name: str,
        description: str,
        schema: Type[BaseModel],
        handler: Callable[..., Any],
        permission_level: str = "read_only",  # read_only, state_change, consequential
    ):
        self.name = name
        self.description = description
        self.schema = schema
        self.handler = handler
        self.permission_level = permission_level

    def to_openai_tool(self) -> Dict[str, Any]:
        schema_dict = self.schema.model_json_schema()
        # Clean metadata not needed by OpenAI
        properties = schema_dict.get("properties", {})
        required = schema_dict.get("required", [])
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, RegisteredTool] = {}
        self._register_default_tools()

    def register(self, tool: RegisteredTool):
        self.tools[tool.name] = tool

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_tool() for tool in self.tools.values()]

    async def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        user_id: int,
    ) -> Dict[str, Any]:
        """Validates arguments, executes registered tool handler, and records audit event."""
        if name not in self.tools:
            return {"error": f"Tool '{name}' is not registered in the system.", "is_success": False}

        tool = self.tools[name]
        start_time = time.time()
        is_success = False
        failure_category = None
        result: Dict[str, Any] = {}

        try:
            # 1. Validate arguments using Pydantic schema
            validated_args = tool.schema(**arguments)
            
            # 2. Execute with timeout
            raw_result = await asyncio.wait_for(
                tool.handler(user_id=user_id, **validated_args.model_dump()),
                timeout=45.0,
            )
            result = raw_result if isinstance(raw_result, dict) else {"result": raw_result}
            is_success = True

        except ValidationError as e:
            failure_category = "validation_error"
            result = {"error": f"Invalid tool arguments: {e.errors()}", "is_success": False}
        except asyncio.TimeoutError:
            failure_category = "timeout"
            result = {"error": f"Tool '{name}' timed out after 45 seconds.", "is_success": False}
        except Exception as e:
            failure_category = "execution_error"
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            result = {"error": str(e), "is_success": False}

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 3. Record audit log in database
        try:
            async with get_db_session() as session:
                audit_repo = AuditRepository(session)
                await audit_repo.record_tool_execution(
                    tool_name=name,
                    user_id=user_id,
                    tool_args=arguments,
                    tool_result=result,
                    is_success=is_success,
                    execution_time_ms=elapsed_ms,
                    failure_category=failure_category,
                )
        except Exception as db_err:
            logger.warning(f"Could not record tool execution audit: {db_err}")

        return result

    def _register_default_tools(self):
        # 1. Web Search
        async def _web_search(user_id: int, query: str, max_results: int = 5):
            return await web_search_tool.search(query=query, max_results=max_results)

        self.register(
            RegisteredTool(
                name="web_search",
                description="Search the web for up-to-date news, research, technical facts, and verified citations.",
                schema=WebSearchInput,
                handler=_web_search,
                permission_level="read_only",
            )
        )

        # 2. URL Reader
        async def _read_url(user_id: int, url: str):
            return await fetch_and_extract_url(url=url)

        self.register(
            RegisteredTool(
                name="read_url",
                description="Safely fetch and read article content or text from a public web URL.",
                schema=UrlReaderInput,
                handler=_read_url,
                permission_level="read_only",
            )
        )

        # 3. Remember Fact
        async def _remember_fact(user_id: int, content: str, category: str = "general"):
            return await memory_service.save_fact(user_id=user_id, content=content, category=category)

        self.register(
            RegisteredTool(
                name="remember_fact",
                description="Persistently store a user preference, background detail, or approved instruction.",
                schema=RememberFactInput,
                handler=_remember_fact,
                permission_level="state_change",
            )
        )

        # 4. Forget Fact
        async def _forget_fact(user_id: int, memory_id: str):
            deleted = await memory_service.delete_fact(user_id=user_id, memory_id=memory_id)
            return {"deleted": deleted, "memory_id": memory_id}

        self.register(
            RegisteredTool(
                name="forget_fact",
                description="Permanently delete a specific stored fact from personal memory.",
                schema=ForgetFactInput,
                handler=_forget_fact,
                permission_level="state_change",
            )
        )

        # 5. Search Memory
        async def _search_memory(user_id: int, query: str):
            async with get_db_session() as session:
                repo = MemoryRepository(session)
                mems = await repo.search_memories(user_id=user_id, query=query)
                return {"facts": [{"id": m.id, "category": m.category, "content": m.content} for m in mems]}

        self.register(
            RegisteredTool(
                name="search_memory",
                description="Search stored personal facts and user preferences.",
                schema=SearchMemoryInput,
                handler=_search_memory,
                permission_level="read_only",
            )
        )

        # 6. Search Documents
        async def _search_documents(user_id: int, query: str, top_k: int = 3):
            from app.memory.retrieval import MemoryRetriever
            ctx = await MemoryRetriever.get_relevant_context(user_id=user_id, query=query, top_chunks=top_k)
            return ctx

        self.register(
            RegisteredTool(
                name="search_documents",
                description="Semantically search excerpts from uploaded documents, CVs, and PDFs.",
                schema=SearchDocumentsInput,
                handler=_search_documents,
                permission_level="read_only",
            )
        )

        # 7. List Documents
        async def _list_documents(user_id: int):
            docs = await memory_service.list_documents(user_id=user_id)
            return {"documents": docs}

        self.register(
            RegisteredTool(
                name="list_documents",
                description="List all documents currently uploaded and indexed for the user.",
                schema=ListDocumentsInput,
                handler=_list_documents,
                permission_level="read_only",
            )
        )

        # 8. Gmail Search
        async def _gmail_search(user_id: int, query: str = "is:unread", max_results: int = 5):
            messages = await gmail_service.search_messages(user_id=user_id, query=query, max_results=max_results)
            return {"messages": messages, "count": len(messages)}

        self.register(
            RegisteredTool(
                name="gmail_search",
                description="Search user's Gmail inbox and read email snippets and metadata.",
                schema=GmailSearchInput,
                handler=_gmail_search,
                permission_level="read_only",
            )
        )

        # 9. Gmail Draft Reply
        async def _gmail_draft(user_id: int, to: str, subject: str, body: str, thread_id: Optional[str] = None):
            res = await gmail_service.create_draft(user_id=user_id, to=to, subject=subject, body=body, thread_id=thread_id)
            return res

        self.register(
            RegisteredTool(
                name="gmail_draft_reply",
                description="Draft an email reply in Gmail without sending it.",
                schema=GmailDraftReplyInput,
                handler=_gmail_draft,
                permission_level="state_change",
            )
        )

        # 10. Search Jobs
        async def _search_jobs(user_id: int, query: str, work_arrangement: str = "remote", location: Optional[str] = None, keywords: Optional[str] = None):
            jobs = await job_service.find_opportunities(
                user_id=user_id,
                query=query,
                work_arrangement=work_arrangement,
                location=location,
                keywords=keywords,
            )
            return {"discovered_jobs": jobs, "count": len(jobs)}

        self.register(
            RegisteredTool(
                name="search_jobs",
                description="Discover and deduplicate remote, hybrid, or onsite job and freelance opportunities.",
                schema=JobDiscoveryInput,
                handler=_search_jobs,
                permission_level="read_only",
            )
        )

        # 11. Create Reminder
        async def _create_reminder(user_id: int, title: str, scheduled_at: str, description: Optional[str] = None):
            # Parse datetime string
            try:
                # Remove Z or parse isoformat
                clean_iso = scheduled_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                raise ValueError(f"Could not parse datetime '{scheduled_at}'. Please format as ISO 8601, e.g. '2026-10-22T10:00:00Z'.")

            async with get_db_session() as session:
                repo = ReminderRepository(session)
                rem = await repo.create_reminder(
                    user_id=user_id,
                    title=title,
                    scheduled_at_utc=dt,
                    description=description,
                )
                return {
                    "reminder_id": rem.id,
                    "title": rem.title,
                    "scheduled_at_utc": rem.scheduled_at_utc.isoformat(),
                    "status": rem.status,
                }

        self.register(
            RegisteredTool(
                name="create_reminder",
                description="Schedule a persistent reminder or personal task.",
                schema=CreateReminderInput,
                handler=_create_reminder,
                permission_level="state_change",
            )
        )

        # 12. List Reminders
        async def _list_reminders(user_id: int, include_completed: bool = False):
            async with get_db_session() as session:
                repo = ReminderRepository(session)
                reminders = await repo.list_user_reminders(user_id=user_id, include_completed=include_completed)
                return {
                    "reminders": [
                        {
                            "id": r.id,
                            "title": r.title,
                            "scheduled_at_utc": r.scheduled_at_utc.isoformat(),
                            "status": r.status,
                        }
                        for r in reminders
                    ]
                }

        self.register(
            RegisteredTool(
                name="list_reminders",
                description="List upcoming or pending reminders and tasks.",
                schema=ListRemindersInput,
                handler=_list_reminders,
                permission_level="read_only",
            )
        )

        # 13. Cancel Reminder
        async def _cancel_reminder(user_id: int, reminder_id: str):
            async with get_db_session() as session:
                repo = ReminderRepository(session)
                cancelled = await repo.cancel_reminder(reminder_id=reminder_id, user_id=user_id)
                return {"cancelled": cancelled, "reminder_id": reminder_id}

        self.register(
            RegisteredTool(
                name="cancel_reminder",
                description="Cancel an active reminder.",
                schema=CancelReminderInput,
                handler=_cancel_reminder,
                permission_level="state_change",
            )
        )

        # 14. Generate File
        async def _generate_file(
            user_id: int,
            file_type: str,
            filename: str,
            title: Optional[str] = "Report",
            content: Optional[str] = None,
            rows: Optional[List[Dict[str, Any]]] = None,
            paragraphs: Optional[List[str]] = None,
        ):
            ft = file_type.lower().strip()
            if ft == "txt":
                path = file_generator.generate_text_file(content=content or "", filename=filename)
            elif ft == "csv":
                path = file_generator.generate_csv_file(rows=rows or [], filename=filename)
            elif ft == "pdf":
                path = file_generator.generate_pdf_report(title=title or "Report", paragraphs=paragraphs or [content or ""], filename=filename)
            elif ft == "docx":
                path = file_generator.generate_docx_document(title=title or "Document", paragraphs=paragraphs or [content or ""], filename=filename)
            else:
                raise ValueError(f"Unsupported file type: {ft}. Supported: txt, csv, pdf, docx")

            return {
                "file_path": path,
                "filename": filename,
                "file_type": ft,
                "message": f"Generated file saved at {path}. Ready for delivery.",
            }

        self.register(
            RegisteredTool(
                name="generate_file",
                description="Generate a downloadable TXT note, CSV spreadsheet, PDF report, or DOCX document.",
                schema=GenerateFileInput,
                handler=_generate_file,
                permission_level="state_change",
            )
        )


tool_registry = ToolRegistry()
