# client/ui/Battle_Scene.py

import pygame
from dataclasses import dataclass
from typing import List, Optional, Tuple
from client.services.game_db_service import service as db_service
from client.utils.resource_manager import ResourceManager
from src.p2p_network.battle import Battle
from client.ui.animations import AttackAnimation, CardPopupAnimation, GameStartAnimation, GameEndAnimation, CoinTossAnimation

# Constants
IDLE = "IDLE"
DRAGGING_CARD = "DRAGGING_CARD"
TARGETING = "TARGETING"
GOTO_LOBBY = "GOTO_LOBBY"

class BattleScene:
    SCREEN_W = 1280
    SCREEN_H = 720

    def __init__(self, screen, action_callback=None, user_data=None, p2p_battle=None):
        self.screen = screen
        self.action_callback = action_callback
        
        # 1. 初始化引擎
        my_id = user_data.get('user_id', 1) if user_data else 1
        
        # 優先使用傳入的 P2P Battle 物件
        if p2p_battle:
            self.engine = p2p_battle
            self.is_p2p = True
        else:
            # Fallback: 建立單機測試用的 GameEngine (或是單機版 Battle)
            # 為了保持一致性，建議即使單機測試也用 Battle 類別，只是不連線
            my_deck = db_service.get_user_deck(my_id)
            if not my_deck: my_deck = [1, 1, 2, 2, 3, 3, 4, 5] * 3
            
            # 這裡我們創一個 Battle 物件但不連線，僅供測試 UI
            # 注意：因為沒有連線，所以不會有對手回應
            from src.common.models import Card
            # 將 ID 列表轉為 Card 物件列表
            all_cards = db_service.get_all_cards_dict()
            deck_cards = []
            for cid in my_deck:
                c_data = all_cards.get(cid)
                if c_data:
                    deck_cards.append(Card.from_dict(c_data))
            
            self.engine = Battle(deck_cards, lambda x: print(x))
            # 手動初始化一些數據以免報錯
            from src.p2p_network.rng_manager import RNGManager
            self.engine.rng = RNGManager(0)
            self.engine._setup_game()
            self.is_p2p = False
        
        self.clock = pygame.time.Clock()
        
        self.bg_image = pygame.Surface((self.SCREEN_W, self.SCREEN_H))
        self.bg_image.fill((40, 40, 40))

        pygame.font.init()
        self.font = pygame.font.SysFont("arial", 20)
        self.font_big = pygame.font.SysFont("arial", 32)

        # UI State
        self.state = IDLE
        self.hovered_card_index = None
        self.card_rects = []
        self.dragging_card_index = None
        self.dragging_pos = (0, 0)
        self.attacker_idx = None

        self.battlefield_rect = pygame.Rect(50, 200, 1180, 320)
        self.end_turn_rect = pygame.Rect(1150, 340, 100, 40)
        self.exit_rect = pygame.Rect(self.SCREEN_W - 60, 10, 50, 30)

        # Animation list
        self.animations = []

        # 階段: 'COIN_TOSS' -> 'GAME_START' -> 'PLAYING'
        self.scene_phase = 'COIN_TOSS'
        # 擲硬幣動畫 (傳入 winner_idx: 0是我先, 1是對手先)
        # self.engine.current_player_idx 在 _setup_game 時已經決定好了
        start_anim = CoinTossAnimation(
            (self.SCREEN_W, self.SCREEN_H), 
            self.engine.current_player_idx
        )
        self.animations.append(start_anim)
        
        self.end_anim_triggered = False
    def update(self, events):
        # 1. 計算 Delta Time
        dt = self.clock.tick() / 1000.0
        
        # 2. 更新動畫
        self.animations = [anim for anim in self.animations if anim.update(dt)]
        
        # 如果目前沒有動畫在跑，檢查是否需要進入下一階段
        if not self.animations:
            if self.scene_phase == 'COIN_TOSS':
                # 硬幣擲完了 -> 進入 GAME START
                self.scene_phase = 'GAME_START'
                self.animations.append(GameStartAnimation((self.SCREEN_W, self.SCREEN_H)))
                
            elif self.scene_phase == 'GAME_START':
                # START 字樣跑完了 -> 正式開始打牌
                self.scene_phase = 'PLAYING'

        if self.engine.game_over:
            # 如果還沒觸發過結束動畫，現在觸發
            if not self.end_anim_triggered:
                result = 'DRAW'
                if self.engine.winner_idx == 0: 
                    result = 'WIN'
                elif self.engine.winner_idx == 1: 
                    result = 'LOSE'
                
                self.animations.append(GameEndAnimation((self.SCREEN_W, self.SCREEN_H), result))
                self.end_anim_triggered = True
            
            # 如果動畫播完了 (animations list 變空)，就跳回大廳
            if not self.animations:
                return GOTO_LOBBY
            
            # 如果正在播結束動畫，不需要處理其他輸入，直接返回
            # (這樣動畫會在 draw() 裡面被畫出來)
            return None 
        # ---------------------------
        
        # 3. 若有動畫正在播放 (包含開始動畫)，鎖住輸入
        if self.animations: return None


        # 獲取當前操作玩家 (UI 永遠操作 Player 0)
        # 注意：engine.current_player_idx 指示現在輪到誰
        is_my_turn = (self.engine.current_player_idx == 0)
        
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_card_index = None
        
        # 永遠計算我方手牌 (Player 0)
        self._compute_hand_layout(0)

        if self.state == IDLE:
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(mouse_pos):
                    self.hovered_card_index = i
                    break

        for event in events:
            if event.type == pygame.QUIT:
                return GOTO_LOBBY

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.exit_rect.collidepoint(event.pos):
                    return GOTO_LOBBY
                
                if self.engine.game_over: continue

                # 結束回合
                if self.end_turn_rect.collidepoint(event.pos):
                    if is_my_turn:
                        self.engine.end_turn()
                    self.state = IDLE
                    continue

                # 點擊手牌 (只有我的回合可以動)
                if is_my_turn:
                    for i, r in enumerate(self.card_rects):
                        if r.collidepoint(event.pos):
                            self.state = DRAGGING_CARD
                            self.dragging_card_index = i
                            break
                
                # 點擊場上隨從 (發起攻擊)
                if self.state == IDLE and is_my_turn:
                    # 檢查是否點擊己方隨從
                    my_rects = self._get_minion_rects(0)
                    my_minions = self.engine.players[0].board
                    
                    for idx, rect in enumerate(my_rects):
                        if rect.collidepoint(event.pos):
                            if idx < len(my_minions):
                                m = my_minions[idx]
                                if m.can_attack and not m.has_attacked:
                                    self.state = TARGETING
                                    self.attacker_idx = idx
                            break

            elif event.type == pygame.MOUSEMOTION:
                if self.state == DRAGGING_CARD:
                    self.dragging_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.state == DRAGGING_CARD and self.dragging_card_index is not None:
                    if self.battlefield_rect.collidepoint(event.pos):
                        # 播放卡片
                        # 取得 ID 供動畫使用
                        p0 = self.engine.players[0]
                        if self.dragging_card_index < len(p0.hand):
                            card_id = p0.hand[self.dragging_card_index]['id']
                            
                            success = self.engine.play_card(self.dragging_card_index)
                            if success:
                                center = (self.SCREEN_W // 2, self.SCREEN_H // 2)
                                self.animations.append(CardPopupAnimation(card_id, center))
                            
                    self.state = IDLE
                    self.dragging_card_index = None

                elif self.state == TARGETING:
                    # 尋找目標 (對手隨從)
                    enemy_rects = self._get_minion_rects(1)
                    target_found = None
                    for idx, rect in enumerate(enemy_rects):
                        if rect.collidepoint(event.pos):
                            target_found = idx
                            break

                    if target_found is not None and self.attacker_idx is not None:
                        # 觸發攻擊
                        # 1. 動畫
                        my_rects = self._get_minion_rects(0)
                        if self.attacker_idx < len(my_rects):
                            start_pos = my_rects[self.attacker_idx].center
                            if target_found < len(enemy_rects):
                                end_pos = enemy_rects[target_found].center
                                
                                # 取得 Card ID
                                attacker_card_id = self.engine.players[0].board[self.attacker_idx].card_id
                                anim = AttackAnimation(start_pos, end_pos, attacker_card_id)
                                self.animations.append(anim)
                                
                                # 2. 邏輯
                                self.engine.attack(self.attacker_idx, target_found)
                    
                    self.state = IDLE
                    self.attacker_idx = None

        return None

    def draw(self):
        self.screen.blit(self.bg_image, (0, 0))
        
        pygame.draw.line(self.screen, (100, 100, 100), (0, self.SCREEN_H//2), (self.SCREEN_W, self.SCREEN_H//2), 2)
        
        # 繪製資訊
        self._draw_player_info(0, bottom=True)
        self._draw_player_info(1, bottom=False)
        
        # 繪製隨從
        self._draw_board(0, bottom=True)
        self._draw_board(1, bottom=False)

        # 永遠只畫我的手牌 (Player 0)
        self._draw_hand(0) 
        
        # 拖曳中
        if self.state == DRAGGING_CARD and self.dragging_card_index is not None:
            hand = self.engine.players[0].hand
            if self.dragging_card_index < len(hand):
                card_data = hand[self.dragging_card_index]
                rect = pygame.Rect(self.dragging_pos[0]-50, self.dragging_pos[1]-70, 100, 140)
                self._draw_card_graphic(card_data, rect)

        # 攻擊線
        if self.state == TARGETING and self.attacker_idx is not None:
            my_rects = self._get_minion_rects(0)
            if self.attacker_idx < len(my_rects):
                start_pos = my_rects[self.attacker_idx].center
                end_pos = pygame.mouse.get_pos()
                pygame.draw.line(self.screen, (255, 0, 0), start_pos, end_pos, 4)

        # 按鈕
        is_my_turn = (self.engine.current_player_idx == 0)
        btn_color = (50, 150, 50) if is_my_turn and not self.engine.game_over else (100, 100, 100)
        pygame.draw.rect(self.screen, btn_color, self.end_turn_rect, border_radius=5)
        btn_txt = self.font.render("End Turn", True, (255, 255, 255))
        self.screen.blit(btn_txt, (self.end_turn_rect.x + 10, self.end_turn_rect.y + 10))
        
        pygame.draw.rect(self.screen, (150, 50, 50), self.exit_rect, border_radius=5)
        self.screen.blit(self.font.render("Exit", True, (255,255,255)), (self.exit_rect.x+5, self.exit_rect.y+5))

        # 遊戲結束
        if self.engine.game_over:
            msg = "Game Over! "
            if self.engine.winner_idx == -1: msg += "Draw!"
            elif self.engine.winner_idx == 0: msg += "You Win!"
            else: msg += "You Lose!"
            
            txt = self.font_big.render(msg, True, (255, 255, 0))
            bg_rect = txt.get_rect(center=(self.SCREEN_W//2, self.SCREEN_H//2))
            pygame.draw.rect(self.screen, (0,0,0), bg_rect.inflate(20, 20))
            self.screen.blit(txt, bg_rect)

        # 回合提示
        turn_msg = f"Turn: {self.engine.turn_count} - {'Your Turn' if is_my_turn else 'Opponent Turn'}"
        turn_surf = self.font.render(turn_msg, True, (200, 200, 255))
        self.screen.blit(turn_surf, (20, 20))

        # 動畫
        for anim in self.animations:
            anim.draw(self.screen)

        pygame.display.flip()

    def _draw_player_info(self, p_idx, bottom):
        # 【修正】移除這裡的 self._draw_hand(0) 呼叫，避免遞迴和重複繪製
        p = self.engine.players[p_idx]
        y = self.SCREEN_H - 100 if bottom else 50
        
        mana_str = f"Mana: {p.current_mana}/{p.max_mana}"
        txt = self.font.render(mana_str, True, (100, 100, 255))
        self.screen.blit(txt, (20, y))
        
        # 顯示對手手牌數
        if not bottom:
            deck_str = f"Hand: {len(p.hand)} | Deck: {len(p.deck)}"
        else:
            deck_str = f"Deck: {len(p.deck)}"
            
        txt2 = self.font.render(deck_str, True, (200, 200, 200))
        self.screen.blit(txt2, (20, y + 20))

    def _draw_board(self, p_idx, bottom):
        minions = self.engine.players[p_idx].board
        rects = self._get_minion_rects(p_idx)
        
        for i, m in enumerate(minions):
            if i >= len(rects): break
            rect = rects[i]
            
            # 狀態顏色
            color = (100, 255, 100) if m.can_attack and not m.has_attacked else (200, 200, 200)
            # 對手的怪是紅的
            if p_idx != 0: color = (200, 100, 100)
            
            img = ResourceManager.get_card_image(m.card_id, 80, 80)
            
            pygame.draw.circle(self.screen, color, rect.center, 45)
            thumb = pygame.transform.scale(img, (60, 60))
            self.screen.blit(thumb, (rect.centerx - 30, rect.centery - 30))
            
            atk_txt = self.font.render(str(m.attack_val), True, (255, 255, 0))
            hp_txt = self.font.render(str(m.current_hp), True, (255, 0, 0))
            self.screen.blit(atk_txt, (rect.left, rect.bottom - 20))
            self.screen.blit(hp_txt, (rect.right - 20, rect.bottom - 20))

    def _draw_hand(self, p_idx):
        if self.state == DRAGGING_CARD:
            # 拖曳時不畫原本那張
            cards_to_draw = [c for i, c in enumerate(self.engine.players[p_idx].hand) if i != self.dragging_card_index]
        else:
            cards_to_draw = self.engine.players[p_idx].hand
            
        for i, rect in enumerate(self.card_rects):
            if i >= len(self.engine.players[p_idx].hand): break
            if self.state == DRAGGING_CARD and i == self.dragging_card_index: continue
            
            card_data = self.engine.players[p_idx].hand[i]
            self._draw_card_graphic(card_data, rect)

    def _draw_card_graphic(self, card_data, rect):
        img = ResourceManager.get_card_image(card_data['id'], rect.width, rect.height)
        self.screen.blit(img, rect)
        
        color = (255, 255, 255)
        # 若法力不足變暗
        current_p = self.engine.get_current_player()
        if card_data['cost'] > current_p.current_mana:
            color = (100, 100, 100)
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            self.screen.blit(overlay, rect)
            
        pygame.draw.rect(self.screen, color, rect, 2)
        
        cost_txt = self.font.render(str(card_data['cost']), True, (0, 0, 255))
        pygame.draw.circle(self.screen, (255, 255, 255), (rect.x+15, rect.y+15), 12)
        self.screen.blit(cost_txt, (rect.x+10, rect.y+5))

    def _compute_hand_layout(self, p_idx):
        # 固定只計算 Player 0 (我) 的手牌配置
        hand_len = len(self.engine.players[0].hand)
        card_w, card_h = 100, 140
        gap = 10
        total_w = hand_len * card_w + (hand_len - 1) * gap
        start_x = (self.SCREEN_W - total_w) // 2
        y = self.SCREEN_H - 160
        
        self.card_rects = []
        for i in range(hand_len):
            self.card_rects.append(pygame.Rect(start_x + i*(card_w+gap), y, card_w, card_h))

    def _get_minion_rects(self, p_idx):
        minions = self.engine.players[p_idx].board
        count = len(minions)
        gap = 20
        m_size = 90
        total_w = count * m_size + (count - 1) * gap
        start_x = (self.SCREEN_W - total_w) // 2
        
        y = 400 if p_idx == 0 else 200
        
        rects = []
        for i in range(count):
            rects.append(pygame.Rect(start_x + i*(m_size+gap), y, m_size, m_size))
        return rects
        minions = self.engine.players[p_idx].board
        count = len(minions)
        gap = 20
        m_size = 90
        total_w = count * m_size + (count - 1) * gap
        start_x = (self.SCREEN_W - total_w) // 2
        
        # P0 在下方 (y=400左右), P1 在上方 (y=200左右)
        y = 400 if p_idx == 0 else 200
        
        rects = []
        for i in range(count):
            rects.append(pygame.Rect(start_x + i*(m_size+gap), y, m_size, m_size))
        return rects