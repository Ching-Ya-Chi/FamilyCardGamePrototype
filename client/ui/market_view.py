import tkinter as tk
import threading
from client.ui.pygame_scene_manager import switch_scene, is_running, start_manager
from client.ui.scene_registry import register_all_scenes
from client.ui.Lobby_Scene import START_BATTLE, GOTO_DECK, GOTO_MARKET, GOTO_LOBBY, GOTO_SETTINGS

class MarketView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text='Marketplace (Pygame)').pack(pady=20)
        btn_back = tk.Button(self, text='Back to Lobby (Tk)', 
                             command=lambda: controller.show_frame('LobbyView'))
        btn_back.pack()

    def on_show(self):
        try:
            if not is_running():
                self._scene_stop = threading.Event()
                register_all_scenes(self.controller.user)
                # 簡化的 handler，實際專案建議封裝
                def _scene_event_handler(state, scene_name=None):
                    try:
                        mapping = {
                            START_BATTLE: 'BattleView',
                            GOTO_DECK: 'DeckBuilderView',
                            GOTO_MARKET: 'MarketView',
                            GOTO_LOBBY: 'LobbyView',
                            GOTO_SETTINGS: 'LoginView',
                        }
                        target = mapping.get(state)
                        if target:
                            self.controller.after(0, lambda: self.controller.show_frame(target))
                    except Exception as e:
                        print('Handler Error:', e)
                
                start_manager(self._scene_stop, size=(1280, 720), event_handler=_scene_event_handler)

            # 切換場景到 market，並傳入 user
            switch_scene('market', user_data=self.controller.user)
        except Exception as e:
            print('Failed to switch to market scene:', e)
