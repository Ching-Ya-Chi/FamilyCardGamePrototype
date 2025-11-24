# client/ui/animations.py

import pygame
from client.utils.resource_manager import ResourceManager

class Animation:
    def update(self, dt):
        """更新動畫狀態，回傳 False 代表動畫結束"""
        return False

    def draw(self, screen):
        """繪製動畫"""
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