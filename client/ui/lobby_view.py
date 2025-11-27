# client/ui/lobby_view.py

import tkinter as tk
from tkinter import messagebox
import threading
from client.ui.connection_dialog import ConnectionDialog # 新增
from src.p2p_network.battle import Battle # 引入 P2P Battle
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
        """處理 P2P 連線並啟動 BattleScene"""
        # 1. 彈出對話框選擇 Host/Join
        dialog = ConnectionDialog(self)
        if not dialog.result:
            return # 取消

        mode = dialog.result[0]
        
        # 2. 準備牌組 (從 DB 讀取並轉換成 Battle 需要的 Card 物件)
        uid = self.controller.user.get('user_id', 1)
        deck_ids = db_service.get_user_deck(uid)
        if not deck_ids: deck_ids = [1]*10 # 預設牌組
        
        # 轉換: Battle 需要 List[Card]
        all_cards = db_service.get_all_cards_dict()
        battle_deck = []
        for cid in deck_ids:
            c_data = all_cards.get(cid)
            if c_data:
                # 注意：Battle 的 Card 類別可能跟 DB 欄位名稱不同，需適配
                # 假設 src.common.models.Card 接受 id, name, cost, attack, health
                battle_deck.append(Card(
                    id=c_data['id'],
                    name=c_data['name'],
                    cost=c_data['cost'],
                    attack=c_data['attack'],
                    health=c_data['health']
                ))

        # 3. 定義回呼函數 (當收到對手動作時)
        def on_remote(intent):
            print(f"[P2P] Received: {intent}")
            # 這裡需要通知 BattleScene 更新畫面
            # 但 BattleScene 在 Pygame 執行緒，這裡在 Socket 執行緒
            # 我們需要一個機制來傳遞，或者讓 BattleScene 自己去 polling Battle 物件
            pass 

        # 4. 建立 Battle 實例
        battle = Battle(battle_deck, on_remote_intent=on_remote)
        
        # 將 battle 物件存到 controller 以便傳給 Scene
        self.controller.p2p_battle = battle 

        # 5. 開始連線 (這會阻塞，所以要用 Thread)
        import threading
        def connect_task():
            try:
                if mode == "HOST":
                    port = dialog.result[1]
                    print(f"Waiting for peer on port {port}...")
                    battle.start_as_responder(port)
                else:
                    ip, port = dialog.result[1], dialog.result[2]
                    print(f"Connecting to {ip}:{port}...")
                    battle.start_as_initiator(ip, port)
                
                print("P2P Connected!")
                # 連線成功後，切換到 BattleView
                self.controller.after(0, lambda: self.controller.show_frame('BattleView'))
            except Exception as e:
                print(f"Connection failed: {e}")

        threading.Thread(target=connect_task, daemon=True).start()

    def on_hide(self):
        """當離開此頁面時 (通常不需要特別停止 manager，因為我們希望背景保持流暢切換)"""
        pass

    def logout(self):
        self.controller.user = {'user_id': None, 'username': None}
        self.controller.show_frame('LoginView')