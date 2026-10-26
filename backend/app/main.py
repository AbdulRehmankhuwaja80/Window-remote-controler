import json
import logging
import os
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select

from backend.app.config import settings
from backend.app.database import init_db, async_session_maker
from backend.app.auth import decode_token
from backend.app.models import Device, User, AuditLog, SessionLog
from backend.app.api.auth import router as auth_router
from backend.app.api.devices import router as devices_router
from backend.app.api.sessions import router as sessions_router
from backend.app.signaling import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("remodesk.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB
    logger.info("Initializing RemoDesk database schema...")
    await init_db()
    logger.info("Database initialized successfully.")
    yield
    # Shutdown
    logger.info("Shutting down RemoDesk gateway...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(devices_router, prefix=settings.API_V1_STR)
app.include_router(sessions_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "active_hosts": len(manager.active_hosts),
        "active_clients": len(manager.active_clients),
        "active_sessions": len(manager.sessions),
    }


@app.get("/download", response_class=HTMLResponse)
async def download_page():
    # Detect local LAN IP for display
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = "192.168.0.37"

    server_url = f"http://{lan_ip}:8000"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RemoDesk Mobile App Download</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #0A0E17;
            color: #E2E8F0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .card {{
            background: #1A2333;
            border: 1px solid #2D3748;
            border-radius: 20px;
            padding: 32px 24px;
            max-width: 440px;
            width: 100%;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .badge {{
            display: inline-block;
            background: rgba(0, 212, 255, 0.15);
            color: #00D4FF;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        h1 {{
            font-size: 26px;
            margin-bottom: 8px;
            color: #FFFFFF;
        }}
        p.subtitle {{
            color: #94A3B8;
            font-size: 14px;
            margin-bottom: 24px;
            line-height: 1.5;
        }}
        .btn-download {{
            display: block;
            background: linear-gradient(135deg, #0066FF, #00D4FF);
            color: #FFFFFF;
            text-decoration: none;
            padding: 16px 24px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 24px;
            box-shadow: 0 4px 15px rgba(0, 102, 255, 0.4);
            transition: transform 0.15s ease;
        }}
        .btn-download:active {{
            transform: scale(0.98);
        }}
        .url-box {{
            background: #0F172A;
            border: 1px dashed #3B82F6;
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 24px;
            text-align: left;
        }}
        .url-label {{
            font-size: 11px;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        .url-val {{
            font-family: monospace;
            font-size: 15px;
            color: #38BDF8;
            word-break: break-all;
            user-select: all;
        }}
        .steps {{
            text-align: left;
            border-top: 1px solid #2D3748;
            padding-top: 20px;
        }}
        .step {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 12px;
            font-size: 13px;
            color: #CBD5E1;
            line-height: 1.4;
        }}
        .step-num {{
            background: #3B82F6;
            color: white;
            font-weight: bold;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            flex-shrink: 0;
            margin-right: 10px;
            margin-top: 1px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Android Mobile Client</span>
        <h1>RemoDesk</h1>
        <p class="subtitle">Control your Windows laptop from anywhere with ultra low-latency WebRTC streaming.</p>

        <a href="/download/remodesk.apk" class="btn-download">
            Download RemoDesk APK (v1.0.0)
        </a>

        <div class="url-box">
            <div class="url-label">Server URL to use in App:</div>
            <div class="url-val" id="srvUrl">{server_url}</div>
        </div>

        <div class="steps">
            <div class="step">
                <div class="step-num">1</div>
                <div>Tap <b>Download RemoDesk APK</b> above and save the file.</div>
            </div>
            <div class="step">
                <div class="step-num">2</div>
                <div>Open the downloaded <code>RemoDesk.apk</code> and tap <b>Install</b> <i>(allow unknown sources if prompted)</i>.</div>
            </div>
            <div class="step">
                <div class="step-num">3</div>
                <div>Open RemoDesk on your phone, verify the Server URL is set to <code>{server_url}</code>, and sign in!</div>
            </div>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/download/remodesk.apk")
async def download_apk_file():
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [
        os.path.join(root_dir, "Apk", "RemoDesk-latest.apk"),
        os.path.join(root_dir, "Apk", "RemoDesk.apk"),
        os.path.join(root_dir, "android-client", "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    ]
    for path in candidates:
        if os.path.exists(path):
            return FileResponse(
                path,
                media_type="application/vnd.android.package-archive",
                filename="RemoDesk.apk"
            )
    raise HTTPException(status_code=404, detail="RemoDesk APK not found. Please compile it first.")


@app.websocket("/ws/signaling")
async def websocket_signaling(
    websocket: WebSocket,
    token: str = Query(None),
    role: str = Query("client"),  # 'client' or 'host'
    device_id: str = Query(None),
    auth_key: str = Query(None),
):
    await websocket.accept()
    client_id = None
    host_id = None
    user_id = None

    try:
        # 1. Authenticate connection
        if role == "host":
            # Host can authenticate with either device_id + auth_key, or JWT token
            if not device_id:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing device_id")
                return

            async with async_session_maker() as session:
                stmt = select(Device).where(Device.id == device_id)
                res = await session.execute(stmt)
                device = res.scalar_one_or_none()

                if not device:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Device not found")
                    return

                if auth_key and device.auth_key != auth_key:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid auth key")
                    return
                elif token:
                    payload = decode_token(token)
                    if not payload or payload.get("sub") != device.user_id:
                        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                        return

                user_id = device.user_id
                device.status = "ONLINE"
                await session.commit()

            host_id = device_id
            await manager.register_host(host_id, user_id, websocket, device_name=device.device_name)
            await websocket.send_text(json.dumps({
                "type": "registered",
                "role": "host",
                "device_id": host_id,
            }))

        else:
            # Android Client authentication via JWT
            if not token:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing JWT token")
                return

            payload = decode_token(token)
            if not payload or "sub" not in payload:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid JWT token")
                return

            user_id = payload["sub"]
            client_id = f"client_{user_id}_{id(websocket)}"
            await manager.register_client(client_id, user_id, websocket)
            await websocket.send_text(json.dumps({
                "type": "registered",
                "role": "client",
                "client_id": client_id,
            }))

        # 2. Main message loop
        while True:
            text = await websocket.receive_text()
            data = json.loads(text)
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            # Session Request from Client to Host
            if msg_type == "session_request":
                target_device_id = data.get("target_device_id")
                session_id = data.get("session_id")
                if not manager.is_host_online(target_device_id):
                    await websocket.send_text(json.dumps({
                        "type": "session_error",
                        "session_id": session_id,
                        "error": "Target laptop is offline.",
                    }))
                    continue

                # Forward request to the host with dynamic display & quality metrics
                await manager.send_to_host(target_device_id, {
                    "type": "incoming_session_request",
                    "session_id": session_id,
                    "client_id": client_id,
                    "user_id": user_id,
                    "client_info": data.get("client_info", "Android Client"),
                    "width": data.get("width"),
                    "height": data.get("height"),
                    "quality": data.get("quality"),
                })

            elif msg_type == "set_quality":
                sess_id = data.get("session_id")
                sess = manager.sessions.get(sess_id)
                if sess:
                    await manager.send_to_host(sess["host_id"], data)

            # Session Response from Host
            elif msg_type == "session_response":
                sess_id = data.get("session_id")
                target_client_id = data.get("client_id")
                accepted = data.get("accepted", False)

                if accepted:
                    manager.start_session(sess_id, host_id, target_client_id, user_id)
                    try:
                        async with async_session_maker() as session:
                            audit = AuditLog(
                                user_id=user_id,
                                device_id=host_id,
                                action="SESSION_STARTED",
                                details=f"Remote session started (session_id={sess_id})",
                            )
                            session.add(audit)
                            await session.commit()
                    except Exception as ex:
                        logger.error(f"Error logging session start: {ex}")

                await manager.send_to_client(target_client_id, {
                    "type": "session_response",
                    "session_id": sess_id,
                    "accepted": accepted,
                    "reason": data.get("reason"),
                })

            # WebRTC SDP Offer (typically from Client or Host)
            elif msg_type == "webrtc_offer":
                sdp = data.get("sdp")
                sess_id = data.get("session_id")
                sess = manager.sessions.get(sess_id)
                if sess:
                    if role == "client":
                        await manager.send_to_host(sess["host_id"], {
                            "type": "webrtc_offer",
                            "session_id": sess_id,
                            "sdp": sdp,
                        })
                    else:
                        await manager.send_to_client(sess["client_id"], {
                            "type": "webrtc_offer",
                            "session_id": sess_id,
                            "sdp": sdp,
                        })

            # WebRTC SDP Answer
            elif msg_type == "webrtc_answer":
                sdp = data.get("sdp")
                sess_id = data.get("session_id")
                sess = manager.sessions.get(sess_id)
                if sess:
                    if role == "host":
                        await manager.send_to_client(sess["client_id"], {
                            "type": "webrtc_answer",
                            "session_id": sess_id,
                            "sdp": sdp,
                        })
                    else:
                        await manager.send_to_host(sess["host_id"], {
                            "type": "webrtc_answer",
                            "session_id": sess_id,
                            "sdp": sdp,
                        })

            # ICE Candidate Exchange
            elif msg_type == "ice_candidate":
                candidate = data.get("candidate")
                sess_id = data.get("session_id")
                sess = manager.sessions.get(sess_id)
                if sess:
                    dest = sess["host_id"] if role == "client" else sess["client_id"]
                    send_fn = manager.send_to_host if role == "client" else manager.send_to_client
                    await send_fn(dest, {
                        "type": "ice_candidate",
                        "session_id": sess_id,
                        "candidate": candidate,
                    })

            # End Session
            elif msg_type == "session_end":
                sess_id = data.get("session_id")
                ended = manager.end_session(sess_id)
                if ended:
                    reason = data.get("reason", "User ended session")
                    try:
                        async with async_session_maker() as session:
                            audit = AuditLog(
                                user_id=ended.get("user_id"),
                                device_id=ended.get("host_id"),
                                action="SESSION_STOPPED",
                                details=f"Remote session stopped ({reason}): session_id={sess_id}",
                            )
                            session.add(audit)
                            await session.commit()
                    except Exception as ex:
                        logger.error(f"Error logging session stop: {ex}")

                    await manager.send_to_host(ended["host_id"], {
                        "type": "session_terminated",
                        "session_id": sess_id,
                        "reason": reason,
                    })
                    await manager.send_to_client(ended["client_id"], {
                        "type": "session_terminated",
                        "session_id": sess_id,
                        "reason": reason,
                    })

            # Generic session message forwarding (desktop_frame, mouse, keyboard, etc.)
            else:
                if role == "host" and host_id:
                    fwd_sid = manager.host_to_session.get(host_id)
                    if fwd_sid and fwd_sid in manager.sessions:
                        await manager.send_to_client(manager.sessions[fwd_sid]["client_id"], data)
                    else:
                        # Direct message routing outside video streaming session (e.g. file operations)
                        target_client = data.get("client_id")
                        if target_client:
                            await manager.send_to_client(target_client, data)
                        else:
                            meta = manager.host_meta.get(host_id)
                            if meta:
                                u_id = meta.get("user_id")
                                if u_id and u_id in manager.user_clients:
                                    for cid in manager.user_clients[u_id]:
                                        await manager.send_to_client(cid, data)
                elif role == "client" and client_id:
                    fwd_sid = manager.client_to_session.get(client_id)
                    if fwd_sid and fwd_sid in manager.sessions:
                        await manager.send_to_host(manager.sessions[fwd_sid]["host_id"], data)
                    else:
                        # Client sending to host directly (e.g. file manager requests)
                        target = data.get("target_device_id") or data.get("device_id")
                        if target and manager.is_host_online(target):
                            meta = manager.host_meta.get(target)
                            if meta and meta.get("user_id") == user_id:
                                data["client_id"] = client_id
                                await manager.send_to_host(target, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {role} (host_id={host_id}, client_id={client_id})")
    except Exception as e:
        logger.error(f"WebSocket unexpected error: {e}")
    finally:
        if role == "host" and host_id:
            await manager.disconnect_host(host_id)
            async with async_session_maker() as session:
                stmt = select(Device).where(Device.id == host_id)
                res = await session.execute(stmt)
                dev = res.scalar_one_or_none()
                if dev:
                    dev.status = "OFFLINE"
                    await session.commit()
        elif role == "client" and client_id:
            await manager.disconnect_client(client_id)
