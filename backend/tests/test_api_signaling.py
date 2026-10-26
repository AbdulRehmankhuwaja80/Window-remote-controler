import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.app.main import app
from backend.app.database import init_db, async_session_maker
from backend.app.models import User
from backend.app.turn import generate_ice_servers


@pytest.mark.asyncio
async def test_auth_and_device_flow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "tester@example.com"
        password = "SuperSecretPassword123!"

        # 1. Register User
        reg_resp = await ac.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Test User",
        })
        assert reg_resp.status_code in [201, 400]

        # 1.1 Check unverified account cannot log in if verification required
        async with async_session_maker() as session:
            stmt = select(User).where(User.email == email)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            if user and not user.is_verified:
                unverified_login = await ac.post("/api/auth/login", json={
                    "email": email,
                    "password": password,
                })
                assert unverified_login.status_code == 403

                # 1.2 Verify email with code
                if not user.verification_code:
                    resend = await ac.post("/api/auth/resend-verification", json={"email": email})
                    assert resend.status_code == 200
                    await session.refresh(user)

                v_resp = await ac.post("/api/auth/verify-email", json={
                    "email": email,
                    "code": user.verification_code,
                })
                assert v_resp.status_code == 200
        
        # 2. Login (now verified)
        login_resp = await ac.post("/api/auth/login", json={
            "email": email,
            "password": password,
        })
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        assert token is not None
        assert refresh_token is not None
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Register Host Device
        host_resp = await ac.post("/api/devices/register-host", json={
            "device_name": "Office Laptop ThinkPad",
            "hostname": "THINKPAD-X1",
            "os_info": "Windows 11 Pro 23H2",
            "hardware_id": "HW-TEST-UUID-9999",
        }, headers=headers)
        assert host_resp.status_code == 200
        host_data = host_resp.json()
        device_id = host_data["device"]["id"]
        auth_key = host_data["auth_key"]
        assert device_id is not None
        assert auth_key is not None

        # 4. List Devices
        dev_list_resp = await ac.get("/api/devices", headers=headers)
        assert dev_list_resp.status_code == 200
        devices = dev_list_resp.json()
        assert len(devices) >= 1
        assert any(d["id"] == device_id for d in devices)

        # 5. ICE Servers config check
        ice_resp = await ac.get("/api/sessions/ice-servers", headers=headers)
        assert ice_resp.status_code == 200
        ice_data = ice_resp.json()
        assert len(ice_data["ice_servers"]) >= 1


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "refresh_tester@example.com"
        password = "Password987!"

        # Register
        await ac.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Refresh Tester",
        })

        # Verify
        async with async_session_maker() as session:
            stmt = select(User).where(User.email == email)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            user.is_verified = True
            await session.commit()

        # Login to obtain initial tokens
        login = await ac.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        tokens = login.json()
        first_refresh = tokens["refresh_token"]

        # Rotate refresh token
        ref_resp = await ac.post("/api/auth/refresh", json={"refresh_token": first_refresh})
        assert ref_resp.status_code == 200
        rotated = ref_resp.json()
        second_refresh = rotated["refresh_token"]
        assert second_refresh != first_refresh
        assert rotated["access_token"] is not None

        # Old refresh token is now revoked and must be rejected
        old_ref_resp = await ac.post("/api/auth/refresh", json={"refresh_token": first_refresh})
        assert old_ref_resp.status_code == 401

        # Logout with active refresh token
        headers = {"Authorization": f"Bearer {rotated['access_token']}"}
        logout_resp = await ac.post("/api/auth/logout", json={"refresh_token": second_refresh}, headers=headers)
        assert logout_resp.status_code == 200

        # Now second_refresh is also revoked
        second_ref_resp = await ac.post("/api/auth/refresh", json={"refresh_token": second_refresh})
        assert second_ref_resp.status_code == 401


@pytest.mark.asyncio
async def test_password_recovery_and_reset():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "recovery_tester@example.com"
        old_password = "OldPassword123!"
        new_password = "NewPassword456!"

        await ac.post("/api/auth/register", json={
            "email": email,
            "password": old_password,
            "full_name": "Recovery Tester",
        })

        # Verify user
        async with async_session_maker() as session:
            stmt = select(User).where(User.email == email)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            user.is_verified = True
            await session.commit()

        # Request reset token
        req_resp = await ac.post("/api/auth/forgot-password", json={"email": email})
        assert req_resp.status_code == 200

        # Retrieve generated token from DB
        async with async_session_maker() as session:
            stmt = select(User).where(User.email == email)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            reset_token = user.reset_token
            assert reset_token is not None

        # Complete reset
        reset_resp = await ac.post("/api/auth/reset-password", json={
            "token": reset_token,
            "new_password": new_password,
        })
        assert reset_resp.status_code == 200

        # Old password fails
        bad_login = await ac.post("/api/auth/login", json={"email": email, "password": old_password})
        assert bad_login.status_code == 401

        # New password succeeds
        good_login = await ac.post("/api/auth/login", json={"email": email, "password": new_password})
        assert good_login.status_code == 200


@pytest.mark.asyncio
async def test_device_permissions_and_audit_logging():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "audit_tester@example.com"
        password = "AuditPassword123!"

        await ac.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Audit Tester",
        })

        # Verify
        async with async_session_maker() as session:
            stmt = select(User).where(User.email == email)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            user.is_verified = True
            await session.commit()

        login = await ac.post("/api/auth/login", json={"email": email, "password": password})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Register device
        reg_dev = await ac.post("/api/devices/register-host", json={
            "device_name": "Audit Test Laptop",
            "hostname": "AUDIT-LAPTOP",
            "os_info": "Windows 11",
            "hardware_id": "HW-AUDIT-001",
        }, headers=headers)
        assert reg_dev.status_code == 200
        device_id = reg_dev.json()["device"]["id"]

        # Rename device
        ren_resp = await ac.patch(f"/api/devices/{device_id}", json={
            "device_name": "Renamed Work Laptop"
        }, headers=headers)
        assert ren_resp.status_code == 200
        assert ren_resp.json()["device_name"] == "Renamed Work Laptop"

        # Toggle remote access
        toggle_resp = await ac.patch(f"/api/devices/{device_id}", json={
            "is_remote_enabled": False
        }, headers=headers)
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["is_remote_enabled"] is False

        # First-time host registration consent (approve)
        consent_resp = await ac.post(f"/api/devices/{device_id}/consent?approved=true", headers=headers)
        assert consent_resp.status_code == 200
        assert consent_resp.json()["is_remote_enabled"] is True

        # Check audit logs
        audit_resp = await ac.get("/api/sessions/audit", headers=headers)
        assert audit_resp.status_code == 200
        logs = audit_resp.json()
        assert len(logs) >= 3
        actions = [log["action"] for log in logs]
        assert "DEVICE_RENAMED" in actions
        assert "REMOTE_ACCESS_TOGGLED" in actions
        assert "DEVICE_REGISTRATION_APPROVED" in actions

        # Revoke / delete device
        del_resp = await ac.delete(f"/api/devices/{device_id}", headers=headers)
        assert del_resp.status_code == 204


def test_turn_generator():
    servers = generate_ice_servers("user-12345")
    assert len(servers) >= 1
    stun_found = any("stun:" in url for s in servers for url in s.urls)
    assert stun_found
