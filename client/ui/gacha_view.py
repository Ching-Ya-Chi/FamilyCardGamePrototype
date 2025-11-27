import tkinter as tk
import threading
from client.ui.pygame_scene_manager import switch_scene, is_running, start_manager
from client.ui.scene_registry import register_all_scenes
from client.ui.Lobby_Scene import START_BATTLE, GOTO_DECK, GOTO_MARKET, GOTO_LOBBY, GOTO_SETTINGS

class GachaView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        # 簡單的 Tkinter 介面，主要依賴 Pygame 顯示
        tk.Label(self, text='Gacha System (Pygame Active)').pack(pady=20)
        
        btn_back = tk.Button(self, text='Back to Lobby (Tk)', 
                             command=lambda: controller.show_frame('LobbyView'))
        btn_back.pack()

    def on_show(self):
        """切換到 Gacha Scene"""
        try:
            if not is_running():
                # 防護性啟動 Manager (通常不會跑到這)
                self._scene_stop = threading.Event()
                register_all_scenes(self.controller.user)
                
                def _scene_event_handler(state, scene_name=None):
                    try:
                        mapping = {
                            START_BATTLE: 'BattleView',
                            GOTO_DECK: 'DeckBuilderView',
                            GOTO_MARKET: 'MarketView',
                            GOTO_LOBBY: 'LobbyView',
                            GOTO_SETTINGS: 'LoginView',
                            # 注意：GOTO_GACHA 是從 Lobby 觸發的，這裡不需要 map Gacha->Gacha
                        }
                        target = mapping.get(state)
                        if target:
                            self.controller.after(0, lambda: self.controller.show_frame(target))
                    except Exception as e:
                        print('Handler Error:', e)
                
                start_manager(self._scene_stop, size=(1280, 720), event_handler=_scene_event_handler)

            # 傳入 user 資料以便 engine 知道扣誰的錢
            switch_scene('gacha', user_data=self.controller.user)
        except Exception as e:
            print('Failed to switch to gacha scene:', e)