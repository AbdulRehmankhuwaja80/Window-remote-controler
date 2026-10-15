import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.database import init_db
from backend.app.turn import generate_ice_servers


@pytest.mark.asyncio
async def test_auth_and_device_flow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Register User
        reg_resp = await ac.post("/api/auth/register", json={
            "email": "tester@example.com",
            "password": "SuperSecretPassword123!",
            "full_name": "Test User",
        })
        assert reg_resp.status_code in [201, 400]
        
        # 2. Login
        login_resp = await ac.post("/api/auth/login", json={
            "email": "tester@example.com",
            "password": "SuperSecretPassword123!",
        })
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        token = token_data["access_token"]
        assert token is not None
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


def test_turn_generator():
    servers = generate_ice_servers("user-12345")
    assert len(servers) >= 1
    stun_found = any("stun:" in url for s in servers for url in s.urls)
    assert stun_found
