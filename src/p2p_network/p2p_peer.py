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
        # 新增：儲存自己的 ID，用於驗證
        self.my_user_id = None 
        # 新增：連線狀態回報 (None=未定, True=成功, False=失敗)
        self.handshake_status = None 
        self.failure_reason = ""


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
                        # --- 修改：接收種子與對方 ID ---
                        seed = int(payload.get('seed'))
                        remote_uid = payload.get('user_id')
                        
                        # 檢查 ID 是否衝突
                        if str(remote_uid) == str(self.my_user_id):
                            print(f"[P2P] Rejecting self-connection from user {remote_uid}")
                            # 回傳拒絕訊息
                            ack = protocol.pack_message(protocol.P2P_SEED_ACK, {'accepted': False, 'reason': 'SAME_USER'})
                            self.send_raw(ack)
                            self._running = False # 斷開
                            self.sock.close()
                            return

                        # ID 不同，接受連線
                        self.rng = RNGManager(seed)
                        ack = protocol.pack_message(protocol.P2P_SEED_ACK, {'accepted': True})
                        self.send_raw(ack)
                        self.handshake_status = True
                    elif action == protocol.P2P_SEED_ACK:
                        accepted = payload.get('accepted', False)
                        if not accepted:
                            reason = payload.get('reason', 'Unknown')
                            print(f"[P2P] Handshake rejected: {reason}")
                            self.handshake_status = False
                            self.failure_reason = reason
                            self._running = False
                            self.sock.close()
                        else:
                            self.handshake_status = True
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

    def connect(self, peer_ip: str, peer_port: int, user_id: int, seed: Optional[int] = None, timeout: float = 5.0):
        """Initiator: connect to peer and perform seed exchange.

        seed: if None, choose time-based seed.
        """
        self.my_user_id = user_id
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((peer_ip, int(peer_port)))
        except OSError:
            # 連線失敗 (沒人聽)，回傳 False
            return False
        s.settimeout(None)
        self.sock = s
        self._running = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

        if seed is None:
            seed = int(time.time())

        # 發起者決定種子，所以必須在這裡立刻初始化
        self.rng = RNGManager(seed)

        # 修改：傳送 user_id
        msg = protocol.pack_message(protocol.P2P_SEED_EXCHANGE, {'seed': seed, 'user_id': user_id})
        self.send_raw(msg)

        # 等待 Handshake 結果 (最多等 2 秒)
        start_wait = time.time()
        while self.handshake_status is None:
            time.sleep(0.1)
            if time.time() - start_wait > 2.0:
                print("[P2P] Handshake timeout")
                self.close()
                return False
        
        return self.handshake_status

    def accept(self, listen_port: int,  user_id: int, timeout: Optional[float] = None):
        """Responder: Wait for connection."""
        self.my_user_id = user_id
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            s.bind(('0.0.0.0', listen_port))
            s.listen(1)
            s.settimeout(timeout)
            print(f"[P2P] Listening on port {listen_port}...")
            conn, addr = s.accept()
        except Exception as e:
            s.close()
            raise e
            
        s.close() # 停止監聽
        self.sock = conn
        self._running = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()
        
        # Responder 等待收到 SEED_EXCHANGE
        # 因為邏輯在 _recv_loop，這裡只需回傳 addr
        return addr

    def close(self):
        self._running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
