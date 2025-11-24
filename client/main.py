"""Client entrypoint: simple Tkinter shell to switch between views."""
import os
import sys
import tkinter as tk
import argparse
import threading

# When running this file directly (python client\main.py) the package
# import `from client.ui import ...` can fail because the project root is
# not on sys.path. Try importing `client` and if it fails, insert the
# project root (parent of this `client` folder) to sys.path so the
# package import works.
try:
    import client  # attempt to resolve package normally
except ModuleNotFoundError:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from client.ui import login_view, lobby_view, market_view, deck_builder, battle_view

# Scene manager helpers
from client.ui.pygame_scene_manager import start_manager, stop_manager, switch_scene, is_running
from client.ui.scene_registry import register_all_scenes


class App(tk.Tk):
    def __init__(self, auto_username=None, auto_user_id=None, auto_gold=None):
        super().__init__()
        self.title("CCG Prototype Client")
        self.geometry("640x480")
        self.user = {"user_id": None, "username": None}

        # container for views
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (login_view.LoginView, lobby_view.LobbyView, market_view.MarketView, deck_builder.DeckBuilderView, battle_view.BattleView):
            frame = F(parent=self.container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # track current frame name so we can call on_hide when switching
        self._current_frame_name = None

        # If auto-login args provided, populate user and show Lobby; otherwise show Login
        if auto_username:
            self.user['username'] = auto_username
            # user_id can be provided or fallback to username
            self.user['user_id'] = auto_user_id if auto_user_id is not None else auto_username
            if auto_gold is not None:
                self.user['gold'] = auto_gold
            self.show_frame('LobbyView')
        else:
            self.show_frame('LoginView')
        self._current_frame_name = None
        
        '''# Start centralized pygame scene manager in background (non-blocking)
        try:
            # register scenes once
            register_all_scenes(self.user)

            # Tk-safe event handler: schedule controller actions on Tk thread
            def _scene_event_handler(state, scene_name=None):
                try:
                    mapping = {
                        lobby_view.START_BATTLE: 'BattleView',
                        lobby_view.GOTO_DECK: 'DeckBuilderView',
                        lobby_view.GOTO_MARKET: 'MarketView',
                        lobby_view.GOTO_LOBBY: 'LobbyView',
                        lobby_view.GOTO_SETTINGS: 'LoginView',
                    }
                    target = mapping.get(state)
                    if target:
                        # schedule on Tk mainloop
                        self.after(0, lambda t=target: self.show_frame(t))
                except Exception as e:
                    print('Scene event handler error:', e)

            # ensure manager running
            if not is_running():
                self._pg_stop = threading.Event()
                start_manager(self._pg_stop, size=(800, 600), event_handler=_scene_event_handler)
        except Exception:
            pass
        '''
        # ensure we stop manager when window is closed
        try:
            self.protocol("WM_DELETE_WINDOW", self.on_close)
        except Exception:
            pass

    def show_frame(self, name):
        # call on_hide on previous frame if available
        if self._current_frame_name:
            prev = self.frames.get(self._current_frame_name)
            if prev and hasattr(prev, 'on_hide') and callable(getattr(prev, 'on_hide')):
                try:
                    prev.on_hide()
                except Exception:
                    pass

        frame = self.frames.get(name)
        if frame:
            frame.tkraise()
            # call on_show hook if view wants to refresh state when shown
            if hasattr(frame, 'on_show') and callable(getattr(frame, 'on_show')):
                try:
                    frame.on_show()
                except Exception:
                    # do not break on refresh errors
                    pass
            self._current_frame_name = name

    def start_scene(self, scene_name: str, **kwargs):
        """Request the pygame scene manager to switch to `scene_name`.

        This is non-blocking: the manager runs in a background thread and will
        perform the switch on its next loop iteration.
        """
        try:
            switch_scene(scene_name, **kwargs)
        except Exception as e:
            print('Failed to request scene switch:', e)

    def on_close(self):
        """Stop background services (pygame manager) and close the Tk app."""
        try:
            if hasattr(self, '_pg_stop') and self._pg_stop:
                # signal manager to stop and wait briefly
                stop_manager(timeout=1.0)
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


def main():
    # parse optional auto-login args
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--auto-username', type=str, default=None)
    p.add_argument('--auto-user-id', type=str, default=None)
    p.add_argument('--auto-gold', type=int, default=None)
    args, _ = p.parse_known_args()

    app = App(auto_username=args.auto_username, auto_user_id=args.auto_user_id, auto_gold=args.auto_gold)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("\n程式被使用者中斷 (KeyboardInterrupt)。正在關閉...")
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")
    finally:
        # 確保無論如何都會呼叫清理函數
        if hasattr(app, 'on_close'):
            app.on_close()
        # 強制結束所有執行緒 (防止 Pygame 卡在背景)
        try:
            import sys
            sys.exit(0)
        except SystemExit:
            pass

if __name__ == '__main__':
    main()
