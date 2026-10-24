import random
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import get_current_user, get_optional_current_user, get_password_hash
from backend.app.database import get_db
from backend.app.models import User, Device, AuditLog
from backend.app.schemas import (
    DeviceOut,
    DeviceRegisterRequest,
    DeviceHostRegisterResponse,
    DeviceUpdateRequest,
    PairDeviceRequest,
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
    current_user: User = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Determine the owning user
    target_user_id = current_user.id if current_user else None

    # Check if this hardware_id already exists
    device = None
    if payload.hardware_id:
        stmt = select(Device).where(Device.hardware_id == payload.hardware_id)
        if target_user_id:
            stmt = stmt.where(Device.user_id == target_user_id)
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()

    if not target_user_id:
        if device:
            target_user_id = device.user_id
        else:
            # Check for existing users or create default local owner
            user_stmt = select(User).order_by(User.created_at.asc())
            user_res = await db.execute(user_stmt)
            first_user = user_res.scalars().first()
            if first_user:
                target_user_id = first_user.id
            else:
                default_user = User(
                    email="owner@remodesk.local",
                    hashed_password=get_password_hash("RemoDeskDefaultOwner2026!"),
                    full_name="Local Machine Owner",
                )
                db.add(default_user)
                await db.flush()
                target_user_id = default_user.id

    pairing_code = f"{random.randint(100000, 999999)}"

    if device:
        # Update existing
        device.user_id = target_user_id
        device.device_name = payload.device_name
        device.hostname = payload.hostname or device.hostname
        device.os_info = payload.os_info or device.os_info
        device.last_seen = datetime.now(timezone.utc)
        device.pairing_code = pairing_code
    else:
        # Create new device
        device = Device(
            user_id=target_user_id,
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
        user_id=target_user_id,
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


@router.post("/pair", response_model=DeviceOut)
async def pair_device_by_code(
    pairing_code: str = None,
    body: PairDeviceRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    code = pairing_code or (body.pairing_code if body else None) or (body.pin if body else None)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pairing PIN or code is required.")
    
    code = str(code).strip()
    device = None
    if body and body.partner_id and body.partner_id.strip():
        p_id = body.partner_id.strip()
        stmt = select(Device).where(
            (Device.hostname.ilike(p_id)) | 
            (Device.device_name.ilike(p_id)) |
            (Device.id == p_id)
        )
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()
        if device and str(device.pairing_code).strip() != code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN does not match the Partner ID.")
    
    if not device:
        stmt = select(Device).where(Device.pairing_code == code)
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid Partner ID or PIN.")

    device.user_id = current_user.id
    device.pairing_verified = True
    await db.commit()
    await db.refresh(device)
    return DeviceOut.model_validate(device)



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
