import json
import logging
from typing import Dict, Optional, Set
from fastapi import WebSocket
from datetime import datetime, timezone

logger = logging.getLogger("remodesk.signaling")


class ConnectionManager:
    def __init__(self):
        # host_id -> WebSocket (Windows Host Agents)
        self.active_hosts: Dict[str, WebSocket] = {}
        # host_id -> metadata (user_id, device_name, status)
        self.host_meta: Dict[str, dict] = {}
        
        # client_id -> WebSocket (Android Mobile Clients)
        self.active_clients: Dict[str, WebSocket] = {}
        # user_id -> Set[client_id]
        self.user_clients: Dict[str, Set[str]] = {}
        
        # active_sessions: session_id -> { "host_id": str, "client_id": str, "user_id": str, "started_at": str }
        self.sessions: Dict[str, dict] = {}
        # Mapping to find session by peer
        self.host_to_session: Dict[str, str] = {}
        self.client_to_session: Dict[str, str] = {}

    async def register_host(self, host_id: str, user_id: str, websocket: WebSocket, device_name: str = "Windows Laptop"):
        self.active_hosts[host_id] = websocket
        self.host_meta[host_id] = {
            "user_id": user_id,
            "device_name": device_name,
            "status": "ONLINE",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Host registered: {host_id} (user: {user_id}, name: {device_name})")
        # Notify user's mobile clients that this host is online
        await self.broadcast_device_status(user_id, host_id, "ONLINE")

    async def register_client(self, client_id: str, user_id: str, websocket: WebSocket):
        self.active_clients[client_id] = websocket
        if user_id not in self.user_clients:
            self.user_clients[user_id] = set()
        self.user_clients[user_id].add(client_id)
        logger.info(f"Client registered: {client_id} (user: {user_id})")

    async def disconnect_host(self, host_id: str):
        if host_id in self.active_hosts:
            del self.active_hosts[host_id]
            meta = self.host_meta.pop(host_id, None)
            if meta:
                user_id = meta.get("user_id")
                await self.broadcast_device_status(user_id, host_id, "OFFLINE")
            
            # End any ongoing session
            session_id = self.host_to_session.pop(host_id, None)
            if session_id and session_id in self.sessions:
                sess = self.sessions.pop(session_id)
                client_id = sess.get("client_id")
                self.client_to_session.pop(client_id, None)
                await self.send_to_client(client_id, {
                    "type": "session_terminated",
                    "session_id": session_id,
                    "reason": "Host agent disconnected",
                })
            logger.info(f"Host disconnected: {host_id}")

    async def disconnect_client(self, client_id: str):
        if client_id in self.active_clients:
            del self.active_clients[client_id]
            for user_id, clients in list(self.user_clients.items()):
                clients.discard(client_id)
                if not clients:
                    del self.user_clients[user_id]

            session_id = self.client_to_session.pop(client_id, None)
            if session_id and session_id in self.sessions:
                sess = self.sessions.pop(session_id)
                host_id = sess.get("host_id")
                self.host_to_session.pop(host_id, None)
                if host_id in self.host_meta:
                    self.host_meta[host_id]["status"] = "ONLINE"
                await self.send_to_host(host_id, {
                    "type": "session_terminated",
                    "session_id": session_id,
                    "reason": "Client disconnected",
                })
            logger.info(f"Client disconnected: {client_id}")

    async def broadcast_device_status(self, user_id: str, host_id: str, status: str):
        if user_id in self.user_clients:
            msg = {
                "type": "device_status_update",
                "device_id": host_id,
                "status": status,
            }
            for client_id in self.user_clients[user_id]:
                await self.send_to_client(client_id, msg)

    async def send_to_host(self, host_id: str, message: dict) -> bool:
        ws = self.active_hosts.get(host_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Error sending message to host {host_id}: {e}")
        return False

    async def send_to_client(self, client_id: str, message: dict) -> bool:
        ws = self.active_clients.get(client_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
        return False

    def is_host_online(self, host_id: str) -> bool:
        return host_id in self.active_hosts

    def start_session(self, session_id: str, host_id: str, client_id: str, user_id: str):
        self.sessions[session_id] = {
            "host_id": host_id,
            "client_id": client_id,
            "user_id": user_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        self.host_to_session[host_id] = session_id
        self.client_to_session[client_id] = session_id
        if host_id in self.host_meta:
            self.host_meta[host_id]["status"] = "IN_SESSION"

    def end_session(self, session_id: str) -> Optional[dict]:
        sess = self.sessions.pop(session_id, None)
        if sess:
            host_id = sess.get("host_id")
            client_id = sess.get("client_id")
            self.host_to_session.pop(host_id, None)
            self.client_to_session.pop(client_id, None)
            if host_id in self.host_meta:
                self.host_meta[host_id]["status"] = "ONLINE"
        return sess


manager = ConnectionManager()
