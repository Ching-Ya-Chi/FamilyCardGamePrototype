"""Shared JSON protocol helpers and message schemas.

This module defines canonical action names and tiny helper wrappers to pack/unpack
JSON messages used by the central server and the P2P battle peers.
"""

from typing import Any, Dict
import json
import time


# --- Server actions (Central Server API) ---
ACTION_LOGIN_REQUEST = "LOGIN_REQUEST"          # payload: {username, password}
ACTION_LOGIN_RESPONSE = "LOGIN_RESPONSE"        # payload: {ok: bool, user_id?, gold?, gems?, error?}

ACTION_MARKET_BUY = "MARKET_BUY"                # payload: {buyer_id, listing_id, quantity}
ACTION_MARKET_BUY_RESPONSE = "MARKET_BUY_RESPONSE"  # payload: {ok: bool, tx_id?, error?}

ACTION_MATCHMAKE_REQUEST = "MATCHMAKE_REQUEST"  # payload: {user_id}
ACTION_MATCHMAKE_RESPONSE = "MATCHMAKE_RESPONSE"# payload: {ok: bool, peer_ip?, peer_port?, error?}

ACTION_ERROR = "ERROR"                          # payload: {error: str}


# --- P2P actions (Direct Peer-to-Peer Battle Intents) ---
# Handshake
P2P_SEED_EXCHANGE = "SEED_EXCHANGE"            # payload: {seed: int}
P2P_SEED_ACK = "SEED_ACK"                      # payload: {accepted: bool}

# Game Logic Intents
P2P_INTENT = "INTENT"                          # payload: {action: <str>, args: {...}}

# Specific Intent Actions (used inside P2P_INTENT payload)
P2P_PLAY_CARD = "PLAY_CARD"                    # args: {card_id: int, index: int}
P2P_ATTACK = "ATTACK"                          # args: {attacker_idx: int, target_idx: int}
P2P_END_TURN = "END_TURN"                      # args: {}


def pack_message(action: str, payload: Dict[str, Any]) -> str:
    """Pack an action and payload to a compact JSON string ready to send."""
    msg = {
        "action": action,
        "payload": payload,
        "ts": int(time.time()),
    }
    return json.dumps(msg, separators=(",", ":"))


def unpack_message(raw: str) -> Dict[str, Any]:
    """Parse a JSON string (or bytes decoded to str) into a dict."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


# --- Helpful Builders ---

def build_login_request(username: str, password: str) -> str:
    return pack_message(ACTION_LOGIN_REQUEST, {"username": username, "password": password})

def build_market_buy(buyer_id: int, listing_id: int, quantity: int = 1) -> str:
    return pack_message(ACTION_MARKET_BUY, {"buyer_id": buyer_id, "listing_id": listing_id, "quantity": quantity})

def build_p2p_intent(intent_action: str, args: Dict[str, Any] = None) -> str:
    """Build a P2P intent message (e.g., telling the other player I played a card)."""
    if args is None:
        args = {}
    return pack_message(P2P_INTENT, {"action": intent_action, "args": args})