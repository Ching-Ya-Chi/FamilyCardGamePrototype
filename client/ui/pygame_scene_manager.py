import pygame
import threading
import time
from typing import Callable, Dict, Optional


class PygameSceneManager:
    def __init__(self, size=(800, 600)):
        pygame.init()
        self.size = size
        self.screen = pygame.display.set_mode(self.size)
        self.clock = pygame.time.Clock()
        self._scenes: Dict[str, Callable] = {}
        self._current_name: Optional[str] = None
        self._current = None
        self._lock = threading.Lock()
        self._next_scene: Optional[tuple] = None
        self._running = False
        self._event_handler = None

    def register(self, name: str, factory: Callable):
        # factory should be a callable that returns a scene instance given (screen, **kwargs)
        self._scenes[name] = factory

    def switch_to(self, name: str, **kwargs):
        with self._lock:
            self._next_scene = (name, kwargs)

    def _apply_next(self):
        with self._lock:
            ns = self._next_scene
            self._next_scene = None
        if not ns:
            return
        name, kwargs = ns
        if name not in self._scenes:
            print(f"Scene '{name}' not registered")
            return
        # instantiate new scene (pass screen)
        try:
            factory = self._scenes[name]
            new_scene = factory(self.screen, **kwargs)
            self._current = new_scene
            self._current_name = name
            print(f"Switched to scene: {name}")
        except Exception as e:
            print(f"Failed to start scene {name}: {e}")

    def set_event_handler(self, handler: Optional[Callable]):
        """Set a callable to receive scene-level state events.

        The handler will be called as handler(state: str, scene_name: str).
        """
        self._event_handler = handler

    def run(self, stop_event: threading.Event):
        self._running = True
        running = True
        while running and (not stop_event or not stop_event.is_set()):
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False
            # apply scene switch if requested
            self._apply_next()
            # dispatch events/update/draw to current scene
            if self._current is not None:
                try:
                    # prefer handle_events if present
                    if hasattr(self._current, 'handle_events') and callable(getattr(self._current, 'handle_events')):
                        result = self._current.handle_events(events)
                        # if scene returned an event/state, forward to handler
                        if result and self._event_handler:
                            try:
                                self._event_handler(result, self._current_name)
                            except Exception as e:
                                print(f"Error in event handler: {e}")
                    elif hasattr(self._current, 'update') and callable(getattr(self._current, 'update')):
                        # update expects events
                        result = self._current.update(events)
                        if result and self._event_handler:
                            try:
                                self._event_handler(result, self._current_name)
                            except Exception as e:
                                print(f"Error in event handler: {e}")
                except Exception as e:
                    print(f"Error in scene event handling: {e}")
                try:
                    if hasattr(self._current, 'draw') and callable(getattr(self._current, 'draw')):
                        self._current.draw()
                except Exception as e:
                    print(f"Error in scene draw: {e}")
            pygame.display.flip()
            self.clock.tick(60)
        try:
            pygame.quit()
        except Exception:
            pass
        self._running = False

    def start(self, stop_event: Optional[threading.Event] = None):
        """Start the manager run loop in a background thread. If already running, no-op."""
        if getattr(self, '_running', False):
            return
        if stop_event is None:
            stop_event = threading.Event()
        self._stop_event = stop_event

        def _run():
            self.run(self._stop_event)

        t = threading.Thread(target=_run, daemon=True)
        self._thread = t
        t.start()

    def stop(self, timeout: Optional[float] = None):
        """Signal the manager to stop and wait for the thread to finish (optional timeout)."""
        if hasattr(self, '_stop_event') and self._stop_event:
            try:
                self._stop_event.set()
            except Exception:
                pass
        if hasattr(self, '_thread') and getattr(self, '_thread') is not None:
            try:
                self._thread.join(timeout)
            except Exception:
                pass
        self._running = False


# Module-level singleton manager (created on demand)
_manager: Optional[PygameSceneManager] = None
_manager_lock = threading.Lock()


def get_manager(size=(1280, 720)) -> PygameSceneManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = PygameSceneManager(size=size)
    return _manager


def start_manager_in_thread(stop_event: threading.Event, size=(800, 600)) -> PygameSceneManager:
    mgr = get_manager(size=size)
    mgr.start(stop_event)
    return mgr


def switch_scene(name: str, **kwargs):
    mgr = get_manager()
    mgr.switch_to(name, **kwargs)


def register_scene(name: str, factory: Callable):
    mgr = get_manager()
    mgr.register(name, factory)


def start_manager(stop_event: Optional[threading.Event] = None, size=(800, 600), event_handler: Optional[Callable] = None) -> PygameSceneManager:
    mgr = get_manager(size=size)
    if event_handler is not None:
        mgr.set_event_handler(event_handler)
    mgr.start(stop_event)
    return mgr


def stop_manager(timeout: Optional[float] = None):
    mgr = get_manager()
    mgr.stop(timeout)


def is_running() -> bool:
    mgr = get_manager()
    return getattr(mgr, '_running', False)
