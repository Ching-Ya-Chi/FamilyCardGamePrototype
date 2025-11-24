"""Central server: handles LOGIN, MARKET_BUY, MATCHMAKE via newline-delimited JSON over TCP.

Run this with Python and point clients at port 5000.
It relies on a pre-existing database (created by scripts/init_game_db.py).
"""
import socket
import threading
import sys
from pathlib import Path
from typing import Tuple

# ensure project src is importable
HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

from src.common import protocol
# 假設你的 db.py 在 src/server/db.py 或根目錄，請依實際情況調整 import
# 如果 db.py 在根目錄，請改成: from db import Database
from src.server.database import Database 
from src.server.auth import verify_password 
from src.server.marketplace import buy_listing
from src.server.matchmaking import request_match


HOST = 'localhost'
PORT = 5000

# 【注意】請確認這裡的路徑指向你 init_game_db.py 產生的那個檔案
# 如果你的 game.db 在專案根目錄，請改為 parents[2] / "game.db"
DB_PATH = str(Path(__file__).resolve().parents[2] / "game.db")
print(f"[Server] Using Database: {DB_PATH}")


def send_msg(conn: socket.socket, msg: str) -> None:
    # newline-delimited framing
    conn.sendall((msg + "\n").encode("utf-8"))


def handle_client(conn: socket.socket, addr: Tuple[str, int], db: Database):
    print(f"client connected: {addr}")
    buffer = b""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line:
                    continue
                try:
                    msg = protocol.unpack_message(line.decode("utf-8"))
                except Exception as e:
                    send_msg(conn, protocol.pack_message(protocol.ACTION_ERROR, {"error": "invalid_json"}))
                    continue

                action = msg.get("action")
                payload = msg.get("payload", {})

                if action == protocol.ACTION_LOGIN_REQUEST:
                    username = payload.get("username")
                    password = payload.get("password")
                    c = db.conn.cursor()
                    # 這裡假設你的 users 表密碼欄位是 password_hash，或者是明碼 (視 init_db 寫法而定)
                    # 如果 init_db 存的是明碼，這裡比較時可能要調整
                    c.execute("SELECT id, password_hash, gold FROM users WHERE username = ?", (username,))
                    row = c.fetchone()

                    if row:
                    # 這裡會比對你輸入的密碼是否等於資料庫裡的 "1234"
                        if verify_password(row["password_hash"], password) or row["password_hash"] == password:
                        # 登入成功...
                            resp = {"ok": True, "user_id": row["id"], "gold": row["gold"]}
                            send_msg(conn, protocol.pack_message(protocol.ACTION_LOGIN_RESPONSE, resp))
                        else:
                            send_msg(conn, protocol.pack_message(protocol.ACTION_LOGIN_RESPONSE, {"ok": False, "error": "invalid_credentials"}))
                    else:
                        send_msg(conn, protocol.pack_message(protocol.ACTION_LOGIN_RESPONSE, {"ok": False, "error": "user_not_found"}))

                elif action == protocol.ACTION_MARKET_BUY:
                    buyer_id = payload.get("buyer_id")
                    listing_id = payload.get("listing_id")
                    quantity = int(payload.get("quantity", 1))
                    ok, tx_id, error = buy_listing(db, int(buyer_id), int(listing_id), quantity)
                    if ok:
                        send_msg(conn, protocol.pack_message(protocol.ACTION_MARKET_BUY_RESPONSE, {"ok": True, "tx_id": tx_id}))
                    else:
                        send_msg(conn, protocol.pack_message(protocol.ACTION_MARKET_BUY_RESPONSE, {"ok": False, "error": error}))

                elif action == protocol.ACTION_MATCHMAKE_REQUEST:
                    user_id = int(payload.get("user_id"))
                    listen_port = int(payload.get("listen_port", 6000))
                    result = request_match(user_id, addr, listen_port)
                    send_msg(conn, protocol.pack_message(protocol.ACTION_MATCHMAKE_RESPONSE, result))

                else:
                    send_msg(conn, protocol.pack_message(protocol.ACTION_ERROR, {"error": "unknown_action"}))

    except Exception as exc:
        print(f"client handler error {exc}")
    finally:
        conn.close()
        print(f"client disconnected: {addr}")


def run_server():
    print(f"Connecting to database at: {DB_PATH}")
    db = Database(DB_PATH)
    
    try:
        db.connect()
        print("Database connected successfully.")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(32)
    print(f"Server listening on {HOST}:{PORT}")

    try:
        while True:
            try:
                conn, addr = s.accept()
                # 建立執行緒處理客戶端
                t = threading.Thread(target=handle_client, args=(conn, addr, db), daemon=True)
                t.start()
                
            except OSError as e:
                # 這是最常見的錯誤 (例如 WinError 10054, 10038)
                # 我們只印出錯誤，但不跳出 while 迴圈
                print(f"[Warning] Accept failed (Connection Error): {e}")
                
            except Exception as e:
                # 捕捉其他所有未預期的錯誤，確保伺服器活著
                print(f"[Error] Unexpected server error: {e}")

    except KeyboardInterrupt:
        print("shutting down")
    finally:
        s.close()


if __name__ == "__main__":
    run_server()