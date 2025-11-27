# client/ui/animations.py

import pygame
import math
from client.utils.resource_manager import ResourceManager

class Animation:
    def update(self, dt):
        """更新動畫狀態，回傳 False 代表動畫結束"""
        return False

    def draw(self, screen):
        """繪製動畫"""
        pass

    def handle_event(self, event):
        pass

class AttackAnimation(Animation):
    """
    攻擊動畫：卡牌衝向目標，然後彈回原位
    """
    def __init__(self, start_pos, end_pos, card_id, width=80, height=80):
        self.start_pos = pygame.Vector2(start_pos)
        self.end_pos = pygame.Vector2(end_pos)
        self.current_pos = pygame.Vector2(start_pos)
        
        # 取得圖片
        self.image = ResourceManager.get_card_image(card_id, width, height)
        
        # 動畫參數
        self.total_time = 0.5  # 總共 0.5 秒
        self.timer = 0.0
        self.phase = 'FORWARD' # FORWARD -> BACK

    def update(self, dt):
        self.timer += dt
        
        # 前半段：衝刺 (0 ~ 0.2秒)
        if self.timer < 0.2:
            t = self.timer / 0.2
            # 線性插值 (Lerp)
            self.current_pos = self.start_pos.lerp(self.end_pos, t)
        
        # 後半段：返回 (0.2 ~ 0.5秒)
        elif self.timer < self.total_time:
            self.phase = 'BACK'
            t = (self.timer - 0.2) / 0.3
            self.current_pos = self.end_pos.lerp(self.start_pos, t)
        
        # 結束
        else:
            return False # Animation finished
        
        return True # Continue

    def draw(self, screen):
        # 畫在計算出的位置
        rect = self.image.get_rect(center=(int(self.current_pos.x), int(self.current_pos.y)))
        screen.blit(self.image, rect)

class PackOpeningAnimation(Animation):
    """
    互動式卡包開啟動畫
    階段：
    1. IDLE: 卡包在中間，背景變暗，等待滑鼠滑過
    2. SWIPING: 偵測滑鼠軌跡，產生切割特效
    3. OPENING: 卡包分成兩半往左右飛，發出強光
    4. REVEALING: 卡片依序彈出顯示
    """
    def __init__(self, screen_size, cards_data):
        self.w, self.h = screen_size
        self.cards = cards_data # 這是抽到的卡片列表 (1張或10張)
        self.waiting_for_click = False 
    
        # --- 新增：互動冷卻時間 ---
        self.input_cooldown = 0.5 # 0.5秒內不接收輸入
        # 載入卡包圖
        self.pack_w, self.pack_h = 300, 450
        original_pack = ResourceManager.get_pack_image("pack.png", self.pack_w, self.pack_h)
        
        # 將卡包切成左右兩半 (為了撕開效果)
        self.pack_l = original_pack.subsurface((0, 0, self.pack_w//2, self.pack_h)).copy()
        self.pack_r = original_pack.subsurface((self.pack_w//2, 0, self.pack_w//2, self.pack_h)).copy()
        
        # 初始位置
        self.center_x = self.w // 2
        self.center_y = self.h // 2
        self.offset_x = 0 # 撕開的距離
        
        # 狀態
        self.state = "IDLE" # IDLE, OPENING, REVEAL_WAIT, REVEAL_SHOW, FINISHED
        self.timer = 0.0
        self.light_radius = 0
        
        # 互動相關
        self.mouse_points = [] # 紀錄滑鼠軌跡
        self.is_dragging = False
        
        # 卡片展示相關
        self.current_card_idx = 0
        self.card_scale = 0.1
        self.card_alpha = 255
        self.waiting_for_click = False # 顯示卡片後等待點擊下一張

    def handle_event(self, event):
        if self.state == "IDLE":
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.is_dragging = True
                self.mouse_points = [event.pos]
            elif event.type == pygame.MOUSEBUTTONUP:
                self.is_dragging = False
                self.mouse_points = []
            elif event.type == pygame.MOUSEMOTION and self.is_dragging:
                self.mouse_points.append(event.pos)
                if len(self.mouse_points) > 10:
                    self.mouse_points.pop(0)
                
                # 簡單判定：是否有橫向穿越卡包
                # 檢查軌跡中最左和最右的點
                xs = [p[0] for p in self.mouse_points]
                if max(xs) - min(xs) > self.pack_w * 0.8:
                    # 檢查是否在卡包高度範圍內
                    ys = [p[1] for p in self.mouse_points]
                    avg_y = sum(ys) / len(ys)
                    if abs(avg_y - self.center_y) < self.pack_h / 2:
                        # 觸發開啟！
                        self.state = "OPENING"
                        self.timer = 0
        
        elif self.state == "REVEAL_WAIT":
            # 點擊以繼續
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.current_card_idx += 1
                if self.current_card_idx >= len(self.cards):
                    self.state = "FINISHED"
                else:
                    # 重置卡片動畫參數
                    self.state = "REVEAL_SHOW"
                    self.card_scale = 0.1
                    self.timer = 0

    def update(self, dt):
        # --- 新增：更新冷卻 ---
        if self.input_cooldown > 0:
            self.input_cooldown -= dt
        # -------------------
        if self.state == "FINISHED":
            return False

        if self.state == "OPENING":
            self.timer += dt
            # 撕開動畫 (0.5秒)
            if self.timer < 0.5:
                progress = self.timer / 0.5
                self.offset_x = 400 * (progress ** 2) # 加速分開
                self.light_radius = int(300 * progress)
            else:
                self.state = "REVEAL_SHOW"
                self.card_scale = 0.1
                self.timer = 0
        
        elif self.state == "REVEAL_SHOW":
            self.timer += dt
            # 卡片放大出現 (0.3秒)
            if self.timer < 0.3:
                t = self.timer / 0.3
                # 彈性效果 (Overshoot)
                self.card_scale = 1.0 + math.sin(t * math.pi) * 0.1 
                if t >= 1: self.card_scale = 1.0
            else:
                self.card_scale = 1.0
                self.state = "REVEAL_WAIT"
        
        return True

    def draw(self, screen):
        # 1. 畫半透明背景 (Dim Background)
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0,0))

        # 2. 畫卡包 (左右兩半)
        if self.state in ["IDLE", "OPENING"]:
            # 左半
            l_x = self.center_x - self.pack_w // 2 - int(self.offset_x)
            l_y = self.center_y - self.pack_h // 2
            screen.blit(self.pack_l, (l_x, l_y))
            
            # 右半
            r_x = self.center_x + int(self.offset_x)
            r_y = l_y
            screen.blit(self.pack_r, (r_x, r_y))

        # 3. 畫光芒 (Opening 時)
        if self.state == "OPENING":
            pygame.draw.circle(screen, (255, 255, 200), (self.center_x, self.center_y), self.light_radius)
            # 再畫一個核心白光
            pygame.draw.circle(screen, (255, 255, 255), (self.center_x, self.center_y), int(self.light_radius * 0.7))

        # 4. 畫滑鼠軌跡 (IDLE 時)
        if self.state == "IDLE" and len(self.mouse_points) > 1:
            pygame.draw.lines(screen, (255, 255, 255), False, self.mouse_points, 5)
            # 提示文字
            font = pygame.font.SysFont(None, 40)
            hint = font.render("<< SWIPE TO OPEN >>", True, (255, 255, 255))
            screen.blit(hint, (self.center_x - hint.get_width()//2, self.center_y + self.pack_h//2 + 20))

        # 5. 畫卡片 (展示階段)
        if self.state in ["REVEAL_SHOW", "REVEAL_WAIT"]:
            if self.current_card_idx < len(self.cards):
                card_data = self.cards[self.current_card_idx]
                
                # 基礎尺寸
                base_w, base_h = 300, 420
                target_w = int(base_w * self.card_scale)
                target_h = int(base_h * self.card_scale)
                
                img = ResourceManager.get_card_image(card_data['id'], target_w, target_h)
                img_rect = img.get_rect(center=(self.center_x, self.center_y))
                
                # 發光背景 (針對稀有卡)
                if card_data['rarity'] in ['Legendary', 'Epic']:
                    glow_radius = int(target_w * 0.8)
                    glow_color = (255, 215, 0) if card_data['rarity'] == 'Legendary' else (186, 85, 211)
                    s = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*glow_color, 100), (glow_radius, glow_radius), glow_radius)
                    screen.blit(s, (self.center_x - glow_radius, self.center_y - glow_radius))

                screen.blit(img, img_rect)
                
                # 畫卡片資訊
                if self.state == "REVEAL_WAIT":
                    # 顯示名字
                    font = pygame.font.SysFont("arial", 48, bold=True)
                    name_txt = font.render(card_data['name'], True, (255, 255, 255))
                    rarity_txt = font.render(card_data['rarity'], True, (200, 200, 200))
                    
                    screen.blit(name_txt, (self.center_x - name_txt.get_width()//2, img_rect.bottom + 20))
                    screen.blit(rarity_txt, (self.center_x - rarity_txt.get_width()//2, img_rect.bottom + 70))
                    
                    # 提示點擊
                    small_font = pygame.font.SysFont(None, 30)
                    click_txt = small_font.render("Click to continue...", True, (150, 150, 150))
                    screen.blit(click_txt, (self.center_x - click_txt.get_width()//2, self.h - 50))
                    
                    # 顯示第幾張
                    count_txt = small_font.render(f"{self.current_card_idx + 1} / {len(self.cards)}", True, (255, 255, 255))
                    screen.blit(count_txt, (self.w - 100, self.h - 50))

class CardPopupAnimation(Animation):
    """
    出牌動畫：卡牌在畫面中央放大顯示，然後淡出
    """
    def __init__(self, card_id, center_pos, duration=1.0):
        self.card_id = card_id
        self.center_pos = center_pos
        self.duration = duration
        self.timer = 0.0
        
        # 原始大圖
        self.base_image = ResourceManager.get_card_image(card_id, 200, 280)
        self.current_image = self.base_image
        self.alpha = 255

    def update(self, dt):
        self.timer += dt
        if self.timer > self.duration:
            return False
        
        # 計算進度 0.0 ~ 1.0
        progress = self.timer / self.duration
        
        # 特效：前 0.2 秒放大，後面 0.8 秒慢慢變透明
        if progress > 0.7:
            # 最後 30% 時間淡出
            fade_progress = (progress - 0.7) / 0.3
            self.alpha = int(255 * (1 - fade_progress))
            self.base_image.set_alpha(self.alpha)
        
        return True

    def draw(self, screen):
        rect = self.base_image.get_rect(center=self.center_pos)
        
        # 畫一個邊框光暈效果
        pygame.draw.rect(screen, (255, 255, 200, self.alpha), rect.inflate(10, 10), 3)
        screen.blit(self.base_image, rect)

class GameStartAnimation(Animation):
    """
    對局開始動畫：BATTLE START 文字飛入或淡入
    """
    def __init__(self, screen_size):
        self.w, self.h = screen_size
        self.timer = 0.0
        self.duration = 2.0 # 持續 2 秒
        
        font = pygame.font.SysFont("arial", 80, bold=True)
        self.text_surf = font.render("BATTLE START", True, (255, 255, 255))
        # 加個邊框讓字清楚
        self.stroke_surf = font.render("BATTLE START", True, (0, 0, 0))
        
        self.center = (self.w // 2, self.h // 2)

    def update(self, dt):
        self.timer += dt
        if self.timer > self.duration:
            return False
        return True

    def draw(self, screen):
        # 半透明黑底條
        overlay = pygame.Surface((self.w, 150), pygame.SRCALPHA)
        
        # 動畫效果：前 0.5 秒淡入，最後 0.5 秒淡出
        alpha = 255
        if self.timer < 0.5:
            alpha = int(255 * (self.timer / 0.5))
        elif self.timer > 1.5:
            alpha = int(255 * ((2.0 - self.timer) / 0.5))
        
        overlay.fill((0, 0, 0, int(alpha * 0.7))) # 背景透明度
        screen.blit(overlay, (0, self.center[1] - 75))
        
        # 文字
        self.text_surf.set_alpha(alpha)
        self.stroke_surf.set_alpha(alpha)
        
        # 稍微縮放效果 (Scale)
        scale = 1.0
        if self.timer < 0.3:
            scale = 3.0 - 2.0 * (self.timer / 0.3) # 從 3倍大縮小到 1倍
        
        current_w = int(self.text_surf.get_width() * scale)
        current_h = int(self.text_surf.get_height() * scale)
        
        scaled_text = pygame.transform.scale(self.text_surf, (current_w, current_h))
        scaled_stroke = pygame.transform.scale(self.stroke_surf, (current_w, current_h))
        
        rect = scaled_text.get_rect(center=self.center)
        
        # 畫陰影/邊框
        screen.blit(scaled_stroke, (rect.x + 2, rect.y + 2))
        screen.blit(scaled_text, rect)


class GameEndAnimation(Animation):
    """
    對局結束動畫：顯示 VICTORY / DEFEAT，並強制覆蓋全螢幕
    """
    def __init__(self, screen_size, result_type):
        # result_type: 'WIN', 'LOSE', 'DRAW'
        self.w, self.h = screen_size
        self.timer = 0.0
        self.duration = 4.0 # 顯示久一點，讓玩家看清楚
        
        font = pygame.font.SysFont("arial", 100, bold=True)
        
        if result_type == 'WIN':
            text = "VICTORY"
            color = (255, 215, 0) # 金色
        elif result_type == 'LOSE':
            text = "DEFEAT"
            color = (200, 50, 50) # 紅色
        else:
            text = "DRAW"
            color = (200, 200, 200) # 灰色
            
        self.text_surf = font.render(text, True, color)
        self.stroke_surf = font.render(text, True, (0, 0, 0))
        self.center = (self.w // 2, self.h // 2)

    def update(self, dt):
        self.timer += dt
        if self.timer > self.duration:
            return False # 動畫結束 -> Scene 偵測到結束後會跳轉
        return True

    def draw(self, screen):
        # 全螢幕漸漸變黑
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        bg_alpha = min(200, int(200 * (self.timer / 1.0))) # 1秒內變黑
        overlay.fill((0, 0, 0, bg_alpha))
        screen.blit(overlay, (0, 0))
        
        # 文字從上掉下來或是放大
        offset_y = 0
        if self.timer < 0.5:
            # 彈跳效果 (Bounce)
            t = self.timer / 0.5
            offset_y = -200 * (1 - t) * (1 - t)
            
        rect = self.text_surf.get_rect(center=(self.center[0], self.center[1] + offset_y))
        
        screen.blit(self.stroke_surf, (rect.x + 4, rect.y + 4))
        screen.blit(self.text_surf, rect)
        
        # 提示文字
        if self.timer > 1.5:
            small_font = pygame.font.SysFont("arial", 30)
            hint = small_font.render("Returning to Lobby...", True, (255, 255, 255))
            
            # 閃爍
            alpha = abs(int(255 * ((self.timer * 2) % 2 - 1)))
            hint.set_alpha(alpha)
            
            screen.blit(hint, hint.get_rect(center=(self.w//2, self.h - 100)))

class CoinTossAnimation(Animation):
    """
    擲硬幣動畫：硬幣拋起、旋轉、落下，最後顯示誰先攻
    """
    def __init__(self, screen_size, winner_idx):
        # winner_idx: 0 = 我方先攻, 1 = 對方先攻
        self.w, self.h = screen_size
        self.winner_idx = winner_idx
        
        self.timer = 0.0
        self.duration = 4.0 # 總時長
        self.center = (self.w // 2, self.h // 2)
        
        # 硬幣外觀
        self.coin_radius = 80
        self.coin_surf = pygame.Surface((self.coin_radius*2, self.coin_radius*2), pygame.SRCALPHA)
        # 金色外圈
        pygame.draw.circle(self.coin_surf, (255, 215, 0), (self.coin_radius, self.coin_radius), self.coin_radius)
        # 亮黃色內圈
        pygame.draw.circle(self.coin_surf, (255, 255, 100), (self.coin_radius, self.coin_radius), self.coin_radius - 5)
        # 邊框
        pygame.draw.circle(self.coin_surf, (180, 140, 0), (self.coin_radius, self.coin_radius), self.coin_radius, 4)
        
        # 字體
        self.font = pygame.font.SysFont("arial", 60, bold=True)
        self.result_text = "YOU GO FIRST" if winner_idx == 0 else "OPPONENT FIRST"
        text_color = (100, 255, 100) if winner_idx == 0 else (255, 100, 100)
        self.text_surf = self.font.render(self.result_text, True, text_color)
        
        # 狀態
        self.state = "TOSSING" # TOSSING -> LANDED -> FINISHED

    def update(self, dt):
        self.timer += dt
        
        # 3秒後結束動畫
        if self.timer > self.duration:
            return False
            
        return True

    def draw(self, screen):
        # 1. 畫半透明黑底
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        
        # 2. 計算硬幣物理 (拋物線 Y)
        # 0~2秒拋起落下
        toss_duration = 2.0
        
        if self.timer < toss_duration:
            # 拋物線公式: h = v0*t - 0.5*g*t^2
            # 簡化版：用 sin 模擬高度變化 0 -> 1 -> 0
            progress = self.timer / toss_duration
            height_offset = math.sin(progress * math.pi) * 300 # 最高飛 300px
            current_y = self.center[1] + 100 - height_offset # +100 是起始位置稍微偏下
            
            # 旋轉效果 (Scale Y)
            # 旋轉速度隨時間變慢
            rot_speed = 20 * (1 - progress * 0.5) 
            scale_y = abs(math.cos(self.timer * rot_speed))
            
            # 繪製旋轉硬幣
            current_h = int(self.coin_radius * 2 * scale_y)
            if current_h < 2: current_h = 2 # 避免變 0
            
            scaled_coin = pygame.transform.scale(self.coin_surf, (self.coin_radius*2, current_h))
            rect = scaled_coin.get_rect(center=(self.center[0], int(current_y)))
            screen.blit(scaled_coin, rect)
            
        else:
            # 落地顯示結果
            # 硬幣定格
            rect = self.coin_surf.get_rect(center=(self.center[0], self.center[1]))
            screen.blit(self.coin_surf, rect)
            
            # 顯示文字 (彈出效果)
            text_t = self.timer - toss_duration
            scale = min(1.0, text_t * 3) # 快速放大
            
            w = int(self.text_surf.get_width() * scale)
            h = int(self.text_surf.get_height() * scale)
            scaled_text = pygame.transform.scale(self.text_surf, (w, h))
            
            text_rect = scaled_text.get_rect(center=(self.center[0], self.center[1] + 120))
            
            # 加個黑框底讓字清楚
            bg_rect = text_rect.inflate(20, 10)
            if scale > 0.1:
                pygame.draw.rect(screen, (0,0,0), bg_rect, border_radius=5)
                screen.blit(scaled_text, text_rect)