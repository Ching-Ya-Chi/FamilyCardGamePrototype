import sys
import os
from pathlib import Path

# 將專案根目錄加入路徑
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.server.database import Database

def init_db():
    db_path = ROOT_DIR / "game.db"
    schema_path = ROOT_DIR / "db" / "schema.sql" # 注意確認 schema.sql 實際路徑
    
    print(f"初始化資料庫: {db_path}")
    db = Database(str(db_path))
    db.connect()
    
    # 1. 建立表格
    db.init_schema(str(schema_path))
    
    # 2. 插入卡片資料
    print("插入卡片資料...")
    cards = [
        (1, "Footman", 1, 1, 2, "A basic soldier.", "Common"),
        (2, "Wolf", 2, 2, 2, "A wild beast.", "Common"),
        (3, "Ogre", 5, 6, 7, "Huge and ugly.", "Rare"),
        (4, "Fire Dragon", 7, 8, 8, "Breaths fire on enemies.", "Legendary"),
        (5, "Ice Wizard", 3, 3, 4, "Freezes targets.", "Epic"),
        (6, "Wind Sprite", 1, 2, 1, "Fast and elusive.", "Common"),
        (7, "Earth Golem", 4, 2, 6, "Solid as a rock.", "Rare"),
        (8, "Thunder Roc", 5, 5, 4, "Strikes with lightning.", "Epic"),
        (9, "Squire", 1, 1, 2, "Ready to serve.", "Common"),
        (10, "Ghoul", 2, 3, 2, "Eats corpses.", "Common")
    ]
    # 補足 20 張
    for i in range(11, 21):
        cards.append((i, f"Card {i}", i % 5 + 1, i % 5, i % 5 + 2, f"Random generated card {i}", "Common"))

    with db.transaction() as conn:
        conn.executemany(
            "INSERT INTO cards (id, name, cost, attack, health, description, rarity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            cards
        )

    # 3. 插入測試使用者
    print("插入使用者...")
    users_data = [
        ("leo", "1", 1000, 50),
        ("Merchant", "1", 5000, 0),
        ("sam", "1", 1000000000, 0) # 修正: 10^9 -> 10億
    ]
    
    with db.transaction() as conn:
        conn.executemany(
            "INSERT INTO users (username, password_hash, gold, gems) VALUES (?, ?, ?, ?)", 
            users_data
        )

    # 4. 發放卡片 (每人每張卡各 2 張)
    print("發放卡片...")
    user_cards = []
    user_ids = [1, 2, 3] # leo, Merchant, sam (根據插入順序)
    card_ids = range(1, 21) # 1~20

    for uid in user_ids:
        for cid in card_ids:
            # (user_id, card_id, count)
            user_cards.append((uid, cid, 2))
    
    with db.transaction() as conn:
        conn.executemany("INSERT INTO user_cards (user_id, card_id, count) VALUES (?, ?, ?)", user_cards)

    # 5. 建立市場掛單
    print("建立市場掛單...")
    listings = [
        (2, 4, 500, 1), # Merchant 賣 Fire Dragon
        (2, 5, 120, 2), # Merchant 賣 Ice Wizard
        (2, 3, 50, 5),  # Merchant 賣 Ogre
    ]
    with db.transaction() as conn:
        conn.executemany("INSERT INTO market_listings (seller_id, card_id, price, quantity) VALUES (?, ?, ?, ?)", listings)

    print("資料庫初始化完成！")

if __name__ == "__main__":
    init_db()