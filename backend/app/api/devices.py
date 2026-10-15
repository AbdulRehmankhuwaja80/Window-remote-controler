import random
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.models import User, Device, AuditLog
from backend.app.schemas import (
    DeviceOut,
    DeviceRegisterRequest,
    DeviceHostRegisterResponse,
    DeviceUpdateRequest,
)
from backend.app.signaling import manager

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceOut])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).where(Device.user_id == current_user.id).order_by(Device.created_at.desc())
    res = await db.execute(stmt)
    devices = res.scalars().all()
    
    # Sync with live WebSocket state
    result = []
    for d in devices:
        live_status = "ONLINE" if manager.is_host_online(d.id) else d.status
        if live_status == "ONLINE" and not manager.is_host_online(d.id):
            live_status = "OFFLINE"
        
        d_out = DeviceOut(
            id=d.id,
            user_id=d.user_id,
            device_name=d.device_name,
            hostname=d.hostname,
            os_info=d.os_info,
            status=live_status,
            is_remote_enabled=d.is_remote_enabled,
            ip_address=d.ip_address,
            last_seen=d.last_seen,
            created_at=d.created_at,
        )
        result.append(d_out)
    return result


@router.post("/register-host", response_model=DeviceHostRegisterResponse)
async def register_host_device(
    payload: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if this hardware_id already exists for this user
    device = None
    if payload.hardware_id:
        stmt = select(Device).where(
            Device.user_id == current_user.id,
            Device.hardware_id == payload.hardware_id,
        )
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()

    pairing_code = f"{random.randint(100000, 999999)}"

    if device:
        # Update existing
        device.device_name = payload.device_name
        device.hostname = payload.hostname or device.hostname
        device.os_info = payload.os_info or device.os_info
        device.last_seen = datetime.now(timezone.utc)
        device.pairing_code = pairing_code
    else:
        # Create new device
        device = Device(
            user_id=current_user.id,
            device_name=payload.device_name,
            hostname=payload.hostname,
            os_info=payload.os_info or "Windows 11",
            hardware_id=payload.hardware_id,
            status="OFFLINE",
            pairing_code=pairing_code,
            pairing_verified=True,
        )
        db.add(device)

    # Log audit event
    audit = AuditLog(
        user_id=current_user.id,
        device_id=device.id,
        action="DEVICE_REGISTERED",
        details=f"Host registered: {payload.device_name} ({payload.os_info})",
    )
    db.add(audit)

    await db.commit()
    await db.refresh(device)

    return DeviceHostRegisterResponse(
        device=DeviceOut.model_validate(device),
        auth_key=device.auth_key,
        pairing_code=pairing_code,
    )


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).where(Device.id == device_id, Device.user_id == current_user.id)
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    
    live_status = "ONLINE" if manager.is_host_online(device.id) else device.status
    if live_status == "ONLINE" and not manager.is_host_online(device.id):
        live_status = "OFFLINE"
    
    return DeviceOut(
        id=device.id,
        user_id=device.user_id,
        device_name=device.device_name,
        hostname=device.hostname,
        os_info=device.os_info,
        status=live_status,
        is_remote_enabled=device.is_remote_enabled,
        ip_address=device.ip_address,
        last_seen=device.last_seen,
        created_at=device.created_at,
    )


@router.patch("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: str,
    payload: DeviceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).where(Device.id == device_id, Device.user_id == current_user.id)
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    if payload.device_name is not None:
        device.device_name = payload.device_name
    if payload.is_remote_enabled is not None:
        device.is_remote_enabled = payload.is_remote_enabled
    if payload.status is not None:
        device.status = payload.status

    await db.commit()
    await db.refresh(device)
    return DeviceOut.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).where(Device.id == device_id, Device.user_id == current_user.id)
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    # Disconnect if active
    if manager.is_host_online(device_id):
        await manager.disconnect_host(device_id)

    await db.delete(device)
    await db.commit()
    return None
