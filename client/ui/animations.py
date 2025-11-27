import pygame
import math
from client.utils.resource_manager import ResourceManager

class Animation:
    def update(self, dt):
        return False
    def draw(self, screen):
        pass
    def handle_event(self, event):
        pass

class AttackAnimation(Animation):
    # ... (保持原本的 AttackAnimation 代碼，它沒有效能問題) ...
    def __init__(self, start_pos, end_pos, card_id, width=80, height=80):
        self.start_pos = pygame.Vector2(start_pos)
        self.end_pos = pygame.Vector2(end_pos)
        self.current_pos = pygame.Vector2(start_pos)
        self.image = ResourceManager.get_card_image(card_id, width, height)
        self.total_time = 0.5 
        self.timer = 0.0
        self.phase = 'FORWARD'

    def update(self, dt):
        self.timer += dt
        if self.timer < 0.2:
            t = self.timer / 0.2
            self.current_pos = self.start_pos.lerp(self.end_pos, t)
        elif self.timer < self.total_time:
            self.phase = 'BACK'
            t = (self.timer - 0.2) / 0.3
            self.current_pos = self.end_pos.lerp(self.start_pos, t)
        else:
            return False 
        return True

    def draw(self, screen):
        rect = self.image.get_rect(center=(int(self.current_pos.x), int(self.current_pos.y)))
        screen.blit(self.image, rect)

class PackOpeningAnimation(Animation):
    # ... (保持原本的 PackOpeningAnimation 代碼) ...
    # 這裡的 Surface 雖然有建立，但邏輯比較複雜，且 PackOpeningAnimation 之前已經修正過縮排
    # 建議確保 draw 裡面沒有 `pygame.Surface` 的建立動作
    # 為了節省篇幅，請保留你上次修正縮排後的 PackOpeningAnimation 版本
    # 僅需檢查 draw 方法開頭的 overlay
    
    def __init__(self, screen_size, cards_data):
        self.w, self.h = screen_size
        self.cards = cards_data 
        
        self.pack_w, self.pack_h = 300, 450
        original_pack = ResourceManager.get_pack_image("pack.png", self.pack_w, self.pack_h)
        self.pack_l = original_pack.subsurface((0, 0, self.pack_w//2, self.pack_h)).copy()
        self.pack_r = original_pack.subsurface((self.pack_w//2, 0, self.pack_w//2, self.pack_h)).copy()
        
        self.center_x = self.w // 2
        self.center_y = self.h // 2
        self.offset_x = 0 
        self.state = "IDLE" 
        self.timer = 0.0
        self.light_radius = 0
        self.mouse_points = [] 
        self.is_dragging = False
        self.current_card_idx = 0
        self.card_scale = 0.1
        self.card_alpha = 255
        self.waiting_for_click = False 
        self.sub_animation = None
        
        # 【優化】預先建立半透明背景
        self.overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 200))

    # ... (handle_event, update, check_next_card_rarity 保持不變) ...
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
                xs = [p[0] for p in self.mouse_points]
                if max(xs) - min(xs) > self.pack_w * 0.8:
                    ys = [p[1] for p in self.mouse_points]
                    avg_y = sum(ys) / len(ys)
                    if abs(avg_y - self.center_y) < self.pack_h / 2:
                        self.state = "OPENING"
                        self.timer = 0
        elif self.state == "REVEAL_WAIT":
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.current_card_idx += 1
                if self.current_card_idx >= len(self.cards):
                    self.state = "FINISHED"
                else:
                    self.check_next_card_rarity()

    def update(self, dt):
        if self.state == "FINISHED": return False
        if self.sub_animation:
            if self.sub_animation.update(dt): return True
            else:
                self.sub_animation = None
                self.state = "REVEAL_SHOW"
                self.card_scale = 0.1
                self.timer = 0
                return True
        if self.state == "OPENING":
            self.timer += dt
            if self.timer < 0.5:
                progress = self.timer / 0.5
                self.offset_x = 400 * (progress ** 2)
                self.light_radius = int(300 * progress)
            else:
                self.check_next_card_rarity()
        elif self.state == "REVEAL_SHOW":
            self.timer += dt
            if self.timer < 0.3:
                t = self.timer / 0.3
                self.card_scale = 1.0 + math.sin(t * math.pi) * 0.1 
                if t >= 1: self.card_scale = 1.0
            else:
                self.card_scale = 1.0
                self.state = "REVEAL_WAIT"
        return True

    def check_next_card_rarity(self):
        if self.current_card_idx < len(self.cards):
            card = self.cards[self.current_card_idx]
            if card.get('rarity') == 'Legendary':
                self.state = "PLAY_CUTIN"
                self.sub_animation = LegendaryCutinAnimation((self.w, self.h))
            else:
                self.state = "REVEAL_SHOW"
                self.card_scale = 0.1
                self.timer = 0
        else:
            self.state = "FINISHED"

    def draw(self, screen):
        # 【優化】使用預先建立的 overlay
        screen.blit(self.overlay, (0,0))

        if self.sub_animation:
            self.sub_animation.draw(screen)
            return

        if self.state in ["IDLE", "OPENING"]:
            l_x = self.center_x - self.pack_w // 2 - int(self.offset_x)
            l_y = self.center_y - self.pack_h // 2
            screen.blit(self.pack_l, (l_x, l_y))
            r_x = self.center_x + int(self.offset_x)
            r_y = l_y
            screen.blit(self.pack_r, (r_x, r_y))

        if self.state == "OPENING":
            pygame.draw.circle(screen, (255, 255, 200), (self.center_x, self.center_y), self.light_radius)
            pygame.draw.circle(screen, (255, 255, 255), (self.center_x, self.center_y), int(self.light_radius * 0.7))

        if self.state == "IDLE" and len(self.mouse_points) > 1:
            pygame.draw.lines(screen, (255, 255, 255), False, self.mouse_points, 5)
            font = pygame.font.SysFont(None, 40)
            hint = font.render("<< SWIPE TO OPEN >>", True, (255, 255, 255))
            screen.blit(hint, (self.center_x - hint.get_width()//2, self.center_y + self.pack_h//2 + 20))

        if self.state in ["REVEAL_SHOW", "REVEAL_WAIT"]:
            if self.current_card_idx < len(self.cards):
                card_data = self.cards[self.current_card_idx]
                base_w, base_h = 300, 420
                target_w = int(base_w * self.card_scale)
                target_h = int(base_h * self.card_scale)
                img = ResourceManager.get_card_image(card_data['id'], target_w, target_h)
                img_rect = img.get_rect(center=(self.center_x, self.center_y))
                
                if card_data['rarity'] in ['Legendary', 'Epic']:
                    glow_radius = int(target_w * 0.8)
                    glow_color = (255, 215, 0) if card_data['rarity'] == 'Legendary' else (186, 85, 211)
                    s = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*glow_color, 100), (glow_radius, glow_radius), glow_radius)
                    screen.blit(s, (self.center_x - glow_radius, self.center_y - glow_radius))

                screen.blit(img, img_rect)
                
                if self.state == "REVEAL_WAIT":
                    font = ResourceManager.get_font(48)
                    name_txt = font.render(card_data['name'], True, (255, 255, 255))
                    rarity_font = ResourceManager.get_font(32)
                    rarity_txt = rarity_font.render(card_data['rarity'], True, (200, 200, 200))
                    screen.blit(name_txt, (self.center_x - name_txt.get_width()//2, img_rect.bottom + 20))
                    screen.blit(rarity_txt, (self.center_x - rarity_txt.get_width()//2, img_rect.bottom + 70))
                    
                    small_font = ResourceManager.get_font(30)
                    click_txt = small_font.render("Click to continue...", True, (150, 150, 150))
                    screen.blit(click_txt, (self.center_x - click_txt.get_width()//2, self.h - 50))
                    
                    count_txt = small_font.render(f"{self.current_card_idx + 1} / {len(self.cards)}", True, (255, 255, 255))
                    screen.blit(count_txt, (self.w - 100, self.h - 50))

class CardPopupAnimation(Animation):
    # ... (保持不變) ...
    def __init__(self, card_id, center_pos, duration=1.0):
        self.card_id = card_id
        self.center_pos = center_pos
        self.duration = duration
        self.timer = 0.0
        self.base_image = ResourceManager.get_card_image(card_id, 200, 280)
        self.current_image = self.base_image
        self.alpha = 255

    def update(self, dt):
        self.timer += dt
        if self.timer > self.duration: return False
        progress = self.timer / self.duration
        if progress > 0.7:
            fade_progress = (progress - 0.7) / 0.3
            self.alpha = int(255 * (1 - fade_progress))
            self.base_image.set_alpha(self.alpha)
        return True

    def draw(self, screen):
        rect = self.base_image.get_rect(center=self.center_pos)
        pygame.draw.rect(screen, (255, 255, 200, self.alpha), rect.inflate(10, 10), 3)
        screen.blit(self.base_image, rect)

class CoinTossAnimation(Animation):
    def __init__(self, screen_size, winner_idx):
        self.w, self.h = screen_size
        self.winner_idx = winner_idx
        self.timer = 0.0
        self.duration = 4.0
        self.center = (self.w // 2, self.h // 2)
        
        self.coin_radius = 80
        # 【優化】硬幣表面可以預先畫好，不用每次畫
        self.coin_surf = pygame.Surface((self.coin_radius*2, self.coin_radius*2), pygame.SRCALPHA)
        pygame.draw.circle(self.coin_surf, (255, 215, 0), (self.coin_radius, self.coin_radius), self.coin_radius)
        pygame.draw.circle(self.coin_surf, (255, 255, 100), (self.coin_radius, self.coin_radius), self.coin_radius - 5)
        pygame.draw.circle(self.coin_surf, (180, 140, 0), (self.coin_radius, self.coin_radius), self.coin_radius, 4)
        
        self.font = ResourceManager.get_font(60)
        self.result_text = "YOU GO FIRST" if winner_idx == 0 else "OPPONENT FIRST"
        text_color = (100, 255, 100) if winner_idx == 0 else (255, 100, 100)
        self.text_surf = self.font.render(self.result_text, True, text_color)
        
        # 【優化】背景 Overlay 預先建立
        self.overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 150))

    def update(self, dt):
        self.timer += dt
        if self.timer > self.duration: return False
        return True

    def draw(self, screen):
        # 【優化】直接 Blit 預先建立的 Overlay
        screen.blit(self.overlay, (0, 0))
        
        toss_duration = 2.0
        if self.timer < toss_duration:
            progress = self.timer / toss_duration
            height_offset = math.sin(progress * math.pi) * 300 
            current_y = self.center[1] + 100 - height_offset
            
            rot_speed = 20 * (1 - progress * 0.5) 
            scale_y = abs(math.cos(self.timer * rot_speed))
            
            current_h = int(self.coin_radius * 2 * scale_y)
            if current_h < 2: current_h = 2
            
            scaled_coin = pygame.transform.scale(self.coin_surf, (self.coin_radius*2, current_h))
            rect = scaled_coin.get_rect(center=(self.center[0], int(current_y)))
            screen.blit(scaled_coin, rect)
        else:
            rect = self.coin_surf.get_rect(center=(self.center[0], self.center[1]))
            screen.blit(self.coin_surf, rect)
            
            text_t = self.timer - toss_duration
            scale = min(1.0, text_t * 3)
            
            # 文字縮放會建立新 Surface，但只維持短時間所以還好
            if scale > 0.1:
                w = int(self.text_surf.get_width() * scale)
                h = int(self.text_surf.get_height() * scale)
                scaled_text = pygame.transform.scale(self.text_surf, (w, h))
                text_rect = scaled_text.get_rect(center=(self.center[0], self.center[1] + 120))
                
                bg_rect = text_rect.inflate(20, 10)
                pygame.draw.rect(screen, (0,0,0), bg_rect, border_radius=5)
                screen.blit(scaled_text, text_rect)

class GameStartAnimation(Animation):
    def __init__(self, screen_size):
        self.w, self.h = screen_size
        self.timer = 0.0
        self.duration = 2.0
        
        font = ResourceManager.get_font(80)
        self.text_surf = font.render("BATTLE START", True, (255, 255, 255))
        self.stroke_surf = font.render("BATTLE START", True, (0, 0, 0))
        self.center = (self.w // 2, self.h // 2)
        
        # 【優化】預先建立 Overlay
        self.overlay = pygame.Surface((self.w, 150), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 180)) # 固定透明度，draw 時用 set_alpha 調整

    def update(self, dt):
        self.timer += dt
        if self.timer > self.duration: return False
        return True

    def draw(self, screen):
        alpha = 255
        if self.timer < 0.5:
            alpha = int(255 * (self.timer / 0.5))
        elif self.timer > 1.5:
            alpha = int(255 * ((2.0 - self.timer) / 0.5))
        
        # 設定 Overlay 透明度 (比起重新建立快得多)
        self.overlay.set_alpha(alpha)
        screen.blit(self.overlay, (0, self.center[1] - 75))
        
        self.text_surf.set_alpha(alpha)
        self.stroke_surf.set_alpha(alpha)
        
        scale = 1.0
        if self.timer < 0.3:
            scale = 3.0 - 2.0 * (self.timer / 0.3)
        
        current_w = int(self.text_surf.get_width() * scale)
        current_h = int(self.text_surf.get_height() * scale)
        
        scaled_text = pygame.transform.scale(self.text_surf, (current_w, current_h))
        scaled_stroke = pygame.transform.scale(self.stroke_surf, (current_w, current_h))
        
        rect = scaled_text.get_rect(center=self.center)
        screen.blit(scaled_stroke, (rect.x + 2, rect.y + 2))
        screen.blit(scaled_text, rect)

class GameEndAnimation(Animation):
    def __init__(self, screen_size, result_type):
        self.w, self.h = screen_size
        self.timer = 0.0
        self.duration = 4.0
        
        font = ResourceManager.get_font(100)
        if result_type == 'WIN':
            text = "VICTORY"
            color = (255, 215, 0)
        elif result_type == 'LOSE':
            text = "DEFEAT"
            color = (200, 50, 50)
        else:
            text = "DRAW"
            color = (200, 200, 200)
            
        self.text_surf = font.render(text, True, color)
        self.stroke_surf = font.render(text, True, (0, 0, 0))
        self.center = (self.w // 2, self.h // 2)
        
        # 【優化】預先建立全螢幕 Overlay
        self.overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 255)) # 黑色，之後用 set_alpha 調整

    def update(self, dt):
        self.timer += dt
        if self.timer > self.duration: return False
        return True

    def draw(self, screen):
        # 調整背景透明度
        bg_alpha = min(200, int(200 * (self.timer / 1.0)))
        self.overlay.set_alpha(bg_alpha)
        screen.blit(self.overlay, (0, 0))
        
        offset_y = 0
        if self.timer < 0.5:
            t = self.timer / 0.5
            offset_y = -200 * (1 - t) * (1 - t)
            
        rect = self.text_surf.get_rect(center=(self.center[0], self.center[1] + offset_y))
        screen.blit(self.stroke_surf, (rect.x + 4, rect.y + 4))
        screen.blit(self.text_surf, rect)
        
        if self.timer > 1.5:
            small_font = ResourceManager.get_font(30)
            hint = small_font.render("Returning to Lobby...", True, (255, 255, 255))
            alpha = abs(int(255 * ((self.timer * 2) % 2 - 1)))
            hint.set_alpha(alpha)
            screen.blit(hint, hint.get_rect(center=(self.w//2, self.h - 100)))

class LegendaryCutinAnimation(Animation):
    def __init__(self, screen_size):
        self.w, self.h = screen_size
        self.timer = 0.0
        self.duration = 1.8 
        self.state = "SLIDE_IN"
        
        target_h = int(self.h * 0.9)
        target_w = int(target_h * 1.2) 
        
        self.image = ResourceManager.get_cutin_image("legendary_cutin.png", target_w, target_h)
        self.img_rect = self.image.get_rect()
        
        self.start_x = self.w
        self.end_x = self.w // 2 - self.img_rect.width // 2 
        self.current_x = self.start_x
        self.current_alpha = 255
        
        # 【優化】預先建立 Overlay 與 Flash
        self.overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 255)) # 全黑，用 set_alpha 控制
        
        self.flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.flash.fill((255, 255, 255, 255))

    def update(self, dt):
        self.timer += dt
        if self.timer < 0.3:
            t = self.timer / 0.3
            t = 1 - pow(1 - t, 3)
            self.current_x = self.start_x + (self.end_x - self.start_x) * t
        elif self.timer < 1.5:
            slow_move = (self.timer - 0.3) * 50 
            self.current_x = self.end_x - slow_move
        elif self.timer < 1.8:
            fade_t = (self.timer - 1.5) / 0.3
            self.current_alpha = int(255 * (1 - fade_t))
            self.image.set_alpha(self.current_alpha)
        else:
            return False
        return True

    def draw(self, screen):
        # 1. 背景壓暗
        bg_alpha = 200 if self.timer < 1.5 else int(200 * (self.current_alpha/255))
        self.overlay.set_alpha(bg_alpha)
        screen.blit(self.overlay, (0, 0))
        
        # 2. 畫切入圖
        screen.blit(self.image, (int(self.current_x), self.h // 2 - self.img_rect.height // 2))
        
        # 3. 衝擊閃光
        if 0.25 < self.timer < 0.45:
            flash_alpha = int(255 * (1 - (self.timer - 0.25) / 0.2))
            self.flash.set_alpha(flash_alpha)
            screen.blit(self.flash, (0, 0), special_flags=pygame.BLEND_ADD)