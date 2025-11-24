"""Deterministic RNG manager using a shared seed for P2P battles."""
from typing import List, Any
import random


class RNGManager:
    def __init__(self, seed: int):
        self.seed = int(seed)
        self._r = random.Random(self.seed)

    def randint(self, a: int, b: int) -> int:
        return self._r.randint(a, b)

    def random(self) -> float:
        return self._r.random()

    def shuffle(self, seq: List[Any]) -> None:
        """Shuffle in-place deterministically."""
        self._r.shuffle(seq)

    def draw_card(self, deck: List[Any]):
        """Draw a card deterministically from deck (list). Returns the card or None."""
        if not deck:
            return None
        idx = self._r.randint(0, len(deck) - 1)
        return deck.pop(idx)

    def random_damage(self, base: int, variance: int = 0) -> int:
        """Compute damage with optional +/- variance."""
        if variance <= 0:
            return base
        return base + self._r.randint(-variance, variance)
