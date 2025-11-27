"""P2P Battle Logic with HeartStone-like mechanics.

Features:
- Mana system (cap increases each turn).
- Second player bonus card.
- Attack logic with counter-attack damage.
- Win condition: Lose if board is empty.
"""
from typing import List, Dict, Any
import threading
import time

from src.p2p_network.p2p_peer import P2PPeer
from src.p2p_network.rng_manager import RNGManager
from src.common.models import Card
from src.common import protocol

SYSTEM_BONUS_CARD_ID = 1

class PlayerState:
    def __init__(self, is_local: bool):
        self.is_local = is_local
        self.hand: List[Dict] = []
        self.board: List[Any] = [] # List[Minion]
        self.deck: List[Any] = []
        self.current_mana = 0 # 初始 0，第一回合開始變 1
        self.max_mana = 0
        self.fatigue = 0

class Minion:
    def __init__(self, card_data, owner_idx):
        self.card_id = card_data.get('id', 0)
        self.name = card_data.get('name', 'Unknown')
        self.max_hp = card_data.get('health', 1)
        self.current_hp = self.max_hp
        self.attack_val = card_data.get('attack', 0)
        self.cost = card_data.get('cost', 0)
        self.owner_idx = owner_idx
# 【規則】剛召喚時不能攻擊 (除非是回合開始前就存在的補償卡)
        self.can_attack = False 
        self.has_attacked = False

class Battle:
    def __init__(self, local_deck: List[Card], on_remote_intent: callable):
        # players[0] = 我 (Local), players[1] = 對手 (Remote)
        self.players = [PlayerState(is_local=True), PlayerState(is_local=False)]
        self.current_player_idx = 0 
        self.turn_count = 0 # 從 0 開始
        self.game_over = False
        self.winner_idx = None
        
        # 標記我是發起者還是接收者，用於決定先後手
        self.is_initiator = False 

        self.local_deck_source = local_deck
        self.players[0].deck = [c.to_dict() for c in local_deck]
        self.players[1].deck = [None] * 30 

        self.peer: P2PPeer = P2PPeer(self._on_intent)
        self.rng: RNGManager = None
        self.on_remote_intent = on_remote_intent
        self._lock = threading.Lock()

    def start_as_initiator(self, peer_ip: str, peer_port: int, user_id: int, seed: int = None):
        self.is_initiator = True
        success = self.peer.connect(peer_ip, peer_port, user_id, seed=seed)
        if success:
            self.rng = self.peer.rng
            self._setup_game()
            return True
        else:
            return False

    def start_as_responder(self, listen_port: int, user_id: int):
        self.is_initiator = False
        self.peer.accept(listen_port, user_id)
        
        # 等待 RNG 同步
        import time
        wait_start = time.time()
        while self.peer.rng is None:
            time.sleep(0.1)
            # 如果對方是自己並被拒絕，peer.running 會變 False
            if not self.peer._running:
                print("[Battle] Peer disconnected during handshake")
                return False
            if time.time() - wait_start > 5.0:
                print("[Battle] Responder handshake timeout")
                return False

        self.rng = self.peer.rng
        self._setup_game()
        return True

    def _setup_game(self):
        """遊戲初始化：洗牌、抽牌、決定先後手、後手補償"""

        # --- 【規則】起手必有 1 費卡 ---
        # 我們需要一個確定性的演算法，讓雙方都能算出同樣的結果 (RNG 已同步)
        # 演算法：
        # 1. 找出所有 Cost=1 的卡片索引
        # 2. 隨機選一張 Cost=1 的卡移到最上面
        # 3. 將剩下的卡片洗牌
        # 4. 抽 3 張 (這樣第 1 張一定是 Cost 1)

        deck = self.players[0].deck
        cost_1_indices = [i for i, c in enumerate(deck) if c['cost'] == 1]
        
        if cost_1_indices:
            # 隨機選一張 Cost 1
            chosen_idx = cost_1_indices[self.rng.randint(0, len(cost_1_indices) - 1)]
            chosen_card = deck.pop(chosen_idx)
            
            # 洗剩下的牌
            self.rng.shuffle(deck)
            
            # 把保底卡插回最上面
            deck.insert(0, chosen_card)
        else:
            # 如果牌組裡真的沒有 1 費卡 (DeckBuilder 沒擋住的話)，就普通洗牌
            self.rng.shuffle(deck)
        
        # 抽 3 張起手牌
        for _ in range(3):
            self._draw_card(0)

        # 決定先後手 (0=Initiator先, 1=Responder先)
        starter = self.rng.randint(0, 1)
        
        # 判斷這局是不是「我的回合」
        # 如果 (RNG說Init先 且 我是Init) 或 (RNG說Resp先 且 我是Resp) -> 我先攻
        if (starter == 0 and self.is_initiator) or (starter == 1 and not self.is_initiator):
            self.current_player_idx = 0 # 我先
            # 對手是後手，給對手一張補償卡 (在我的畫面上加給對手)
            self._add_bonus_minion(1)
        else:
            self.current_player_idx = 1 # 對手先
            # 我是後手，給我一張補償卡
            self._add_bonus_minion(0)

        # 開始第一回合
        self._start_turn_logic()

    def _add_bonus_minion(self, p_idx):
        """給予後手玩家一張場上隨從 (系統指定 ID)"""
        # 為了不 Crash，若 DB 讀不到就用 Dummy
        from client.services.game_db_service import service as db_service
        card_list = db_service.get_card_list()
        # 使用設定好的 SYSTEM_BONUS_CARD_ID
        card_data = next((c for c in card_list if c['id'] == SYSTEM_BONUS_CARD_ID), None)
        
        if not card_data:
            # Fallback if ID not found in DB
            card_data = {'id': SYSTEM_BONUS_CARD_ID, 'name': 'System Minion', 'cost': 1, 'attack': 1, 'health': 1}

        minion = Minion(card_data, owner_idx=p_idx)
        # 【規則】後手補償卡是遊戲開始時就在場上的，所以第一回合就能動
        # 因為 _start_turn_logic 會把當前玩家所有隨從設為 can_attack=True
        # 所以這裡設 False 也沒關係，只要輪到該玩家，這張卡就會醒來
        minion.can_attack = False 
        
        self.players[p_idx].board.append(minion)

    def _start_turn_logic(self):
        """回合開始：加法力、抽牌、重置攻擊狀態"""
        self.turn_count += 1
        p_idx = self.current_player_idx
        p = self.players[p_idx]
        
        # 法力成長 (上限 10)
        if p.max_mana < 10:
            p.max_mana += 1
        p.current_mana = p.max_mana
        
        # 【規則】解除召喚失調：當回合開始時，該玩家所有場上隨從都可以攻擊
        for m in p.board:
            m.can_attack = True
            m.has_attacked = False
            
        # 抽牌
        self._draw_card(p_idx)
        
        # 檢查勝利條件 (防止抽牌疲勞死或開局空場)
        self._check_win_condition()

    def _draw_card(self, p_idx):
        p = self.players[p_idx]
        if p_idx == 0: # 我方抽牌
            if p.deck:
                card = p.deck.pop(0)
                p.hand.append(card)
            else:
                # 疲勞 (可選)
                pass
        else:
            # 對手抽牌 (視覺上只知道手牌數增加)
            # 塞一個空 dict 佔位
            p.hand.append({}) 

    def play_card(self, hand_index: int):
        """我方出牌"""
        if self.game_over or self.current_player_idx != 0:
            return False
        
        p0 = self.players[0]
        if hand_index < 0 or hand_index >= len(p0.hand): return False
        
        card_data = p0.hand[hand_index]
        if p0.current_mana < card_data['cost']:
            print("Not enough mana")
            return False

        with self._lock:
            p0.current_mana -= card_data['cost']
            p0.hand.pop(hand_index)
            minion = Minion(card_data, owner_idx=0)
            # 【規則】召喚失調：剛打出的牌預設不能攻擊
            minion.can_attack = False 
            p0.board.append(minion)

        # 傳送意圖
        intent = {'action': 'PLAY_CARD', 'args': {'card_id': card_data['id']}}
        self.peer.send_intent(intent)
        
        self._check_win_condition()
        return True

    def attack(self, attacker_idx, target_idx):
        """我方發動攻擊"""
        if self.game_over or self.current_player_idx != 0: return False
        
        my_board = self.players[0].board
        op_board = self.players[1].board
        
        if attacker_idx >= len(my_board) or target_idx >= len(op_board): return False
        
        attacker = my_board[attacker_idx]
        if not attacker.can_attack or attacker.has_attacked:
            print("Cannot attack")
            return False
            
        # 執行攻擊運算 (本地)
        self._resolve_combat(0, attacker_idx, 1, target_idx)
        
        # 傳送意圖
        # 注意：對手收到時，attacker 是對手的隨從(1)，target 是我的隨從(0)
        intent = {
            'action': 'ATTACK', 
            'args': {'attacker_idx': attacker_idx, 'target_idx': target_idx}
        }
        self.peer.send_intent(intent)
        return True

    def _resolve_combat(self, att_owner, att_idx, def_owner, def_idx):
        """處理戰鬥數值與死亡"""
        attacker = self.players[att_owner].board[att_idx]
        defender = self.players[def_owner].board[def_idx]
        
        # 標記已攻擊
        attacker.has_attacked = True
        
        # 雙方扣血
        defender.current_hp -= attacker.attack_val
        attacker.current_hp -= defender.attack_val
        
        print(f"Combat: {attacker.name}({attacker.current_hp}) vs {defender.name}({defender.current_hp})")
        
        # 移除死亡隨從
        self._clean_dead_minions()
        self._check_win_condition()

    def _clean_dead_minions(self):
        for p in self.players:
            p.board = [m for m in p.board if m.current_hp > 0]

    def end_turn(self):
        if self.current_player_idx != 0: return

        with self._lock:
            self.current_player_idx = 1 # 切換到對手
            self.peer.send_intent({'action': 'END_TURN'})
            # 幫對手執行回合開始邏輯 (加法力、抽牌)
            self._start_turn_logic()

    def _on_intent(self, payload: Dict[str, Any]):
        """處理對手傳來的動作"""
        act = payload.get('action')
        args = payload.get('args', {})
        
        with self._lock:
            if act == 'PLAY_CARD':
                card_id = args.get('card_id')
                # 查詢卡片資料 (這裡簡單模擬，正式版應從 Service 讀)
                # 為了不 Crash，如果讀不到就用 Dummy
                from client.services.game_db_service import service as db_service
                card_list = db_service.get_card_list()
                card_data = next((c for c in card_list if c['id'] == card_id), 
                                 {'id': card_id, 'name': 'Unknown', 'cost': 0, 'attack': 1, 'health': 1})
                
                minion = Minion(card_data, owner_idx=1)
                self.players[1].board.append(minion)
                
                # 扣對手法力 (視覺同步)
                if self.players[1].current_mana >= minion.cost:
                    self.players[1].current_mana -= minion.cost
                # 對手手牌 -1
                if self.players[1].hand: self.players[1].hand.pop()
                
                self._check_win_condition()
                
                # 通知 UI 播放動畫
                if self.on_remote_intent: self.on_remote_intent(payload)

            elif act == 'ATTACK':
                # 對手(1) 的 attacker_idx 打 我(0) 的 target_idx
                att_idx = args.get('attacker_idx')
                def_idx = args.get('target_idx')
                
                # 在我的視角：Attacker 是 Player 1, Defender 是 Player 0
                self._resolve_combat(1, att_idx, 0, def_idx)
                
                # 通知 UI (例如播放被挨打的動畫)
                if self.on_remote_intent: self.on_remote_intent(payload)

            elif act == 'END_TURN':
                self.current_player_idx = 0 # 輪到我
                self._start_turn_logic()

    def _check_win_condition(self):
        """勝利條件：場上無牌即輸"""
        # 給予保護期：如果回合數很低 (Turn <= 2)，通常還沒下怪，不判輸
        if self.turn_count <= 2:
            return

        p0_empty = len(self.players[0].board) == 0
        p1_empty = len(self.players[1].board) == 0

        if p0_empty and p1_empty:
            self.game_over = True
            self.winner_idx = -1 # Draw
        elif p0_empty:
            self.game_over = True
            self.winner_idx = 1 # P1(對手) Win, P0 Lose
        elif p1_empty:
            self.game_over = True
            self.winner_idx = 0 # P0(我) Win

    def get_current_player(self):
        return self.players[self.current_player_idx]
    
    def get_enemy_player(self):
        return self.players[1 - self.current_player_idx]

    @property
    def logs(self):
        return []