import argparse
import subprocess
import sys
import time
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_PORT = 5000

def get_env():
    """設定 PYTHONPATH 確保能抓到 src"""
    env = os.environ.copy()
    env_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env_pythonpath if env_pythonpath else '')
    return env

def kill_process_on_port(port):
    """
    檢查指定 Port 是否被占用，若是則嘗試殺掉該進程。
    目前針對 Windows 優化 (因為你的環境是 Windows)。
    """
    print(f"檢查 Port {port} 是否被占用...")
    
    if sys.platform == "win32":
        try:
            # 1. 使用 netstat 找出占用 port 的 PID
            # -a: 顯示所有連線, -n: 數字形式, -o: 顯示 PID
            result = subprocess.run(
                ["netstat", "-ano"], 
                capture_output=True, text=True, shell=True
            )
            
            # 解析輸出找 PID
            # 格式範例:   TCP    0.0.0.0:5000           0.0.0.0:0              LISTENING       1234
            lines = result.stdout.splitlines()
            pids = set()
            for line in lines:
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    pids.add(pid)
            
            if not pids:
                print(f"Port {port} 目前空閒。")
                return

            # 2. 殺掉進程
            for pid in pids:
                print(f"發現 PID {pid} 占用 Port {port}，正在強制關閉...")
                subprocess.run(["taskkill", "/F", "/PID", pid], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"PID {pid} 已關閉。")
                
            # 稍微等待釋放
            time.sleep(1)
            
        except Exception as e:
            print(f"無法自動關閉占用 Port 的進程: {e}")
            print("請手動關閉或是忽略此錯誤。")
    else:
        print("非 Windows 系統，跳過自動殺進程步驟 (請手動確認 Port 空閒)。")

def init_database():
    """執行 init_game_db.py 重置資料庫"""
    print("-" * 40)
    print("正在初始化資料庫 (init_game_db.py)...")
    cmd = [sys.executable, str(ROOT / 'scripts' / 'init_game_db.py')]
    # 使用 .run() 因為我們需要等待它完成才能繼續
    subprocess.run(cmd, cwd=str(ROOT), env=get_env(), check=True)
    print("資料庫初始化完成。")

def run_server():
    """啟動 Server (背景執行)"""
    print("-" * 40)
    print(f"正在啟動 Server (Port {SERVER_PORT})...")
    cmd = [sys.executable, str(ROOT / 'src' / 'server' / 'server_main.py')]
    # 使用 Popen 讓它在背景跑
    return subprocess.Popen(cmd, cwd=str(ROOT), env=get_env())

def run_client(username, user_id):
    """啟動 Client 並自動登入"""
    print(f"正在啟動 Client: {username} (ID: {user_id})...")
    cmd = [
        sys.executable, 
        str(ROOT / 'client' / 'main.py'),
        '--auto-username', username,
        '--auto-user-id', str(user_id)
    ]
    # 使用 Popen 讓它在背景跑
    return subprocess.Popen(cmd, cwd=str(ROOT), env=get_env())

def main():
    procs = []
    try:
        # 1. 檢查並清理 Port
        kill_process_on_port(SERVER_PORT)

        # 2. 初始化 DB
        init_database()

        # 3. 啟動 Server
        server_proc = run_server()
        procs.append(server_proc)
        
        # 等待 Server 啟動完畢 (給它 2 秒)
        time.sleep(2)

        # 4. 同時啟動兩個 Client
        # 根據 init_game_db.py: leo是ID 1, sam是ID 3
        p1 = run_client("leo", 1)
        procs.append(p1)
        
        # 稍微錯開一點點啟動時間，避免同時搶焦點
        time.sleep(0.5)
        
        p2 = run_client("sam", 3)
        procs.append(p2)

        print("-" * 40)
        print("開發環境啟動完畢！")
        print("請保持此視窗開啟。按下 Ctrl+C 可同時關閉所有視窗。")
        print("-" * 40)

        # 監控子進程
        while True:
            # 檢查是否所有子進程都還活著，如果有任何一個死了 (例如 Server 崩潰)，通常也要結束
            if server_proc.poll() is not None:
                print("Server 已停止，結束腳本。")
                break
            
            # 檢查是否有 Client 關閉，如果兩個 Client 都關了，也可以結束腳本
            clients_alive = [p.poll() is None for p in procs[1:]]
            if not any(clients_alive):
                print("所有 Client 已關閉，結束腳本。")
                break
                
            time.sleep(1)

    except KeyboardInterrupt:
        print('\n偵測到中斷訊號 (Ctrl+C)，正在關閉所有程式...')
    finally:
        for p in procs:
            try:
                if p.poll() is None:
                    p.terminate()
            except Exception:
                pass
        print("清理完成。Bye!")

if __name__ == '__main__':
    main()
