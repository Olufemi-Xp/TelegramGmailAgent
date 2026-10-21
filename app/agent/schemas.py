from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    query: str = Field(description="Search terms or question to research on the web")
    max_results: int = Field(default=5, description="Maximum number of search results to retrieve (1-10)")


class UrlReaderInput(BaseModel):
    url: str = Field(description="Public HTTP or HTTPS URL of the web page or article to read")


class RememberFactInput(BaseModel):
    content: str = Field(description="Fact, preference, instruction, or background detail to remember")
    category: str = Field(default="general", description="Category for organizing memory: e.g. career, preferences, family, tech, general")


class ForgetFactInput(BaseModel):
    memory_id: str = Field(description="Unique ID of the personal memory to delete")


class SearchMemoryInput(BaseModel):
    query: str = Field(description="Search keywords to find stored personal facts")


class SearchDocumentsInput(BaseModel):
    query: str = Field(description="Query to search semantic excerpts from uploaded CVs and documents")
    top_k: int = Field(default=3, description="Number of excerpts to retrieve")


class ListDocumentsInput(BaseModel):
    pass


class GmailSearchInput(BaseModel):
    query: str = Field(default="is:unread", description="Gmail search query string, e.g. 'is:unread', 'from:recruiter', 'newer_than:2d'")
    max_results: int = Field(default=5, description="Maximum number of emails to retrieve (1-10)")


class GmailDraftReplyInput(BaseModel):
    to: str = Field(description="Recipient email address")
    subject: str = Field(description="Subject line for the email")
    body: str = Field(description="Email body text content")
    thread_id: Optional[str] = Field(default=None, description="Optional Gmail thread ID to reply within an existing thread")


class JobDiscoveryInput(BaseModel):
    query: str = Field(description="Role, tech stack, or job title to search for, e.g. 'Senior Python AI Engineer'")
    work_arrangement: str = Field(default="remote", description="Work arrangement: 'remote', 'hybrid', or 'onsite'")
    location: Optional[str] = Field(default=None, description="Target city, country, or timezone, e.g. 'Europe', 'US', 'Japan'")
    keywords: Optional[str] = Field(default=None, description="Additional keywords or skills to include")


class CreateReminderInput(BaseModel):
    title: str = Field(description="Title or task description for the reminder")
    scheduled_at: str = Field(description="ISO 8601 formatted datetime string (e.g. 2026-10-22T09:00:00Z) or relative expression")
    description: Optional[str] = Field(default=None, description="Optional extra details or checklist notes")


class ListRemindersInput(BaseModel):
    include_completed: bool = Field(default=False, description="Whether to include delivered/completed reminders")


class CancelReminderInput(BaseModel):
    reminder_id: str = Field(description="Unique ID of the reminder to cancel")


class GenerateFileInput(BaseModel):
    file_type: str = Field(description="Type of file to generate: 'txt', 'csv', 'pdf', or 'docx'")
    filename: str = Field(description="Desired output filename, e.g. 'market_research.pdf', 'jobs.csv'")
    title: Optional[str] = Field(default="Document", description="Title for document reports (PDF/DOCX)")
    content: Optional[str] = Field(default=None, description="Text content for TXT files or report body")
    rows: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of row dictionaries for CSV files")
    paragraphs: Optional[List[str]] = Field(default=None, description="List of paragraph strings for PDF/DOCX reports")
