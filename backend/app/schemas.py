from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=32)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# Device Schemas
class DeviceRegisterRequest(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=100)
    hostname: Optional[str] = None
    os_info: Optional[str] = "Windows 11"
    hardware_id: Optional[str] = None


class DeviceUpdateRequest(BaseModel):
    device_name: Optional[str] = None
    is_remote_enabled: Optional[bool] = None
    status: Optional[str] = None


class PairDeviceRequest(BaseModel):
    pairing_code: Optional[str] = None
    partner_id: Optional[str] = None
    pin: Optional[str] = None


class DeviceOut(BaseModel):
    id: str
    user_id: str
    device_name: str
    hostname: Optional[str] = None
    os_info: str
    status: str
    is_remote_enabled: bool
    ip_address: Optional[str] = None
    last_seen: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceHostRegisterResponse(BaseModel):
    device: DeviceOut
    auth_key: str
    pairing_code: Optional[str] = None


# WebRTC & Signaling Schemas
class IceServerConfig(BaseModel):
    urls: List[str]
    username: Optional[str] = None
    credential: Optional[str] = None


class WebRtcConfigResponse(BaseModel):
    ice_servers: List[IceServerConfig]


class SessionStartRequest(BaseModel):
    device_id: str
    client_info: Optional[str] = "Android Mobile"


class SessionStartResponse(BaseModel):
    session_id: str
    device_id: str
    status: str
    ice_servers: List[IceServerConfig]


class AuditLogOut(BaseModel):
    id: int
    user_id: str
    device_id: Optional[str] = None
    action: str
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
