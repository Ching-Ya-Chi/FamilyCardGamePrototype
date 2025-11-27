from dataclasses import dataclass, asdict
from typing import Dict, Any
import json
from pathlib import Path


@dataclass
class Card:
    """Card dataclass reflecting the database schema and game logic.

    Fields:
      id: int         -- unique card id (DB uses INTEGER)
      name: str
      cost: int
      attack: int
      health: int
      description: str -- Flavor text or ability description
      rarity: str      -- 'Common', 'Rare', 'Epic', 'Legendary'
      type: str        -- 'Minion' (default), 'Spell'
      raw: Dict[str, Any] = None -- full JSON payload if present
    """

    id: int
    name: str
    cost: int
    attack: int
    health: int
    description: str = ""
    rarity: str = "Common"
    type: str = "Minion"
    raw: Dict[str, Any] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Card":
        """Create a Card object from a dictionary (e.g., from DB row)."""
        return cls(
            id=int(d.get("id", 0)),
            name=str(d.get("name", "Unnamed")),
            cost=int(d.get("cost", 0)),
            attack=int(d.get("attack", 0)),
            health=int(d.get("health", 0)),
            # 從 DB 讀取描述與稀有度
            description=str(d.get("description", "")),
            rarity=str(d.get("rarity", "Common")),
            # 資料庫沒存 type，預設為 Minion
            type=str(d.get("type", "Minion")),
            raw=d,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding 'raw' to avoid redundancy."""
        d = asdict(self)
        if "raw" in d:
            del d["raw"]
        return d


def load_cards_from_file(path: str) -> Dict[int, Card]:
    """Load a list of card definitions (JSON array) into a dict of Card objects keyed by id.
    
    Note: In the full game, we mostly load from DB (game_db_service), 
    but this is useful for testing or bootstrapping.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"cards file not found: {path}")

    with p.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    cards: Dict[int, Card] = {}
    for item in raw:
        card = Card.from_dict(item)
        cards[card.id] = card

    return cards


def dump_cards_to_file(cards: Dict[int, Card], path: str) -> None:
    p = Path(path)
    arr = [c.to_dict() for c in cards.values()]
    with p.open("w", encoding="utf-8") as fh:
        json.dump(arr, fh, indent=2, ensure_ascii=False)
