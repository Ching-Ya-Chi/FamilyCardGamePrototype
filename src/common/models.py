from dataclasses import dataclass, asdict
from typing import Dict, Any
import json
from pathlib import Path


@dataclass
class Card:
    """Simple card dataclass for prototype.

    Fields:
      id: str         -- unique card id (string)
      name: str
      cost: int
      attack: int
      health: int
      type: str       -- e.g., 'Minion', 'Spell', 'Weapon'
      raw: Dict[str, Any] = None -- full JSON payload if present
    """

    id: str
    name: str
    cost: int
    attack: int
    health: int
    type: str
    raw: Dict[str, Any] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Card":
        # Basic normalization and defaults for happy path
        return cls(
            id=str(d["id"]),
            name=d.get("name", "Unnamed"),
            cost=int(d.get("cost", 0)),
            attack=int(d.get("attack", 0)),
            health=int(d.get("health", 0)),
            type=d.get("type", "Minion"),
            raw=d,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_cards_from_file(path: str) -> Dict[str, Card]:
    """Load a list of card definitions (JSON array) into a dict of Card objects keyed by id.

    Example JSON format (array):
    [
      {"id": "C001", "name": "Novice", "cost": 1, "attack": 1, "health": 2, "type": "Minion"},
      ...
    ]
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"cards file not found: {path}")

    with p.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    cards: Dict[str, Card] = {}
    for item in raw:
        card = Card.from_dict(item)
        cards[card.id] = card

    return cards


def dump_cards_to_file(cards: Dict[str, Card], path: str) -> None:
    p = Path(path)
    arr = [c.to_dict() for c in cards.values()]
    with p.open("w", encoding="utf-8") as fh:
        json.dump(arr, fh, indent=2, ensure_ascii=False)
