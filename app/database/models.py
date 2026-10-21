import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.types import JSON, TypeDecorator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type if available, otherwise uses String(36).
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)


class JsonType(TypeDecorator):
    """Platform-independent JSON type.
    Uses JSONB on PostgreSQL, normal JSON on SQLite.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class VectorType(TypeDecorator):
    """Platform-independent vector type.
    Stores list of floats as JSON array in SQLite, or pgvector Vector in PostgreSQL.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 384, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except ImportError:
                return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram User ID
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    is_allowed = Column(Boolean, default=True, nullable=False)
    settings = Column(JsonType, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("PersonalMemory", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    oauth_credentials = relationship("OAuthCredential", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    summaries = relationship("ConversationSummary", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(GUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # system, user, assistant, tool
    content = Column(Text, nullable=True)
    tool_calls = Column(JsonType, nullable=True)
    tool_call_id = Column(String(255), nullable=True)
    token_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    conversation = relationship("Conversation", back_populates="messages")


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(GUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_text = Column(Text, nullable=False)
    up_to_message_id = Column(GUID, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="summaries")


class PersonalMemory(Base):
    __tablename__ = "personal_memories"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), default="general", nullable=False, index=True)
    content = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    verification_state = Column(String(50), default="verified", nullable=False)
    source = Column(String(255), default="user_instruction", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="memories")


class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(String(500), nullable=False)
    page_count = Column(Integer, default=1, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    is_indexed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JsonType, default=dict, nullable=False)
    embedding = Column(VectorType(dim=384), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("Document", back_populates="chunks")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    normalized_url = Column(String(1000), nullable=False)
    source_domain = Column(String(255), nullable=False)
    title = Column(String(500), nullable=False)
    employer = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    work_arrangement = Column(String(100), nullable=True)  # remote, hybrid, onsite
    compensation = Column(String(255), nullable=True)
    date_posted = Column(String(100), nullable=True)
    date_discovered = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    summary = Column(Text, nullable=True)
    source_link = Column(String(1000), nullable=False)
    match_rationale = Column(Text, nullable=True)
    application_status = Column(String(50), default="discovered", nullable=False)
    fingerprint = Column(String(64), nullable=False, unique=True, index=True)

    user = relationship("User", back_populates="jobs")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_at_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    recurrence_rule = Column(String(255), nullable=True)
    timezone = Column(String(100), default="Africa/Lagos", nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, delivered, failed, cancelled, completed
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    idempotency_key = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="reminders")


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, nullable=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    tool_args = Column(JsonType, nullable=True)
    tool_result = Column(JsonType, nullable=True)
    is_success = Column(Boolean, default=True, nullable=False)
    execution_time_ms = Column(Integer, default=0, nullable=False)
    failure_category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class TelegramUpdate(Base):
    __tablename__ = "telegram_updates"

    update_id = Column(BigInteger, primary_key=True)
    processed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    user_id = Column(BigInteger, nullable=True)
    update_type = Column(String(50), nullable=True)


class OAuthCredential(Base):
    __tablename__ = "oauth_credentials"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), default="google_gmail", nullable=False)
    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="oauth_credentials")
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)


class PendingApproval(Base):
    __tablename__ = "pending_approvals"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    action_args = Column(JsonType, nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, approved, rejected, expired
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(GUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    details = Column(JsonType, default=dict, nullable=False)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
