"""Simple P2P peer connection and handshake using newline-delimited JSON messages.

Handshake (happy path):
- Initiator connects to responder and sends a P2P_SEED_EXCHANGE message with a chosen seed.
- Responder replies with P2P_SEED_ACK {accepted: true}.

After handshake both sides initialize RNGManager with the agreed seed and exchange INTENT messages.
"""
import socket
import threading
from typing import Callable, Optional
import time

from src.common import protocol
from src.p2p_network.rng_manager import RNGManager


class P2PPeer:
    def __init__(self, on_intent: Callable[[dict], None]):
        self.sock: Optional[socket.socket] = None
        self.rng: Optional[RNGManager] = None
        self.on_intent = on_intent
        self._recv_thread: Optional[threading.Thread] = None
        self._running = False

    def _recv_loop(self):
        buf = b""
        try:
            while self._running:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line:
                        continue
                    msg = protocol.unpack_message(line.decode('utf-8'))
                    action = msg.get('action')
                    payload = msg.get('payload', {})
                    if action == protocol.P2P_INTENT:
                        # call the intent handler
                        try:
                            self.on_intent(payload)
                        except Exception:
                            pass
                    elif action == protocol.P2P_SEED_EXCHANGE:
                        seed = int(payload.get('seed'))
                        # accept and reply
                        self.rng = RNGManager(seed)
                        ack = protocol.pack_message(protocol.P2P_SEED_ACK, {'accepted': True})
                        self.send_raw(ack)
                    elif action == protocol.P2P_SEED_ACK:
                        # initiator receives ACK
                        # payload {accepted: bool}
                        accepted = payload.get('accepted', False)
                        if not accepted:
                            # For prototype we won't handle rejection further
                            pass
                    else:
                        # ignore other messages for now
                        pass
        except Exception:
            pass
        finally:
            self._running = False
            try:
                self.sock.close()
            except Exception:
                pass

    def send_raw(self, msg: str):
        if not self.sock:
            raise RuntimeError('not connected')
        self.sock.sendall((msg + '\n').encode('utf-8'))

    def send_intent(self, intent: dict):
        msg = protocol.pack_message(protocol.P2P_INTENT, intent)
        self.send_raw(msg)

    def connect(self, peer_ip: str, peer_port: int, seed: Optional[int] = None, timeout: float = 5.0):
        """Initiator: connect to peer and perform seed exchange.

        seed: if None, choose time-based seed.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((peer_ip, int(peer_port)))
        s.settimeout(None)
        self.sock = s
        self._running = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

        if seed is None:
            seed = int(time.time())

        # send seed
        msg = protocol.pack_message(protocol.P2P_SEED_EXCHANGE, {'seed': seed})
        self.send_raw(msg)

        # wait a short while for ack and rng to be set by recv
        time.sleep(0.1)
        if self.rng is None:
            # if the other side didn't exchange, set rng ourselves (initiator's view)
            self.rng = RNGManager(seed)

        return True

    def accept(self, listen_port: int, timeout: Optional[float] = None):
        """Responder: listen for a connection and accept one peer.

        This will block until a connection is accepted (or timeout).
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', listen_port))
        s.listen(1)
        s.settimeout(timeout)
        conn, addr = s.accept()
        s.close()
        self.sock = conn
        self._running = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()
        return addr

    def close(self):
        self._running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
