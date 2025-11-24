# client/logic/game_engine.py

import random
from client.services.game_db_service import service as db_service

class Minion:
    def __init__(self, card_data, owner_idx):
        self.card_id = card_data['id']
        self.name = card_data['name']
        self.max_hp = card_data['health']
        self.current_hp = self.max_hp
        self.attack_val = card_data['attack']
        self.cost = card_data['cost']
        self.owner_idx = owner_idx # 0 or 1
        self.can_attack = False # 剛下場不能攻擊 (衝鋒除外，這裡先做基礎)
        self.has_attacked = False

class Player:
    def __init__(self, user_id, deck_list):
        self.user_id = user_id
        self.deck = deck_list.copy()
        random.shuffle(self.deck)
        self.hand = [] # List of Card Data (Dict)
        self.board = [] # List of Minion Objects
        self.max_mana = 0
        self.current_mana = 0
        self.fatigue_damage = 0

class GameEngine:
    def __init__(self, p1_user_id, p1_deck, p2_user_id, p2_deck):
        self.players = [
            Player(p1_user_id, p1_deck),
            Player(p2_user_id, p2_deck)
        ]
        self.turn_count = 0
        self.current_player_idx = 0 # 0 for P1, 1 for P2
        self.game_over = False
        self.winner_idx = None
        self.logs = []

        # 載入所有卡片資料以供查詢
        self.card_db = db_service.get_all_cards_dict()

        self._setup_game()

    def _setup_game(self):
        # 1. 決定先後手 (這裡簡單用隨機，或者固定 P1 先)
        self.current_player_idx = random.randint(0, 1)
        self.log(f"Game Start! Player {self.current_player_idx + 1} goes first.")

        # 2. 雙方抽牌 (起手 3 張)
        for i in range(2):
            for _ in range(3):
                self._draw_card(i)

        # 3. 後手補償：場上直接生成一張 Card ID 1
        second_player_idx = 1 - self.current_player_idx
        bonus_card = self.card_db.get(1)
        if bonus_card:
            minion = Minion(bonus_card, second_player_idx)
            minion.can_attack = True # 特例：場上原本有的通常可以直接打，或是下一回合打
            self.players[second_player_idx].board.append(minion)
            self.log(f"Player {second_player_idx + 1} gets a bonus {minion.name} on board.")

        # 4. 開始第一回合
        self._start_turn()

    def _start_turn(self):
        self.turn_count += 1
        p = self.get_current_player()
        
        # 法力成長 (上限 10)
        if p.max_mana < 10:
            p.max_mana += 1
        p.current_mana = p.max_mana
        
        # 重置場上隨從攻擊狀態
        for m in p.board:
            m.can_attack = True
            m.has_attacked = False

        # 抽一張牌
        self._draw_card(self.current_player_idx)
        
        # 檢查勝利條件 (若回合開始時場上無怪 -> 輸掉)
        # 注意：通常檢查是在動作後，但依照你的需求「場上沒有卡牌後落敗」
        # 我們設定為：回合結束時檢查，或者隨從死亡時檢查。
        # 為了避免第一回合先手直接輸掉 (因為還沒下怪)，我們給予豁免權
        # 只有當 Turn > 2 (雙方都動過後) 才開始嚴格檢查，或者只在隨從死亡時檢查

    def _draw_card(self, player_idx):
        p = self.players[player_idx]
        if len(p.deck) > 0:
            card_id = p.deck.pop(0)
            card_data = self.card_db.get(card_id)
            if card_data:
                p.hand.append(card_data)
        else:
            p.fatigue_damage += 1
            self.log(f"Player {player_idx+1} is out of cards! Fatigue: {p.fatigue_damage}")

    def play_card(self, hand_index):
        """玩家打出手牌"""
        if self.game_over: return False
        
        p = self.get_current_player()
        if hand_index < 0 or hand_index >= len(p.hand):
            return False

        card_data = p.hand[hand_index]
        if p.current_mana >= card_data['cost']:
            # 扣魔
            p.current_mana -= card_data['cost']
            # 移除手牌
            p.hand.pop(hand_index)
            # 召喚隨從
            minion = Minion(card_data, self.current_player_idx)
            p.board.append(minion)
            self.log(f"Player {self.current_player_idx+1} played {minion.name}")
            
            # 檢查勝利條件 (雖然下怪通常不會輸，但保持一致性)
            self._check_win_condition()
            return True
        else:
            self.log("Not enough mana!")
            return False

    def attack(self, attacker_idx, target_idx):
        """
        attacker_idx: 當前玩家場上隨從的 index
        target_idx: 對手場上隨從的 index
        """
        if self.game_over: return False
        
        p = self.get_current_player()
        enemy = self.players[1 - self.current_player_idx]

        if attacker_idx >= len(p.board) or target_idx >= len(enemy.board):
            return False

        attacker = p.board[attacker_idx]
        defender = enemy.board[target_idx]

        if not attacker.can_attack or attacker.has_attacked:
            self.log("This minion cannot attack.")
            return False

        # 執行戰鬥
        self.log(f"{attacker.name} attacks {defender.name}")
        
        # 雙方扣血
        defender.current_hp -= attacker.attack_val
        attacker.current_hp -= defender.attack_val
        
        attacker.has_attacked = True
        
        # 處理死亡
        self._resolve_deaths(p, enemy)
        
        return True

    def end_turn(self):
        if self.game_over: return
        
        # 檢查勝利條件 (回合結束時若空場則輸)
        self._check_win_condition()
        if self.game_over: return

        self.log(f"Player {self.current_player_idx+1} ended turn.")
        self.current_player_idx = 1 - self.current_player_idx
        self._start_turn()

    def _resolve_deaths(self, p1, p2):
        # 移除血量 <= 0 的隨從
        p1.board = [m for m in p1.board if m.current_hp > 0]
        p2.board = [m for m in p2.board if m.current_hp > 0]
        
        self._check_win_condition()

    def _check_win_condition(self):
        # 規則：場上沒有卡牌後落敗
        # 豁免：第一回合先手剛開始時是空的，不能判輸
        # 邏輯修正：只要回合數 > 1 (雙方都已經有機會做事了)，空場即判負
        # 或者：如果你自己的回合結束時空場，或者對手回合把你打光，你就輸了
        
        # 這裡採用嚴格判定：任何時刻偵測到空場即輸，但給予開局保護
        if self.turn_count <= 1 and len(self.players[self.current_player_idx].board) == 0:
            return # 第一回合保護期

        p1_empty = len(self.players[0].board) == 0
        p2_empty = len(self.players[1].board) == 0

        if p1_empty and p2_empty:
            self.game_over = True
            self.winner_idx = -1 # 平手
            self.log("Draw! Both boards empty.")
        elif p1_empty:
            self.game_over = True
            self.winner_idx = 1 # P2 Win
            self.log("Player 1 has no minions! Player 2 Wins!")
        elif p2_empty:
            self.game_over = True
            self.winner_idx = 0 # P1 Win
            self.log("Player 2 has no minions! Player 1 Wins!")

    def get_current_player(self):
        return self.players[self.current_player_idx]
    
    def get_enemy_player(self):
        return self.players[1 - self.current_player_idx]

    def log(self, msg):
        print(f"[Engine] {msg}")
        self.logs.append(msg)