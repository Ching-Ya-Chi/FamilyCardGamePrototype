from src.server.database import Database
from pathlib import Path

# 指向你的 DB 檔案
DB_PATH = Path(__file__).resolve().parents[2] / "game.db"

class GameDBService:
    def __init__(self):
        self.db = Database(str(DB_PATH))
        # 注意：實際專案可能需要更好的連線管理，這裡為了 prototype 每次操作都 connect
        self.db.connect() 

    def get_all_cards_dict(self):
        """回傳字典格式的卡片圖鑑 {id: card_data}"""
        rows = self.db.fetchall("SELECT * FROM cards")
        return {row['id']: dict(row) for row in rows}

    def get_card_list(self):
        """回傳列表格式的卡片"""
        rows = self.db.fetchall("SELECT * FROM cards")
        return [dict(row) for row in rows]

    def get_user_inventory(self, user_id):
        """回傳使用者持有的卡片庫存 {card_id: count}"""
        sql = "SELECT card_id, count FROM user_cards WHERE user_id = ?"
        rows = self.db.fetchall(sql, (user_id,))
        inventory = {row['card_id']: row['count'] for row in rows}
        return inventory

    def get_market_listings(self):
        """取得市場掛單，包含卡片詳細資訊"""
        sql = """
            SELECT m.id, m.price, m.quantity, u.username as seller, c.name, c.id as card_id, c.attack, c.health
            FROM market_listings m
            JOIN users u ON m.seller_id = u.id
            JOIN cards c ON m.card_id = c.id
        """
        rows = self.db.fetchall(sql)
        # 整理結構以符合 MarketScene 的需求
        # 這裡將資料整理成 MarketScene 喜歡的巢狀結構
        market_data = {}
        for row in rows:
            c_name = row['name']
            if c_name not in market_data:
                market_data[c_name] = {"sells": [], "buys": []}
            
            market_data[c_name]["sells"].append({
                "user": row['seller'],
                "price": row['price']
            })
        return market_data
    
    def get_user_deck(self, user_id):
        """取得玩家目前的牌組 (回傳 card_id 的列表)"""
        try:
            # 假設 deck_cards 表結構是 (user_id, card_id, count)
            # 這裡我們將其展開為 [1, 1, 2, 3, 3, 3] 這樣的列表
            sql = "SELECT card_id, count FROM deck_cards WHERE user_id = ?"
            rows = self.db.fetchall(sql, (user_id,))
            deck = []
            for row in rows:
                # 根據 count 重複添加 card_id
                for _ in range(row['count']):
                    deck.append(row['card_id'])
            # 依照 ID 排序方便檢視
            deck.sort()
            return deck
        except Exception as e:
            print(f"[DB] Get deck error: {e}")
            return []

    def save_user_deck(self, user_id, deck_list):
        """儲存玩家牌組 (先清空舊的，再存入新的)"""
        try:
            # 1. 統計每個 ID 的數量
            from collections import Counter
            counts = Counter(deck_list)
            
            with self.db.transaction() as conn:
                # 2. 刪除該玩家舊的牌組資料
                conn.execute("DELETE FROM deck_cards WHERE user_id = ?", (user_id,))
                
                # 3. 插入新資料
                data_to_insert = [(user_id, cid, count) for cid, count in counts.items()]
                if data_to_insert:
                    conn.executemany(
                        "INSERT INTO deck_cards (user_id, card_id, count) VALUES (?, ?, ?)", 
                        data_to_insert
                    )
            print(f"[DB] Saved deck for user {user_id}. Size: {len(deck_list)}")
            return True
        except Exception as e:
            print(f"[DB] Save deck error: {e}")
            return False
        
    def get_user_fresh_data(self, user_id):
        """從 DB 獲取最新的使用者資訊 (Gold, Gems)"""
        try:
            # 回傳 dict (row)
            row = self.db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"[DB] Get User Data Error: {e}")
            return None
        
    def execute_buy(self, buyer_id, listing_id):
        """
        執行購買交易：
        1. 檢查買家金幣
        2. 扣除金幣，給予賣家金幣
        3. 扣除掛單數量 (若歸零則刪除)
        4. 買家獲得卡片
        """
        try:
            with self.db.transaction() as conn:
                # A. 取得掛單資訊
                row = conn.execute("SELECT seller_id, card_id, price, quantity FROM market_listings WHERE id = ?", (listing_id,)).fetchone()
                if not row: return "Listing not found"
                seller_id, card_id, price, qty = row['seller_id'], row['card_id'], row['price'], row['quantity']

                if seller_id == buyer_id: return "Cannot buy your own listing"

                # B. 檢查買家金幣
                buyer = conn.execute("SELECT gold FROM users WHERE id = ?", (buyer_id,)).fetchone()
                if buyer['gold'] < price: return "Not enough gold"

                # C. 金幣轉移
                conn.execute("UPDATE users SET gold = gold - ? WHERE id = ?", (price, buyer_id))
                conn.execute("UPDATE users SET gold = gold + ? WHERE id = ?", (price, seller_id))

                # D. 處理掛單 (扣庫存或刪除)
                if qty > 1:
                    conn.execute("UPDATE market_listings SET quantity = quantity - 1 WHERE id = ?", (listing_id,))
                else:
                    conn.execute("DELETE FROM market_listings WHERE id = ?", (listing_id,))

                # E. 給買家卡片 (檢查是否已有記錄)
                inventory = conn.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?", (buyer_id, card_id)).fetchone()
                if inventory:
                    conn.execute("UPDATE user_cards SET count = count + 1 WHERE user_id = ? AND card_id = ?", (buyer_id, card_id))
                else:
                    conn.execute("INSERT INTO user_cards (user_id, card_id, count) VALUES (?, ?, 1)", (buyer_id, card_id))
                
                #F. 寫入交易紀錄
                conn.execute(
                    "INSERT INTO transaction_logs (buyer_id, seller_id, card_id, price) VALUES (?, ?, ?, ?)",
                    (buyer_id, seller_id, card_id, price)
                )
            
            print(f"[DB] Transaction Success: User {buyer_id} bought Listing {listing_id}")
            return "Success"
        except Exception as e:
            print(f"[DB] Buy Error: {e}")
            return f"Error: {e}"

    def execute_sell(self, seller_id, card_id, price):
        """
        執行販賣上架：
        1. 檢查庫存
        2. 扣除庫存
        3. 新增掛單
        """
        try:
            with self.db.transaction() as conn:
                # A. 檢查庫存
                row = conn.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?", (seller_id, card_id)).fetchone()
                if not row or row['count'] < 1:
                    return "Not enough cards"

                # B. 扣除庫存
                if row['count'] > 1:
                    conn.execute("UPDATE user_cards SET count = count - 1 WHERE user_id = ? AND card_id = ?", (seller_id, card_id))
                else:
                    conn.execute("DELETE FROM user_cards WHERE user_id = ? AND card_id = ?", (seller_id, card_id))

                # C. 新增掛單
                conn.execute("INSERT INTO market_listings (seller_id, card_id, price, quantity) VALUES (?, ?, ?, 1)", (seller_id, card_id, price))
            
            print(f"[DB] Listing Created: User {seller_id} selling Card {card_id} for {price}")
            return "Success"
        except Exception as e:
            print(f"[DB] Sell Error: {e}")
            return f"Error: {e}"
            
    def get_raw_listings(self):
        """回傳包含 listing_id 的完整列表，供 MarketScene 使用"""
        sql = """
            SELECT m.id as listing_id, m.price, m.quantity, u.username as seller, c.name, c.id as card_id
            FROM market_listings m
            JOIN users u ON m.seller_id = u.id
            JOIN cards c ON m.card_id = c.id
        """
        return self.db.fetchall(sql)

    def get_gacha_box_state(self, user_id):
        """取得玩家卡盒剩餘狀況"""
        try:
            row = self.db.fetchone("SELECT * FROM user_gacha_box WHERE user_id = ?", (user_id,))
            if not row:
                # 如果沒有，創建一個新的
                with self.db.transaction() as conn:
                    conn.execute("INSERT INTO user_gacha_box (user_id) VALUES (?)", (user_id,))
                return {'legend_count': 1, 'epic_count': 4, 'rare_count': 20, 'common_count': 75}
            return dict(row)
        except Exception as e:
            print(f"[DB] Get Gacha State Error: {e}")
            return None

    def execute_gacha_draw(self, user_id, rarity_picked, cost):
        """
        執行抽卡交易：
        1. 扣錢
        2. 扣除卡盒對應稀有度的數量
        3. 隨機挑選一張該稀有度的卡片
        4. 加入玩家庫存
        """
        try:
            with self.db.transaction() as conn:
                # 1. 檢查金幣
                user = conn.execute("SELECT gold FROM users WHERE id = ?", (user_id,)).fetchone()
                if user['gold'] < cost:
                    return {"success": False, "message": "Not enough gold"}

                # 2. 檢查該稀有度是否還有剩
                col_name = f"{rarity_picked.lower()}_count" # e.g. legend_count
                box = conn.execute(f"SELECT {col_name} FROM user_gacha_box WHERE user_id = ?", (user_id,)).fetchone()
                if box[col_name] <= 0:
                    return {"success": False, "message": f"No {rarity_picked} cards left in box"}

                # --- 交易執行 ---
                
                # A. 扣錢
                conn.execute("UPDATE users SET gold = gold - ? WHERE id = ?", (cost, user_id))
                
                # B. 扣卡盒
                conn.execute(f"UPDATE user_gacha_box SET {col_name} = {col_name} - 1 WHERE user_id = ?", (user_id,))
                
                # C. 隨機選一張該稀有度的卡 (從卡片圖鑑中選)
                # 注意：這裡簡單用 SQL Random，實際專案可能會有更複雜的權重
                # 修正: rarity 欄位首字大寫 (Legendary, Epic...)
                target_rarity_str = rarity_picked.capitalize() 
                if rarity_picked == "legend": target_rarity_str = "Legendary"
                
                card_row = conn.execute(
                    "SELECT * FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", 
                    (target_rarity_str,)
                ).fetchone()
                
                if not card_row:
                    # 萬一圖鑑裡沒有這種卡 (防呆)
                    raise Exception(f"No cards defined for rarity {target_rarity_str}")
                
                card_id = card_row['id']
                
                # D. 給玩家卡片
                inventory = conn.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?", (user_id, card_id)).fetchone()
                if inventory:
                    conn.execute("UPDATE user_cards SET count = count + 1 WHERE user_id = ? AND card_id = ?", (user_id, card_id))
                else:
                    conn.execute("INSERT INTO user_cards (user_id, card_id, count) VALUES (?, ?, 1)", (user_id, card_id))

                print(f"[DB] Gacha Success: {rarity_picked} -> Card {card_id}")
                
                # 回傳卡片資料供前端顯示
                return {
                    "success": True, 
                    "card": dict(card_row),
                    "remaining": box[col_name] - 1 # 回傳該稀有度剩多少
                }
                
        except Exception as e:
            print(f"[DB] Gacha Transaction Error: {e}")
            return {"success": False, "message": str(e)}

# 全域單例
service = GameDBService()