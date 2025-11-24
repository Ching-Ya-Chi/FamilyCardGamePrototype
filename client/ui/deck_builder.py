import tkinter as tk
import threading
from .lobby_view import START_BATTLE, GOTO_DECK, GOTO_MARKET, GOTO_LOBBY, GOTO_SETTINGS
from client.ui.pygame_scene_manager import start_manager, switch_scene, is_running
from client.ui.scene_registry import register_all_scenes

class DeckBuilderView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        tk.Label(self, text='Deck Builder (Pygame)').pack(pady=20)
        
        # 只需要一個返回按鈕作為備用
        btn_back = tk.Button(self, text='Back to Lobby (Tk)', 
                             command=lambda: controller.show_frame('LobbyView'))
        btn_back.pack()

    def on_show(self):
        """切換到 Deck Builder Scene"""
        try:
            if not is_running():
                # 防護性啟動
                self._scene_stop = threading.Event()
                register_all_scenes(self.controller.user)
                # ... (略過 handler 定義，與 LobbyView 相同) ...
                # 建議將 handler 抽離到 utils 避免重複代碼，這裡簡略
                
            # 切換場景，並傳入 user 資料
            switch_scene('deck', user_data=self.controller.user)
        except Exception as e:
            print('Failed to switch to deck scene:', e)