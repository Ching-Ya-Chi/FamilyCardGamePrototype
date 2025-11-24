"""A minimal deterministic battle loop using the P2P peer and RNG manager.

This is intentionally small and focused on the happy path: each player has health
and a hand of simple minion cards (with attack values). Playing a card deals its
attack as direct damage to the other player. Intent messages are sent, not full state.
"""
from typing import List, Dict, Any
import threading
import time

from src.p2p_network.p2p_peer import P2PPeer
from src.p2p_network.rng_manager import RNGManager
from src.common.models import Card
from src.common import protocol


class Battle:
    def __init__(self, local_deck: List[Card], on_remote_intent: callable):
        # local_deck: list of Card objects representing the deck
        self.local_deck = [c for c in local_deck]
        self.local_hand: List[Card] = []
        self.health = 30
        self.enemy_health = 30
        self.peer: P2PPeer = P2PPeer(self._on_intent)
        self.rng: RNGManager = None  # set after handshake
        self.on_remote_intent = on_remote_intent
        self._lock = threading.Lock()

    def start_as_initiator(self, peer_ip: str, peer_port: int, seed: int = None):
        self.peer.connect(peer_ip, peer_port, seed=seed)
        self.rng = self.peer.rng
        # shuffle deck deterministically
        self.rng.shuffle(self.local_deck)
        # draw opening hand (3)
        for _ in range(3):
            c = self.rng.draw_card(self.local_deck)
            if c:
                self.local_hand.append(c)

    def start_as_responder(self, listen_port: int):
        addr = self.peer.accept(listen_port)
        # rng will be set after peer receives seed
        # wait a short time for handshake
        time.sleep(0.1)
        self.rng = self.peer.rng
        if self.rng is None:
            # fallback seed
            self.rng = RNGManager(0)
        self.rng.shuffle(self.local_deck)
        for _ in range(3):
            c = self.rng.draw_card(self.local_deck)
            if c:
                self.local_hand.append(c)

    def _on_intent(self, payload: Dict[str, Any]):
        # called by P2PPeer when remote sends an intent
        act = payload.get('action')
        args = payload.get('args', {})
        if act == 'PLAY_CARD':
            # remote played a card; apply its attack to local health
            attack = int(args.get('attack', 0))
            with self._lock:
                self.health -= attack
            # notify external handler
            try:
                self.on_remote_intent({'type': 'PLAY_CARD', 'attack': attack})
            except Exception:
                pass

    def play_card(self, hand_index: int):
        # play a card from local hand; send intent to peer
        with self._lock:
            if hand_index < 0 or hand_index >= len(self.local_hand):
                return False
            card = self.local_hand.pop(hand_index)
            # perform local effect: reduce enemy health
            damage = card.attack
            self.enemy_health -= damage

        intent = {'action': 'PLAY_CARD', 'args': {'card_id': card.id, 'attack': card.attack}}
        self.peer.send_intent(intent)
        return True

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'health': self.health,
                'enemy_health': self.enemy_health,
                'hand': [c.to_dict() for c in self.local_hand],
                'deck_count': len(self.local_deck),
            }
