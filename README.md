# CardGamePrototype

Prototype Online Collectible Card Game (CCG) in Python.

Overview
- Central server (meta-game): user auth, deck building, matchmaking, marketplace using SQLite.
- P2P in-game battles: deterministic seed exchange and intent-based actions between peers.

Quick start (server)

1. From the project root run the server:

```powershell
cd 'C:\Users\Chile\.vscode\workSpace\CardGamePrototype'
python .\src\server\server_main.py
```

2. The server will create `db/game.db` and seed two test users (alice / bob).

P2P battle (quick test)

1. Use the `src/p2p_network` modules to implement a simple local battle. A small example is provided in `scripts/test_p2p.py`.

Notes
- Networking uses newline-delimited JSON messages for the prototype. Each message is an object with `action` and `payload` fields.
- Determinism is achieved by exchanging a shared integer seed (P2P_SEED_EXCHANGE). Both peers use the same seed to initialize `RNGManager`.
- Marketplace buy operations use a single SQLite transaction (`BEGIN IMMEDIATE`) to maintain atomicity.

Files of interest
- `src/common/models.py` — dataclass for Card and JSON loader
- `src/common/protocol.py` — shared message names and pack/unpack helpers
- `src/server` — central server code (DB, auth, marketplace, matchmaking, server_main)
- `src/p2p_network` — RNG manager, peer handshake, and battle logic

License
Prototype code; feel free to adapt for learning or prototyping.

```mermaid
erDiagram
    %% 1. 使用者表 (User Profile)
    USERS {
        int id PK "Auto Increment"
        string username "Unique"
        string password_hash "Security"
        int gold "金幣 (遊戲內獲取)"
        int gems "寶石 (付費/稀有)"
    }

    %% 2. 卡片定義 (Metadata)
    %% 備註：對應 cards.json 的邏輯映射
    CARDS {
        int id PK
        string name "e.g. Novice Soldier"
        int cost "消耗"
        int attack "攻擊力"
        int health "血量"
        string description "技能描述"
        string rarity "Common/Rare..."
    }

    %% 3. 玩家庫存 (Inventory)
    USER_CARDS {
        int id PK
        int user_id FK
        int card_id FK
        int count "持有數量"
    }

    %% 4. 牌組構成 (Deck Construction)
    DECK_CARDS {
        int user_id FK
        int card_id FK
        int count "放入牌組數量"
    }

    %% 5. 市場掛單 (Marketplace)
    MARKET_LISTINGS {
        int id PK
        int seller_id FK
        int card_id FK
        int price "售價"
        int quantity "掛單數量"
    }

    %% 6. 交易日誌 (Audit Log)
    TRANSACTION_LOGS {
        int id PK
        int buyer_id FK
        int seller_id FK
        int card_id FK
        int price "成交價"
        datetime timestamp "交易時間"
    }

    %% 關聯定義
    USERS ||--o{ USER_CARDS : "owns"
    CARDS ||--o{ USER_CARDS : "defined_as"
    
    USERS ||--o{ DECK_CARDS : "builds_deck_with"
    CARDS ||--o{ DECK_CARDS : "included_in_deck"
    
    USERS ||--o{ MARKET_LISTINGS : "sells"
    CARDS ||--o{ MARKET_LISTINGS : "listed_item"
    
    USERS ||--o{ TRANSACTION_LOGS : "buyer_record"
    USERS ||--o{ TRANSACTION_LOGS : "seller_record"
```

```mermaid
sequenceDiagram
    participant P1 as Player A (Client)
    participant P2 as Player B (Peer)
    participant Server as Game Server
    
    Note over P1, P2: 階段 1: 初始化同步 (Protocol.py)
    P1->>P2: Send P2P_SEED_EXCHANGE {seed: 12345}
    P2-->>P1: Reply P2P_SEED_ACK {accepted: true}
    Note right of P1: 雙方確認亂數種子一致<br/>確保遊戲邏輯同步
    
    Note over P1, P2: 階段 2: 戰鬥操作 (Action)
    P1->>P1: 玩家使用 "Arcane Bolt"
    P1->>P2: Send JSON Payload (TCP Socket)
    Note right of P1: Action: "P2P_INTENT"<br/>Args: {action: "PLAY_CARD", card_idx: 1}
    
    P2->>P2: unpack_message()
    P2->>P2: GameEngine 更新狀態<br/>(扣除 P2 血量 -3)
    
    Note over P1, Server: 階段 3: 結算
    P1->>Server: STATE_SYNC (Result)
    Server-->>P1: Update Rank/Gold
```
