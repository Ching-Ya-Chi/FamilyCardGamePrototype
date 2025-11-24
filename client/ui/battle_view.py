import tkinter as tk
from tkinter import messagebox
from src.p2p_network.battle import Battle
from src.common.models import load_cards_from_file, Card
from pathlib import Path
import threading
import time

CARDS_PATH = str(Path(__file__).resolve().parents[2] / 'data' / 'cards.json')


class BattleView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        tk.Label(self, text='Battle').pack()

        self.txt = tk.Text(self, height=10)
        self.txt.pack(fill='x')

        btn_play = tk.Button(self, text='Play First Card', command=self.play_first)
        btn_play.pack(pady=4)

        btn_back = tk.Button(self, text='Back to Lobby', command=self.back_to_lobby)
        btn_back.pack(pady=4)

        self.battle: Battle = None
        # load_cards_from_file returns Card instances; accept either dicts or Card objects
        loaded = load_cards_from_file(CARDS_PATH).values()
        self.local_deck = [c if isinstance(c, Card) else Card.from_dict(c) for c in loaded]

    def start_as_initiator(self, peer_ip, peer_port):
        # start battle as initiator (connects to peer and draws hand)
        def _start():
            self.append('Connecting to peer...')
            try:
                self.battle = Battle(self.local_deck.copy(), on_remote_intent=self.on_remote)
                self.battle.start_as_initiator(peer_ip, peer_port)
                self.append('Connected and opening hand drawn.')
                self.append(str(self.battle.get_state()))
            except Exception as e:
                self.append('Error: ' + str(e))
        threading.Thread(target=_start, daemon=True).start()

    def start_as_responder(self, listen_port=6001):
        def _start():
            self.append('Waiting for incoming peer...')
            try:
                self.battle = Battle(self.local_deck.copy(), on_remote_intent=self.on_remote)
                self.battle.start_as_responder(listen_port)
                self.append('Peer connected and opening hand drawn.')
                self.append(str(self.battle.get_state()))
            except Exception as e:
                self.append('Error: ' + str(e))
        threading.Thread(target=_start, daemon=True).start()

    def play_first(self):
        if not self.battle:
            messagebox.showwarning('Not ready', 'Battle not started')
            return
        ok = self.battle.play_card(0)
        if ok:
            self.append('Played first card. New state:')
            self.append(str(self.battle.get_state()))
        else:
            self.append('Failed to play card')

    def on_remote(self, payload):
        self.append('Remote intent: ' + str(payload))

    def append(self, text):
        self.txt.insert(tk.END, text + '\n')
        self.txt.see(tk.END)

    def back_to_lobby(self):
        self.controller.show_frame('LobbyView')

    def on_show(self):
        """Ensure the pygame scene manager is running and switch to the battle scene."""
        try:
            from .pygame_scene_manager import start_manager, switch_scene, is_running
            from .scene_registry import register_all_scenes
            from .lobby_view import START_BATTLE, GOTO_DECK, GOTO_MARKET, GOTO_LOBBY, GOTO_SETTINGS

            if not is_running():
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
                        }
                        target = mapping.get(state)
                        if target:
                            self.controller.after(0, lambda: self.controller.show_frame(target))
                    except Exception as e:
                        print('Scene event handler error:', e)

                start_manager(self._scene_stop, size=(800, 600), event_handler=_scene_event_handler)
                time.sleep(0.1)
            switch_scene('battle')
        except Exception as e:
            print('Failed to switch to battle scene:', e)
