# client/ui/Battle_Scene.py

import pygame
from dataclasses import dataclass # 雖然 Engine 有 class，但為了 UI 方便可以用 duck typing
from typing import List, Optional, Tuple
from client.services.game_db_service import service as db_service
from client.utils.resource_manager import ResourceManager
from client.logic.game_engine import GameEngine # 引入引擎
from client.ui.animations import AttackAnimation, CardPopupAnimation

# Constants
IDLE = "IDLE"
DRAGGING_CARD = "DRAGGING_CARD"
TARGETING = "TARGETING"
GOTO_LOBBY = "GOTO_LOBBY"

class BattleScene:
    SCREEN_W = 1280
    SCREEN_H = 720

    def __init__(self, screen, action_callback=None, user_data=None):
        self.screen = screen
        self.action_callback = action_callback # 保留給網路版用，單機版暫時不用
        
        # 1. 初始化引擎
        # 為了測試，我們讓 P1 (自己) 和 P2 (電腦/對手) 都用同一副牌
        # 實際應用中，P1 是 self.user_id，P2 可以是 AI 或網路對手
        my_id = user_data.get('user_id', 1) if user_data else 1
        my_deck = db_service.get_user_deck(my_id)
        if not my_deck: my_deck = [1, 1, 2, 2, 3, 3, 4, 5] * 3 # 沒牌組時的預設牌
        
        # 啟動引擎：P1 是自己，P2 也是假裝用我的牌組
        self.engine = GameEngine(my_id, my_deck, 999, my_deck)
        
        # 為了方便 UI 判斷「我是誰」，我們假設 UI 永遠顯示 self.engine.players[0] 在下方
        # 如果引擎決定 P2 先手，那 UI 下方可能會暫時無法動作，這需要做「視角轉換」，這裡先簡化：
        # 畫面下方永遠是 Engine 的 Player 0，上方是 Player 1
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
        self.attacker_idx = None # 用 index 而不是物件，方便跟 Engine 溝通

        self.battlefield_rect = pygame.Rect(50, 200, 1180, 320)
        self.end_turn_rect = pygame.Rect(1150, 340, 100, 40)
        self.exit_rect = pygame.Rect(self.SCREEN_W - 60, 10, 50, 30)

        # Animation list
        self.animations = []

    def update(self, events):
        # 1. 計算 Delta Time (秒)
        dt = self.clock.tick() / 1000.0 # 轉成秒
        
        # 2. 更新所有動畫
        # 這裡使用 list comprehension 保留還沒結束的動畫 (update 回傳 True 的)
        self.animations = [anim for anim in self.animations if anim.update(dt)]
        
        # 3. 若有動畫正在播放，可以選擇「鎖住輸入」(Block Input)
        if self.animations: return None

        # 簡單判定：如果現在不是我的回合 (Player 0)，就鎖住操作 (或是讓 AI 跑)
        # 這裡為了單機測試，我們允許操作雙方，或者假設我是 Player 0
        current_p_idx = self.engine.current_player_idx
        
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_card_index = None
        
        # 根據當前玩家是誰，計算手牌位置
        self._compute_hand_layout(current_p_idx)

        # Hover 檢測
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
                
                if self.engine.game_over: continue # 遊戲結束不能操作

                # 點擊結束回合
                if self.end_turn_rect.collidepoint(event.pos):
                    self.engine.end_turn()
                    self.state = IDLE
                    continue

                # 點擊手牌 (只有當前玩家可以動手牌)
                for i, r in enumerate(self.card_rects):
                    if r.collidepoint(event.pos):
                        self.state = DRAGGING_CARD
                        self.dragging_card_index = i
                        break
                
                # 點擊場上隨從 (攻擊邏輯)
                if self.state == IDLE:
                    # 檢查是否點擊己方隨從 (發起攻擊)
                    my_minions = self.engine.players[current_p_idx].board
                    enemy_minions = self.engine.players[1 - current_p_idx].board
                    
                    # 計算座標 (下方是 P0, 上方是 P1)
                    # 這裡為了簡單，我們假設 P0 永遠在下方，P1 在上方
                    # 如果 current_player 是 P1，那他操作上方怪去打下方
                    
                    my_rects = self._get_minion_rects(current_p_idx)
                    for idx, rect in enumerate(my_rects):
                        if rect.collidepoint(event.pos):
                            # 檢查是否可攻擊
                            if my_minions[idx].can_attack and not my_minions[idx].has_attacked:
                                self.state = TARGETING
                                self.attacker_idx = idx
                            break

            elif event.type == pygame.MOUSEMOTION:
                if self.state == DRAGGING_CARD:
                    self.dragging_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.state == DRAGGING_CARD and self.dragging_card_index is not None:
                    if self.battlefield_rect.collidepoint(event.pos):
                        # 取得要打出的卡片 ID (為了動畫用)
                        card_to_play = self.engine.players[current_p_idx].hand[self.dragging_card_index]
                        card_id = card_to_play['id']
                        
                        # 執行邏輯
                        success = self.engine.play_card(self.dragging_card_index)
                        
                        if success:
                            # --- 觸發出牌動畫 ---
                            # 在螢幕正中央顯示大卡片
                            center = (self.SCREEN_W // 2, self.SCREEN_H // 2)
                            self.animations.append(CardPopupAnimation(card_id, center))
                            # -------------------
                            
                    self.state = IDLE
                    self.dragging_card_index = None

                elif self.state == TARGETING:
                    # ... (尋找目標代碼) ...
                    enemy_idx = 1 - current_p_idx
                    enemy_rects = self._get_minion_rects(enemy_idx)
                    target_found = None
                    for idx, rect in enumerate(enemy_rects):
                        if rect.collidepoint(event.pos):
                            target_found = idx
                            break

                    if target_found is not None:
                        # --- 觸發攻擊動畫 ---
                        # 1. 取得攻擊者和目標的螢幕座標
                        # 攻擊者是己方 (attacker_idx)
                        my_rects = self._get_minion_rects(current_p_idx)
                        attacker_rect = my_rects[self.attacker_idx]
                        
                        # 目標是敵方 (target_found)
                        enemy_rects = self._get_minion_rects(1 - current_p_idx)
                        target_rect = enemy_rects[target_found]
                        
                        # 取得攻擊者的 Card ID
                        attacker_card_id = self.engine.players[current_p_idx].board[self.attacker_idx].card_id
                        
                        # 加入動畫 (從攻擊者位置 -> 衝向目標中心)
                        anim = AttackAnimation(
                            start_pos=attacker_rect.center, 
                            end_pos=target_rect.center, 
                            card_id=attacker_card_id
                        )
                        self.animations.append(anim)
                        # -------------------

                        # 執行邏輯 (傷害計算)
                        self.engine.attack(self.attacker_idx, target_found)
                    
                    self.state = IDLE
                    self.attacker_idx = None

        return None

    def draw(self):
        self.screen.blit(self.bg_image, (0, 0))
        
        # 繪製戰場分界線
        pygame.draw.line(self.screen, (100, 100, 100), (0, self.SCREEN_H//2), (self.SCREEN_W, self.SCREEN_H//2), 2)
        
        # 繪製雙方資訊 (P0 下方, P1 上方)
        self._draw_player_info(0, bottom=True)
        self._draw_player_info(1, bottom=False)
        
        # 繪製隨從
        self._draw_board(0, bottom=True)
        self._draw_board(1, bottom=False)

        # 繪製當前玩家手牌
        current_p = self.engine.current_player_idx
        # 這裡有個設計選擇：是否要畫對手手牌背面？先只畫當前玩家的手牌
        self._draw_hand(current_p)
        
        # 拖曳中的卡片
        if self.state == DRAGGING_CARD and self.dragging_card_index is not None:
            card_data = self.engine.players[current_p].hand[self.dragging_card_index]
            # 簡單畫一個跟著滑鼠的卡
            rect = pygame.Rect(self.dragging_pos[0]-50, self.dragging_pos[1]-70, 100, 140)
            ResourceManager.get_card_image(card_data['id'], 100, 140) # 確保載入
            self._draw_card_graphic(card_data, rect)

        # 攻擊連線
        if self.state == TARGETING and self.attacker_idx is not None:
            start_rects = self._get_minion_rects(current_p)
            if self.attacker_idx < len(start_rects):
                start_pos = start_rects[self.attacker_idx].center
                end_pos = pygame.mouse.get_pos()
                pygame.draw.line(self.screen, (255, 0, 0), start_pos, end_pos, 4)

        # 結束回合按鈕
        btn_color = (50, 150, 50) if not self.engine.game_over else (100, 100, 100)
        pygame.draw.rect(self.screen, btn_color, self.end_turn_rect, border_radius=5)
        btn_txt = self.font.render("End Turn", True, (255, 255, 255))
        self.screen.blit(btn_txt, (self.end_turn_rect.x + 10, self.end_turn_rect.y + 10))
        
        # 退出按鈕
        pygame.draw.rect(self.screen, (150, 50, 50), self.exit_rect, border_radius=5)
        self.screen.blit(self.font.render("Exit", True, (255,255,255)), (self.exit_rect.x+5, self.exit_rect.y+5))

        # 遊戲結束訊息
        if self.engine.game_over:
            msg = "Game Over! "
            if self.engine.winner_idx == -1: msg += "Draw!"
            elif self.engine.winner_idx == 0: msg += "Bottom Player Wins!"
            else: msg += "Top Player Wins!"
            
            txt = self.font_big.render(msg, True, (255, 255, 0))
            bg_rect = txt.get_rect(center=(self.SCREEN_W//2, self.SCREEN_H//2))
            pygame.draw.rect(self.screen, (0,0,0), bg_rect.inflate(20, 20))
            self.screen.blit(txt, bg_rect)

        # 顯示當前是誰的回合
        turn_msg = f"Turn: {self.engine.turn_count} - Player {current_p + 1}'s Turn"
        turn_surf = self.font.render(turn_msg, True, (200, 200, 255))
        self.screen.blit(turn_surf, (20, 20))

        # 繪製所有動畫 (畫在最上層)
        for anim in self.animations:
            anim.draw(self.screen)

        pygame.display.flip()

    def _draw_player_info(self, p_idx, bottom):
        p = self.engine.players[p_idx]
        y = self.SCREEN_H - 100 if bottom else 50
        
        # Mana
        mana_str = f"Mana: {p.current_mana}/{p.max_mana}"
        txt = self.font.render(mana_str, True, (100, 100, 255))
        self.screen.blit(txt, (20, y))
        
        # Deck count
        deck_str = f"Deck: {len(p.deck)}"
        txt2 = self.font.render(deck_str, True, (200, 200, 200))
        self.screen.blit(txt2, (20, y + 20))

    def _draw_board(self, p_idx, bottom):
        minions = self.engine.players[p_idx].board
        rects = self._get_minion_rects(p_idx)
        
        for i, m in enumerate(minions):
            rect = rects[i]
            # 畫圓形或方形代表隨從
            color = (100, 255, 100) if m.can_attack and not m.has_attacked else (200, 200, 200)
            if p_idx != self.engine.current_player_idx: color = (200, 100, 100) # 敵人紅色
            
            # 使用圖片
            img = ResourceManager.get_card_image(m.card_id, 80, 80)
            
            # 圓形裁切效果 (簡單做)
            pygame.draw.circle(self.screen, color, rect.center, 45) # 外框 (狀態顏色)
            
            # 畫圖片在中間
            # 為了讓圖片適應圓形，通常會用遮罩，這裡直接貼上去簡單點
            thumb = pygame.transform.scale(img, (60, 60))
            self.screen.blit(thumb, (rect.centerx - 30, rect.centery - 30))
            
            # 攻/血
            atk_txt = self.font.render(str(m.attack_val), True, (255, 255, 0))
            hp_txt = self.font.render(str(m.current_hp), True, (255, 0, 0))
            self.screen.blit(atk_txt, (rect.left, rect.bottom - 20))
            self.screen.blit(hp_txt, (rect.right - 20, rect.bottom - 20))

    def _draw_hand(self, p_idx):
        # 只畫當前操作者的手牌
        if self.state == DRAGGING_CARD:
            # 拖曳時不畫原本那張
            cards_to_draw = [c for i, c in enumerate(self.engine.players[p_idx].hand) if i != self.dragging_card_index]
            original_count = len(self.engine.players[p_idx].hand)
        else:
            cards_to_draw = self.engine.players[p_idx].hand
            original_count = len(cards_to_draw)
            
        # 重新計算 rects (因為可能有卡被拿起來)
        # 這裡為了簡單，直接用 self.card_rects，但要注意 dragging 的索引對應
        for i, rect in enumerate(self.card_rects):
            if i >= len(self.engine.players[p_idx].hand): break
            if self.state == DRAGGING_CARD and i == self.dragging_card_index: continue
            
            card_data = self.engine.players[p_idx].hand[i]
            self._draw_card_graphic(card_data, rect)

    def _draw_card_graphic(self, card_data, rect):
        # 使用 ResourceManager
        img = ResourceManager.get_card_image(card_data['id'], rect.width, rect.height)
        self.screen.blit(img, rect)
        
        # 邊框
        color = (255, 255, 255)
        # 若法力不足變暗
        current_p = self.engine.get_current_player()
        if card_data['cost'] > current_p.current_mana:
            color = (100, 100, 100)
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            self.screen.blit(overlay, rect)
            
        pygame.draw.rect(self.screen, color, rect, 2)
        
        # 費用
        cost_txt = self.font.render(str(card_data['cost']), True, (0, 0, 255))
        pygame.draw.circle(self.screen, (255, 255, 255), (rect.x+15, rect.y+15), 12)
        self.screen.blit(cost_txt, (rect.x+10, rect.y+5))

    def _compute_hand_layout(self, p_idx):
        hand_len = len(self.engine.players[p_idx].hand)
        card_w, card_h = 100, 140
        gap = 10
        total_w = hand_len * card_w + (hand_len - 1) * gap
        start_x = (self.SCREEN_W - total_w) // 2
        y = self.SCREEN_H - 160 # 固定在下方
        
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
        
        # P0 在下方 (y=400左右), P1 在上方 (y=200左右)
        y = 400 if p_idx == 0 else 200
        
        rects = []
        for i in range(count):
            rects.append(pygame.Rect(start_x + i*(m_size+gap), y, m_size, m_size))
        return rects