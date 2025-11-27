# client/ui/lobby_view.py

import tkinter as tk
from tkinter import messagebox
import threading
from src.p2p_network.battle import Battle,P2PPeer # 引入 P2P Battle
from client.services.game_db_service import service as db_service # 讀牌組用
from src.common.models import Card # 用來轉換牌組格式

# 引入剛剛分出去的 Scene 裡的常數，保持一致性
from client.ui.Lobby_Scene import (
    START_BATTLE, GOTO_DECK, GOTO_MARKET, GOTO_LOBBY, GOTO_SETTINGS, GOTO_GACHA
)
from client.ui.pygame_scene_manager import start_manager, switch_scene, is_running
from client.ui.scene_registry import register_all_scenes
from client.services.game_db_service import service as db_service

class LobbyView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Tkinter 的介面可以用於 Debug 或作為後備選項
        lbl = tk.Label(self, text='Lobby Controller', font=('TkDefaultFont', 16))
        lbl.pack(pady=10)

        self.user_label = tk.Label(self, text='Loading...')
        self.user_label.pack()

        btn_logout = tk.Button(self, text='Logout', command=self.logout)
        btn_logout.pack(pady=20)

    def on_show(self):
        """當切換到此頁面時，啟動 Pygame Lobby 場景"""
        #  獲取當前 user_id
        current_user = self.controller.user
        uid = current_user.get('user_id')

        # ---從 DB 撈取最新資料 ---
        if uid:
            fresh_data = db_service.get_user_fresh_data(uid)
            if fresh_data:
                # 更新 Controller 中的全域變數
                self.controller.user['gold'] = fresh_data['gold']
                self.controller.user['gems'] = fresh_data['gems']
                # 也可以順便更新 username 以防萬一
                self.controller.user['username'] = fresh_data['username']
                print(f"[LobbyView] Data refreshed. Gold: {fresh_data['gold']}")

        # 1. 更新 Tkinter 上的文字
        user = self.controller.user or {}
        self.user_label.config(text=f"User: {user.get('username')} (Gold: {user.get('gold')})")
        # 2. 確保註冊場景 (即使 is_running 是 True，也重新註冊一次比較保險，雖然有點重複但安全)
        # 注意：register_scene 內部只是更新 dict，開銷很小
        try:
            register_all_scenes(self.controller.user)
        except Exception as e:
            print(f"Register scenes warning: {e}")

        # 3. 確保 Pygame Scene Manager 正在運行
        if not is_running():
            self._scene_stop = threading.Event()
            
            def _scene_event_handler(state, scene_name=None):
                if state == START_BATTLE:
                    # 攔截：不直接跳轉，先回到主執行緒處理連線
                    self.controller.after(0, self.start_p2p_battle)
                    return

                try:
                    mapping = {
                        # START_BATTLE 已經被上面攔截了，這裡可以拿掉或留著當備用
                        GOTO_DECK: 'DeckBuilderView',
                        GOTO_MARKET: 'MarketView',
                        GOTO_LOBBY: 'LobbyView',
                        GOTO_SETTINGS: 'LoginView',
                        'GOTO_GACHA': 'GachaView',
                    }
                    target = mapping.get(state)
                    if target:
                        self.controller.after(0, lambda: self.controller.show_frame(target))
                except Exception as e:
                    print('Handler Error:', e)

            start_manager(self._scene_stop, size=(1280, 720), event_handler=_scene_event_handler)

        # 4. 命令 SceneManager 切換到 'lobby'
        try:
            print(f"Switching to lobby scene with user: {user.get('username')}") # Debug
            switch_scene('lobby', user_data=self.controller.user)
        except Exception as e:
            print(f"Failed to switch scene: {e}")

    def start_p2p_battle(self):
        """自動處理 P2P 連線：先嘗試 Join，失敗則 Host"""
        
        # 1. 取得使用者資料
        user = self.controller.user
        uid = user.get('user_id')
        if not uid:
            messagebox.showerror("Error", "User ID not found!")
            return

        # 2. 準備牌組 (與之前相同)
        deck_ids = db_service.get_user_deck(uid)
        if not deck_ids: deck_ids = [1]*10 
        
        all_cards = db_service.get_all_cards_dict()
        battle_deck = []
        for cid in deck_ids:
            c_data = all_cards.get(cid)
            if c_data:
                battle_deck.append(Card(
                    id=c_data['id'],
                    name=c_data['name'],
                    cost=c_data['cost'],
                    attack=c_data['attack'],
                    health=c_data['health'],
                    type='Minion',
                    rarity=c_data.get('rarity', 'Common')
                ))

        # 3. 建立回呼與物件
        def on_remote(intent):
            # 這裡之後可以對接 UI 更新
            pass 

        battle = Battle(battle_deck, on_remote_intent=on_remote)
        self.controller.p2p_battle = battle 

        # 4. 自動連線邏輯 (背景執行)
        def connect_task():
            target_ip = "127.0.0.1"
            target_port = 6001
            
            print(f"[P2P] Auto-connecting to {target_ip}:{target_port}...")
            
            # --- 嘗試 JOIN ---
            # start_as_initiator 內部會嘗試 socket.connect
            # 如果 Port 沒人聽，會回傳 False (在我們修改過的 p2p_peer.connect 中捕獲 OSError)
            # 如果有人聽，但 Handshake 發現 ID 相同，也會回傳 False
            
            is_connected = battle.start_as_initiator(target_ip, target_port, user_id=uid)
            
            if is_connected:
                print("[P2P] Joined existing room as Client.")
                self.controller.after(0, lambda: self.controller.show_frame('BattleView'))
            
            else:
                # 連線失敗原因分析
                reason = getattr(battle.peer, 'failure_reason', '')
                if reason == 'SAME_USER':
                    print("[P2P] Found room but it's SAME USER. Aborting.")
                    self.controller.after(0, lambda: messagebox.showwarning("Warning", "You cannot play against yourself!"))
                    battle.peer.close()
                    return

                # 如果不是因為帳號衝突，而是因為連不上 (OSError)，那就代表沒人開房
                # --- 改為 HOST ---
                print("[P2P] No room found (or connection failed). Starting Host...")
                try:
                    # 重新建立一個 peer (因為舊的 socket 可能已經髒了)
                    battle.peer = P2PPeer(battle._on_intent)
                    
                    # 開始監聽 (這會阻塞直到有人連入)
                    # 為了不讓 UI 完全卡死等待，這裡其實在 Thread 裡，所以可以阻塞
                    # 但最好給個提示正在等待
                    print(f"[P2P] Waiting for challenger on port {target_port}...")
                    
                    # 這裡我們可以先切換到 BattleView 顯示「等待中...」
                    # 但目前的 BattleView 是直接進遊戲，所以我們先在這裡等
                    
                    success = battle.start_as_responder(target_port, user_id=uid)
                    
                    if success:
                        print("[P2P] Client connected! Starting game.")
                        self.controller.after(0, lambda: self.controller.show_frame('BattleView'))
                    else:
                        print("[P2P] Host start failed (maybe handshake rejected).")
                        
                except OSError:
                    # Port 佔用嚴重錯誤
                    print("[P2P] Port 6001 is busy but connect failed. Zombie process?")
                    self.controller.after(0, lambda: messagebox.showerror("Error", "Port 6001 is busy."))

        threading.Thread(target=connect_task, daemon=True).start()

    def on_hide(self):
        """當離開此頁面時 (通常不需要特別停止 manager，因為我們希望背景保持流暢切換)"""
        pass

    def logout(self):
        self.controller.user = {'user_id': None, 'username': None}
        self.controller.show_frame('LoginView')