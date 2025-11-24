"""Register game scenes with the pygame scene manager.

This central registry avoids circular imports by being a small shim that
imports scene classes and registers factories with the manager.
"""
from .pygame_scene_manager import register_scene


def register_all_scenes(default_user=None):
    # Import scenes here to avoid module-level circular imports
    from .Lobby_Scene import LobbyScene
    from .DeckBuilderScene import DeckBuilderScene
    from .Battle_Scene import BattleScene
    from .MarketScene import MarketScene

    def lobby_factory(screen, user_data=None, **kw):
        return LobbyScene(screen, user_data or default_user)
    def deck_factory(screen, user_data=None, **kw):
        # 傳入 user_data (如果沒有則使用 default_user)
        return DeckBuilderScene(screen, user_data=user_data or default_user)
    
    def market_factory(screen, user_data=None, **kw):
        # 傳入 user_data (如果沒有則使用 default_user)
        return MarketScene(screen, user_data=user_data or default_user)
    def battle_factory(screen, user_data=None, **kw):
        # 傳入 user_data (如果沒有則使用 default_user)
        return BattleScene(screen, user_data=user_data or default_user)

    register_scene('lobby', lobby_factory)
    register_scene('deck', deck_factory)
    register_scene('market', market_factory)
    register_scene('battle', battle_factory)
