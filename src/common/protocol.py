"""Shared JSON protocol helpers and message schemas for server <-> client and P2P intents.

This module defines canonical action names and tiny helper wrappers to pack/unpack
JSON messages used by the central server and the P2P battle peers.

All messages are JSON objects with at least these fields:
  - action: string (action type)
  - payload: object (action-specific data)
  - ts: integer (unix timestamp) optional

We use JSON strings over TCP sockets for simplicity. Each TCP message should be
terminated by a newline ("\n") or framed with a length-prefix in production.
"""

from typing import Any, Dict
import json
import time


# --- Server actions (central server API)
ACTION_LOGIN_REQUEST = "LOGIN_REQUEST"          # payload: {username, password}
ACTION_LOGIN_RESPONSE = "LOGIN_RESPONSE"        # payload: {ok: bool, user_id?, error?}

ACTION_MARKET_BUY = "MARKET_BUY"                # payload: {buyer_id, listing_id, quantity}
ACTION_MARKET_BUY_RESPONSE = "MARKET_BUY_RESPONSE"  # payload: {ok: bool, tx_id?, error?}

ACTION_MATCHMAKE_REQUEST = "MATCHMAKE_REQUEST"  # payload: {user_id}
ACTION_MATCHMAKE_RESPONSE = "MATCHMAKE_RESPONSE"# payload: {ok: bool, peer_ip?, peer_port?, error?}

ACTION_ERROR = "ERROR"                          # payload: {error: str}


# --- P2P action names (in-game intents between peers)
P2P_SEED_EXCHANGE = "SEED_EXCHANGE"            # payload: {seed: int}
P2P_SEED_ACK = "SEED_ACK"                      # payload: {accepted: bool}

P2P_INTENT = "INTENT"                          # payload: {action: <str>, args: {...}}
P2P_STATE_SYNC = "STATE_SYNC"                  # payload: full state snapshot (used rarely)

P2P_PLAY_CARD = "PLAY_CARD"                    # intent: {card_idx:int}
P2P_ATTACK = "ATTACK"                          # intent: {attacker_idx:int, target_idx:int}


def pack_message(action: str, payload: Dict[str, Any]) -> str:
    """Pack an action and payload to a compact JSON string ready to send.

    Note: For TCP newline-delimited framing, append "\n" when sending.
    """
    msg = {
        "action": action,
        "payload": payload,
        "ts": int(time.time()),
    }
    return json.dumps(msg, separators=(",", ":"))


def unpack_message(raw: str) -> Dict[str, Any]:
    """Parse a JSON string (or bytes decoded to str) into a dict.

    Caller should validate `action` and `payload` contents.
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


# Helpful example builders
def build_login_request(username: str, password: str) -> str:
    return pack_message(ACTION_LOGIN_REQUEST, {"username": username, "password": password})


def build_market_buy(buyer_id: int, listing_id: int, quantity: int = 1) -> str:
    return pack_message(ACTION_MARKET_BUY, {"buyer_id": buyer_id, "listing_id": listing_id, "quantity": quantity})


def build_p2p_intent(action: str, args: Dict[str, Any]) -> str:
    return pack_message(P2P_INTENT, {"action": action, "args": args})


# Example quick validators (happy-path, for later expansion)
def is_server_action(d: Dict[str, Any]) -> bool:
    return d.get("action") in {
        ACTION_LOGIN_REQUEST, ACTION_LOGIN_RESPONSE,
        ACTION_MARKET_BUY, ACTION_MARKET_BUY_RESPONSE,
        ACTION_MATCHMAKE_REQUEST, ACTION_MATCHMAKE_RESPONSE,
        ACTION_ERROR,
    }


def is_p2p_action(d: Dict[str, Any]) -> bool:
    return d.get("action") in {P2P_SEED_EXCHANGE, P2P_SEED_ACK, P2P_INTENT, P2P_STATE_SYNC, P2P_PLAY_CARD, P2P_ATTACK}
