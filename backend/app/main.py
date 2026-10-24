import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from backend.app.config import settings
from backend.app.database import init_db, async_session_maker
from backend.app.auth import decode_token
from backend.app.models import Device, User
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
                elif role == "client" and client_id:
                    fwd_sid = manager.client_to_session.get(client_id)
                    if fwd_sid and fwd_sid in manager.sessions:
                        await manager.send_to_host(manager.sessions[fwd_sid]["host_id"], data)

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
