import threading
from typing import Dict, Optional, Tuple

# Very small in-memory matchmaker for prototype
# It pairs two clients that call request_match. Each caller provides their listen_port
# so the server can exchange peer_ip and peer_port to the other client.

_queue = []
_lock = threading.Lock()


def request_match(user_id: int, client_addr: Tuple[str, int], listen_port: int) -> Dict[str, Optional[object]]:
    """Request a match. If another waiting player exists, return both endpoints.

    Returns a dict:
      {"status": "paired", "peer_ip": str, "peer_port": int, "peer_user_id": int}
    or
      {"status": "waiting"}
    """
    with _lock:
        if _queue:
            other = _queue.pop(0)
            # other: (user_id, ip, listen_port)
            other_user_id, other_ip, other_port = other
            # Return pairing info for caller: other user's ip/port
            return {"status": "paired", "peer_ip": other_ip, "peer_port": other_port, "peer_user_id": other_user_id}
        else:
            # push this caller to queue and return waiting
            _queue.append((user_id, client_addr[0], listen_port))
            return {"status": "waiting"}
