-- 清空舊表 (開發用，正式環境小心)
DROP TABLE IF EXISTS market_listings;
DROP TABLE IF EXISTS deck_cards;
DROP TABLE IF EXISTS user_cards;
DROP TABLE IF EXISTS cards;
DROP TABLE IF EXISTS users;

-- 1. 使用者表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    gold INTEGER DEFAULT 0,
    gems INTEGER DEFAULT 0
);

-- 2. 卡片定義表 (所有卡片的圖鑑)
CREATE TABLE cards (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cost INTEGER NOT NULL,
    attack INTEGER DEFAULT 0,
    health INTEGER DEFAULT 0,
    description TEXT,
    rarity TEXT DEFAULT 'Common'
);

-- 3. 玩家持有卡片 (庫存)
CREATE TABLE user_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    card_id INTEGER,
    count INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(card_id) REFERENCES cards(id)
);

-- 4. 玩家牌組 (簡化版：記錄哪些卡在牌組裡)
CREATE TABLE deck_cards (
    user_id INTEGER,
    card_id INTEGER,
    count INTEGER DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(card_id) REFERENCES cards(id)
);

-- 5. 市場掛單
CREATE TABLE market_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER,
    card_id INTEGER,
    price INTEGER,
    quantity INTEGER DEFAULT 1,
    FOREIGN KEY(seller_id) REFERENCES users(id),
    FOREIGN KEY(card_id) REFERENCES cards(id)
);


CREATE TABLE IF NOT EXISTS transaction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER,
    seller_id INTEGER,
    card_id INTEGER,
    price INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(buyer_id) REFERENCES users(id),
    FOREIGN KEY(seller_id) REFERENCES users(id),
    FOREIGN KEY(card_id) REFERENCES cards(id)
);
