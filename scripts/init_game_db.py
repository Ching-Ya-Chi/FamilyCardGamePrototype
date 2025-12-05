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
    
    conn = db.connect() 
    #在執行 schema 之前，先暫時關閉外鍵檢查，以免 DROP TABLE 失敗
    conn.execute("PRAGMA foreign_keys = OFF")
    # 1. 建立表格
    db.init_schema(str(schema_path))
    # 重建後重新開啟檢查，確保後續 INSERT 資料時資料完整性受保護
    conn.execute("PRAGMA foreign_keys = ON")
     # 2. 插入卡片資料 (確保稀有度分配正確)
    print("插入卡片資料...")
    # 格式: (id, name, cost, atk, hp, desc, rarity)
    cards = [
        # 1 Legend
        (1, "便當龍", 7, 8, 8, "Legendary Dragon.", "Legendary"),
        # 4 Epic
        (2, "霜淇淋法師", 3, 3, 4, "Freezes targets.", "Epic"),
        (3, "優格超人", 5, 5, 4, "Strikes with lightning.", "Epic"),
        (4, "御夫-飯糰", 4, 4, 5, "Consume life.", "Epic"),
        (5, "屠夫", 4, 3, 6, "Heals allies.", "Epic"),
        # Some Rare
        (6, "三明治守衛", 5, 6, 7, "Huge and ugly.", "Rare"),
        (7, "來杯咖啡嗎", 4, 2, 6, "Solid as a rock.", "Rare"),
        (8, "茶葉蛋大師", 2, 2, 2, "A wild beast.", "Rare"),
        (9, "Family Guy", 1, 1, 4, "A guy.", "Common"),
        # ... 這裡為了簡化，剩下的 ID 9~30 我們隨機分配 Rare/Common
    ]
    
    # 補足卡片並隨機分配稀有度 (模擬資料庫)
    import random
    for i in range(10, 31):
        # 簡單機率分配用於測試
        r_val = random.random()
        if r_val < 0.2: rarity = "Rare"
        else: rarity = "Common"
        cards.append((i, f"Card {i}", random.randint(1,5), random.randint(1,5), random.randint(1,5), "Generated", rarity))

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
        (2, 4, 500, 1), 
        (2, 5, 120, 2), 
        (2, 3, 50, 5),  
    ]
    with db.transaction() as conn:
        conn.executemany("INSERT INTO market_listings (seller_id, card_id, price, quantity) VALUES (?, ?, ?, ?)", listings)

    # 6. 初始化玩家卡盒 (新增這段)
    print("初始化玩家卡盒...")
    user_ids = [1, 2, 3]
    gacha_boxes = []
    for uid in user_ids:
        # 預設 100 張: 1L, 4E, 20R, 75C
        gacha_boxes.append((uid, 1, 4, 20, 75))
    
    with db.transaction() as conn:
        conn.executemany(
            "INSERT INTO user_gacha_box (user_id, legend_count, epic_count, rare_count, common_count) VALUES (?, ?, ?, ?, ?)",
            gacha_boxes
        )

    print("資料庫初始化完成！")


if __name__ == "__main__":
    init_db()