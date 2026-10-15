import base64
import hashlib
import hmac
import time
from typing import List
from backend.app.config import settings
from backend.app.schemas import IceServerConfig


def generate_ice_servers(user_id: str = "anonymous") -> List[IceServerConfig]:
    """
    Builds the ICE servers list, providing STUN and ephemeral TURN credentials
    compliant with RFC 5766 and coturn REST API.
    """
    servers: List[IceServerConfig] = []

    # STUN servers (always available)
    servers.append(IceServerConfig(urls=settings.STUN_SERVERS))

    # TURN server (if configured)
    if settings.TURN_SERVER_URL and settings.TURN_SECRET:
        timestamp = int(time.time()) + settings.TURN_TTL_SECONDS
        turn_username = f"{timestamp}:{user_id}"
        
        # Coturn HMAC-SHA1 secret authentication
        digest = hmac.new(
            settings.TURN_SECRET.encode("utf-8"),
            turn_username.encode("utf-8"),
            hashlib.sha1
        ).digest()
        turn_credential = base64.b64encode(digest).decode("utf-8")

        servers.append(
            IceServerConfig(
                urls=[
                    f"turn:{settings.TURN_SERVER_URL}?transport=udp",
                    f"turn:{settings.TURN_SERVER_URL}?transport=tcp",
                ],
                username=turn_username,
                credential=turn_credential,
            )
        )

    return servers
