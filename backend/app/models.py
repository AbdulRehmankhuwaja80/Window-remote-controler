import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Integer,
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(32), nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)
    reset_token = Column(String(64), nullable=True)
    reset_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    devices = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("SessionLog", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    replaced_by_token = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="refresh_tokens")


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_name = Column(String(120), nullable=False)
    hostname = Column(String(120), nullable=True)
    os_info = Column(String(120), default="Windows 11")
    hardware_id = Column(String(120), index=True, nullable=True)
    status = Column(String(30), default="OFFLINE")  # ONLINE, OFFLINE, IN_SESSION, PAUSED
    is_remote_enabled = Column(Boolean, default=True)
    auth_key = Column(String(64), nullable=False, default=lambda: uuid.uuid4().hex)
    pairing_code = Column(String(6), nullable=True)  # 6-digit one-time code for new client authorization
    pairing_verified = Column(Boolean, default=True)
    ip_address = Column(String(64), nullable=True)
    last_seen = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    owner = relationship("User", back_populates="devices")
    sessions = relationship("SessionLog", back_populates="device", cascade="all, delete-orphan")


class SessionLog(Base):
    __tablename__ = "session_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    client_info = Column(String(120), nullable=True)
    status = Column(String(30), default="ACTIVE")  # ACTIVE, TERMINATED, REJECTED, ERROR
    started_at = Column(DateTime, default=utc_now)
    ended_at = Column(DateTime, nullable=True)
    termination_reason = Column(String(255), nullable=True)

    user = relationship("User", back_populates="sessions")
    device = relationship("Device", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(36), nullable=True)
    action = Column(String(60), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now)
