from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
    generate_verification_code,
    generate_secure_token,
    get_current_user,
)
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import User, RefreshToken, AuditLog
from backend.app.schemas import (
    UserCreate,
    UserLogin,
    UserOut,
    Token,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RefreshTokenRequest,
    LogoutRequest,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    email = user_in.email.lower().strip()
    stmt = select(User).where(User.email == email)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    verification_code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
    is_verified = settings.AUTO_VERIFY_NEW_USERS

    user = User(
        email=email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_verified=is_verified,
        verification_code=verification_code,
        verification_expires_at=expires_at,
    )
    db.add(user)
    await db.flush()

    raw_refresh, token_hash, ref_expires = create_refresh_token(user.id)
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=ref_expires,
    )
    db.add(db_refresh)

    audit = AuditLog(
        user_id=user.id,
        action="USER_REGISTERED",
        details=f"User registered with email {email}. Verified: {is_verified}",
    )
    db.add(audit)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.lower().strip()
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.is_verified:
        return MessageResponse(message="Account email is already verified.")

    now = datetime.now(timezone.utc)
    # Handle timezone-naive datetime from SQLite
    v_exp = user.verification_expires_at
    if v_exp and v_exp.tzinfo is None:
        v_exp = v_exp.replace(tzinfo=timezone.utc)

    if not user.verification_code or user.verification_code != payload.code.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    if v_exp and now > v_exp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code has expired. Please request a new code.")

    user.is_verified = True
    user.verification_code = None
    user.verification_expires_at = None

    audit = AuditLog(
        user_id=user.id,
        action="AUTH_EMAIL_VERIFIED",
        details=f"Email {email} successfully verified.",
    )
    db.add(audit)

    await db.commit()
    return MessageResponse(message="Email address verified successfully.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.lower().strip()
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        return MessageResponse(message="If this email is registered, a new verification code has been generated.")

    if user.is_verified:
        return MessageResponse(message="Email address is already verified.")

    code = generate_verification_code()
    user.verification_code = code
    user.verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)

    audit = AuditLog(
        user_id=user.id,
        action="VERIFICATION_CODE_RESENT",
        details=f"New verification code generated for {email}.",
    )
    db.add(audit)

    await db.commit()
    return MessageResponse(message="A new verification code has been issued. Check your email.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.lower().strip()
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        return MessageResponse(message="If this email is registered, password recovery instructions have been sent.")

    token = generate_secure_token(32)
    user.reset_token = token
    user.reset_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

    audit = AuditLog(
        user_id=user.id,
        action="PASSWORD_RESET_REQUESTED",
        details=f"Password reset token generated for {email}.",
    )
    db.add(audit)

    await db.commit()
    return MessageResponse(message="Password recovery token generated and sent to email address.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token = payload.token.strip()
    stmt = select(User).where(User.reset_token == token)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token.")

    now = datetime.now(timezone.utc)
    r_exp = user.reset_expires_at
    if r_exp and r_exp.tzinfo is None:
        r_exp = r_exp.replace(tzinfo=timezone.utc)

    if r_exp and now > r_exp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset token has expired.")

    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_expires_at = None

    # Revoke all existing refresh tokens for security
    stmt_ref = select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)
    ref_res = await db.execute(stmt_ref)
    for ref in ref_res.scalars().all():
        ref.is_revoked = True

    audit = AuditLog(
        user_id=user.id,
        action="AUTH_PASSWORD_RESET",
        details="Password successfully reset. All active sessions invalidated.",
    )
    db.add(audit)

    await db.commit()
    return MessageResponse(message="Password has been successfully reset. Please log in with your new password.")


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    email = credentials.email.lower().strip()
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    if not user.is_verified and not settings.AUTO_VERIFY_NEW_USERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account email is not verified. Please verify your email first.",
        )

    raw_refresh, token_hash, ref_expires = create_refresh_token(user.id)
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=ref_expires,
    )
    db.add(db_refresh)

    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN_SUCCESS",
        details=f"Successful login for {email}.",
    )
    db.add(audit)

    await db.commit()

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    raw_token = payload.refresh_token.strip()
    t_hash = hash_token(raw_token)

    stmt = select(RefreshToken).where(RefreshToken.token_hash == t_hash)
    res = await db.execute(stmt)
    db_token = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not db_token or db_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    exp = db_token.expires_at
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if now > exp:
        db_token.is_revoked = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt_user = select(User).where(User.id == db_token.user_id)
    u_res = await db.execute(stmt_user)
    user = u_res.scalar_one_or_none()
    if not user or not user.is_active:
        db_token.is_revoked = True
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive.")

    # Refresh token rotation: revoke old token and generate replacement
    db_token.is_revoked = True
    new_raw_refresh, new_token_hash, new_ref_expires = create_refresh_token(user.id)
    db_token.replaced_by_token = new_token_hash

    new_db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=new_ref_expires,
    )
    db.add(new_db_refresh)

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    await db.commit()
    return Token(
        access_token=access_token,
        refresh_token=new_raw_refresh,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if payload and payload.refresh_token:
        t_hash = hash_token(payload.refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == t_hash, RefreshToken.user_id == current_user.id)
        res = await db.execute(stmt)
        token = res.scalar_one_or_none()
        if token:
            token.is_revoked = True

    audit = AuditLog(
        user_id=current_user.id,
        action="USER_LOGOUT",
        details=f"User {current_user.email} signed out.",
    )
    db.add(audit)

    await db.commit()
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserOut)
async def get_profile(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
