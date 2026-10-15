import pytest
import json
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database import init_db
from backend.app.signaling import manager


@pytest.mark.asyncio
async def test_full_remote_desktop_signaling_lifecycle():
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Register User
        email = "remote_traveler@example.com"
        reg = await ac.post("/api/auth/register", json={
            "email": email,
            "password": "SecurePassword2026!",
            "full_name": "Alex Traveler",
        })
        assert reg.status_code in [201, 400]

        # 2. Login
        login = await ac.post("/api/auth/login", json={
            "email": email,
            "password": "SecurePassword2026!",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Register Laptop Host
        host_reg = await ac.post("/api/devices/register-host", json={
            "device_name": "Home Laptop Dell XPS 15",
            "hostname": "DELL-XPS-HOME",
            "os_info": "Windows 11 Pro 64-bit",
            "hardware_id": "HW-E2E-998877",
        }, headers=headers)
        assert host_reg.status_code == 200
        host_info = host_reg.json()
        device_id = host_info["device"]["id"]
        auth_key = host_info["auth_key"]
        assert device_id is not None
        assert auth_key is not None

        # 4. List Devices
        devs = await ac.get("/api/devices", headers=headers)
        assert devs.status_code == 200
        device_list = devs.json()
        assert any(d["id"] == device_id for d in device_list)

        # 5. Start Session API
        # First register host on WebSocket so device is ONLINE
        with TestClient(app) as test_client:
            with test_client.websocket_connect(
                f"/ws/signaling?role=host&device_id={device_id}&auth_key={auth_key}"
            ) as host_ws:
                # Host receives confirmation
                host_reg_msg = json.loads(host_ws.receive_text())
                assert host_reg_msg["type"] == "registered"
                assert host_reg_msg["role"] == "host"

                # Check device status is now ONLINE
                assert manager.is_host_online(device_id)

                # Now Android mobile client connects to WebSocket
                with test_client.websocket_connect(
                    f"/ws/signaling?role=client&token={token}"
                ) as client_ws:
                    client_reg_msg = json.loads(client_ws.receive_text())
                    assert client_reg_msg["type"] == "registered"
                    assert client_reg_msg["role"] == "client"
                    client_id = client_reg_msg["client_id"]

                    # Android sends session request
                    client_ws.send_text(json.dumps({
                        "type": "session_request",
                        "target_device_id": device_id,
                        "session_id": "sess-e2e-12345",
                        "client_info": "Pixel 8 Pro Android 14",
                    }))

                    # Host receives incoming session request
                    inc_req = json.loads(host_ws.receive_text())
                    assert inc_req["type"] == "incoming_session_request"
                    assert inc_req["session_id"] == "sess-e2e-12345"
                    assert inc_req["client_info"] == "Pixel 8 Pro Android 14"

                    # Host accepts session request
                    host_ws.send_text(json.dumps({
                        "type": "session_response",
                        "session_id": "sess-e2e-12345",
                        "client_id": client_id,
                        "accepted": True,
                    }))

                    # Android receives accepted response
                    client_resp = json.loads(client_ws.receive_text())
                    assert client_resp["type"] == "session_response"
                    assert client_resp["accepted"] is True

                    # Android sends WebRTC Offer SDP
                    offer_sdp = "v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
                    client_ws.send_text(json.dumps({
                        "type": "webrtc_offer",
                        "session_id": "sess-e2e-12345",
                        "sdp": offer_sdp,
                    }))

                    # Host receives Offer SDP
                    host_offer = json.loads(host_ws.receive_text())
                    assert host_offer["type"] == "webrtc_offer"
                    assert host_offer["sdp"] == offer_sdp

                    # Host sends Answer SDP
                    answer_sdp = "v=0\r\no=- 67890 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
                    host_ws.send_text(json.dumps({
                        "type": "webrtc_answer",
                        "session_id": "sess-e2e-12345",
                        "sdp": answer_sdp,
                    }))

                    # Android receives Answer SDP
                    client_ans = json.loads(client_ws.receive_text())
                    assert client_ans["type"] == "webrtc_answer"
                    assert client_ans["sdp"] == answer_sdp

                    # Peer exchanges ICE candidate
                    candidate_str = "candidate:1 1 UDP 2130706431 192.168.1.100 50000 typ host"
                    client_ws.send_text(json.dumps({
                        "type": "ice_candidate",
                        "session_id": "sess-e2e-12345",
                        "candidate": candidate_str,
                    }))

                    host_cand = json.loads(host_ws.receive_text())
                    assert host_cand["type"] == "ice_candidate"
                    assert host_cand["candidate"] == candidate_str

                    # Terminate session
                    client_ws.send_text(json.dumps({
                        "type": "session_end",
                        "session_id": "sess-e2e-12345",
                        "reason": "User completed task",
                    }))

                    term_host = json.loads(host_ws.receive_text())
                    assert term_host["type"] == "session_terminated"

                    term_client = json.loads(client_ws.receive_text())
                    assert term_client["type"] == "session_terminated"
