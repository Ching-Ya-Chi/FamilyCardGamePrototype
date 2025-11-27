import sys
import os
import time
import socket
import subprocess
from pathlib import Path

# 設定專案根目錄
ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "src" / "server" / "server_main.py"
CLIENT_SCRIPT = ROOT / "client" / "main.py"

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000

def is_port_open(host, port):
    """檢查指定 Port 是否有服務在運行"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)  # 設定超時，避免卡住
        result = s.connect_ex((host, port))
        return result == 0

def run():
    print("--- Card Game Prototype Launcher ---")
    
    # 設定環境變數，確保子進程能找到專案根目錄的模組
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    
    server_process = None
    client_process = None

    try:
        # 1. 檢查 Server 狀態
        if is_port_open(SERVER_HOST, SERVER_PORT):
            print(f"✅ 偵測到 Server 已在 {SERVER_HOST}:{SERVER_PORT} 運行中。")
        else:
            print(f"⚠️  Port {SERVER_PORT} 未被佔用，正在啟動本地 Server...")
            
            # 啟動 Server
            server_process = subprocess.Popen(
                [sys.executable, str(SERVER_SCRIPT)],
                env=env,
                cwd=str(ROOT) # 設定工作目錄為專案根目錄
            )
            
            # 等待幾秒讓 Server 初始化
            print("   等待 Server 啟動...")
            time.sleep(2)
            
            # 再次檢查確認是否啟動成功
            if is_port_open(SERVER_HOST, SERVER_PORT):
                print("✅ Server 啟動成功！")
            else:
                print("❌ Server 啟動似乎失敗，請檢查錯誤訊息。")
                # 雖然失敗但我們繼續嘗試開 Client，或許只是啟動慢

        # 2. 啟動 Client
        print("🚀 正在啟動 Client (main.py)...")
        client_process = subprocess.Popen(
            [sys.executable, str(CLIENT_SCRIPT)],
            env=env,
            cwd=str(ROOT)
        )

        print("\n程式運行中... (關閉 Client 視窗以結束此腳本)")
        
        # 3. 等待 Client 結束
        # 我們讓腳本停在這裡，直到 Client 視窗被關閉
        client_process.wait()
        print("\nClient 已關閉。")

    except KeyboardInterrupt:
        print("\n偵測到中斷訊號 (Ctrl+C)。")
    except Exception as e:
        print(f"\n發生未預期的錯誤: {e}")
    finally:
        # 4. 清理工作
        if server_process:
            print("正在關閉由腳本啟動的本地 Server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("Server 已關閉。")
        
        print("Bye!")

if __name__ == '__main__':
    run()