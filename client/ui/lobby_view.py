# client/ui/lobby_view.py

import tkinter as tk
from tkinter import messagebox
import threading

# 引入剛剛分出去的 Scene 裡的常數，保持一致性
from client.ui.Lobby_Scene import (
    START_BATTLE, GOTO_DECK, GOTO_MARKET, GOTO_LOBBY, GOTO_SETTINGS
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
            register_all_scenes(self.controller.user)
            
            # 定義當 Pygame 按鈕被點擊時，Tkinter 要做什麼
            def _scene_event_handler(state, scene_name=None):
                try:
                    mapping = {
                        START_BATTLE: 'BattleView',
                        GOTO_DECK: 'DeckBuilderView',
                        GOTO_MARKET: 'MarketView',
                        GOTO_LOBBY: 'LobbyView', # 自己
                        GOTO_SETTINGS: 'LoginView',
                    }
                    target = mapping.get(state)
                    if target:
                        # 必須透過 after 回到主執行緒操作 UI
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

    def on_hide(self):
        """當離開此頁面時 (通常不需要特別停止 manager，因為我們希望背景保持流暢切換)"""
        pass

    def logout(self):
        self.controller.user = {'user_id': None, 'username': None}
        self.controller.show_frame('LoginView')