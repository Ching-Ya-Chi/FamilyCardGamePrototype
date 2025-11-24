from typing import Tuple, Optional
from src.server.database import Database


def buy_listing(db: Database, buyer_id: int, listing_id: int, qty: int = 1) -> Tuple[bool, Optional[int], Optional[str]]:
    """Attempt to buy `qty` units from listing_id as buyer_id.

    Returns (ok, tx_id, error_msg)
    """
    conn = db.conn
    if conn is None:
        return False, None, "db not connected"

    with db.transaction() as tx:
        cur = tx.execute("SELECT id, seller_id, card_id, price, quantity FROM marketplace_listings WHERE id = ?", (listing_id,))
        row = cur.fetchone()
        if not row:
            return False, None, "listing_not_found"

        seller_id = row["seller_id"]
        card_id = row["card_id"]
        price = int(row["price"])
        available = int(row["quantity"])

        if available < qty:
            return False, None, "insufficient_listing_quantity"

        total_price = price * qty

        # check buyer gold
        cur = tx.execute("SELECT gold FROM users WHERE id = ?", (buyer_id,))
        brow = cur.fetchone()
        if not brow:
            return False, None, "buyer_not_found"
        buyer_gold = int(brow["gold"])
        if buyer_gold < total_price:
            return False, None, "insufficient_gold"

        # adjust balances
        tx.execute("UPDATE users SET gold = gold - ? WHERE id = ?", (total_price, buyer_id))
        tx.execute("UPDATE users SET gold = gold + ? WHERE id = ?", (total_price, seller_id))

        # decrease or remove listing
        new_qty = available - qty
        if new_qty > 0:
            tx.execute("UPDATE marketplace_listings SET quantity = ? WHERE id = ?", (new_qty, listing_id))
        else:
            tx.execute("DELETE FROM marketplace_listings WHERE id = ?", (listing_id,))

        # give buyer the cards (upsert into user_cards)
        tx.execute(
            "INSERT INTO user_cards (user_id, card_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, card_id) DO UPDATE SET quantity = user_cards.quantity + excluded.quantity",
            (buyer_id, card_id, qty),
        )

        # optionally reduce seller inventory (if enforced) -- best practice requires reserved stock when listing
        tx.execute(
            "UPDATE user_cards SET quantity = quantity - ? WHERE user_id = ? AND card_id = ?",
            (qty, seller_id, card_id),
        )

        # audit log
        cur = tx.execute(
            "INSERT INTO marketplace_tx (buyer_id, seller_id, listing_id, card_id, price, quantity) VALUES (?, ?, ?, ?, ?, ?)",
            (buyer_id, seller_id, listing_id, card_id, price, qty),
        )
        tx_id = cur.lastrowid

        return True, tx_id, None
