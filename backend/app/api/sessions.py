import uuid
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.models import User, Device, SessionLog, AuditLog
from backend.app.schemas import (
    WebRtcConfigResponse,
    SessionStartRequest,
    SessionStartResponse,
    AuditLogOut,
)
from backend.app.signaling import manager
from backend.app.turn import generate_ice_servers

router = APIRouter(prefix="/sessions", tags=["Sessions & WebRTC"])


@router.get("/ice-servers", response_model=WebRtcConfigResponse)
async def get_ice_servers(current_user: User = Depends(get_current_user)):
    servers = generate_ice_servers(user_id=current_user.id)
    return WebRtcConfigResponse(ice_servers=servers)


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    payload: SessionStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).where(Device.id == payload.device_id, Device.user_id == current_user.id)
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    if not device.is_remote_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Remote access is paused or disabled on this laptop.",
        )

    if not manager.is_host_online(device.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is currently offline. Ensure laptop is powered on, awake, and RemoDesk host is running.",
        )

    session_id = str(uuid.uuid4())
    session_log = SessionLog(
        id=session_id,
        user_id=current_user.id,
        device_id=device.id,
        client_info=payload.client_info,
        status="STARTING",
    )
    db.add(session_log)

    audit = AuditLog(
        user_id=current_user.id,
        device_id=device.id,
        action="SESSION_START_REQUEST",
        details=f"Client ({payload.client_info}) requested session",
    )
    db.add(audit)

    await db.commit()

    ice_servers = generate_ice_servers(user_id=current_user.id)
    return SessionStartResponse(
        session_id=session_id,
        device_id=device.id,
        status="CONNECTING",
        ice_servers=ice_servers,
    )


@router.get("/audit", response_model=List[AuditLogOut])
async def get_audit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    res = await db.execute(stmt)
    return [AuditLogOut.model_validate(log) for log in res.scalars().all()]
