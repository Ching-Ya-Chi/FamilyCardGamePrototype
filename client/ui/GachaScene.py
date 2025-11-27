import pygame
from client.logic.gacha_engine import GachaEngine
from client.ui.animations import PackOpeningAnimation 
from client.utils.resource_manager import ResourceManager

class GachaScene:
    def __init__(self, screen, user_data=None):
        self.screen = screen
        self.width, self.height = screen.get_size()
        self.user = user_data or {}
        self.user_id = self.user.get('user_id', 1)
        
        self.engine = GachaEngine(self.user_id)
        
        pygame.font.init()
        self.font = ResourceManager.get_font(24)
        self.title_font = ResourceManager.get_font(48)
        self.info_font = ResourceManager.get_font(32)
        
        self.bg_color = (30, 30, 45)
        
        # UI 元件
        # 單抽按鈕 (偏左)
        self.draw_one_btn = pygame.Rect(self.width//2 - 220, self.height - 120, 200, 60)
        # 十連抽按鈕 (偏右)
        self.draw_ten_btn = pygame.Rect(self.width//2 + 20, self.height - 120, 200, 60)
        
        self.back_btn_rect = pygame.Rect(20, 20, 100, 40)
        
        self.animations = []
        self.clock = pygame.time.Clock()
        
        self.message = f"Cost: 100 Gold / Draw"
        self.box_state = self.engine.get_box_info()

    def update(self, events):
        dt = self.clock.tick() / 1000.0
        
        # 更新動畫
        active_anims = []
        for anim in self.animations:
            if anim.update(dt):
                active_anims.append(anim)
        self.animations = active_anims
        
        # 若有動畫，鎖住底部按鈕，但允許動畫接收事件
        is_animating = len(self.animations) > 0

        for ev in events:
            # 如果有動畫，把事件傳給動畫處理 (為了滑動開包和點擊切換卡片)
            if is_animating:
                for anim in self.animations:
                    if hasattr(anim, 'handle_event'):
                        anim.handle_event(ev)
                # 動畫期間，只允許 QUIT，不允許點擊背景按鈕
                if ev.type == pygame.QUIT: return "GOTO_LOBBY"
                continue 

            # 一般 UI 事件
            if ev.type == pygame.QUIT:
                return "GOTO_LOBBY"
            
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.back_btn_rect.collidepoint(ev.pos):
                    return "GOTO_LOBBY"
                
                if self.draw_one_btn.collidepoint(ev.pos):
                    self.perform_draw(count=1)
                
                if self.draw_ten_btn.collidepoint(ev.pos):
                    self.perform_draw(count=10)
                    
        return None

    def perform_draw(self, count=1):
        if count == 1:
            result = self.engine.draw_one()
            if result['success']:
                cards = [result['card']]
            else:
                self.message = f"Failed: {result['message']}"
                return
        else:
            result = self.engine.draw_ten()
            if result['success']:
                cards = result['cards']
            else:
                self.message = f"Failed: {result['message']}"
                return

        # 成功抽到卡片，啟動開包動畫
        # 無論是 1 張還是 10 張，都傳給動畫物件，它會依序顯示
        anim = PackOpeningAnimation((self.width, self.height), cards)
        self.animations.append(anim)
        
        self.message = f"Drew {len(cards)} cards!"
        self.box_state = self.engine.get_box_info()

    def draw(self):
        self.screen.fill(self.bg_color)
        
        title = self.title_font.render("Seasonal Gacha Box", True, (255, 215, 0))
        self.screen.blit(title, (self.width//2 - title.get_width()//2, 40))
        
        if self.box_state:
            self.draw_box_info()

        # 按鈕樣式
        btn_active_color = (50, 180, 100)
        btn_disabled_color = (80, 80, 80)
        is_animating = len(self.animations) > 0
        curr_color = btn_disabled_color if is_animating else btn_active_color

        # Draw 1 Button
        pygame.draw.rect(self.screen, curr_color, self.draw_one_btn, border_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), self.draw_one_btn, 2, border_radius=10)
        txt1 = self.info_font.render("Draw 1", True, (255, 255, 255))
        self.screen.blit(txt1, txt1.get_rect(center=self.draw_one_btn.center))

        # Draw 10 Button (金色邊框)
        pygame.draw.rect(self.screen, curr_color, self.draw_ten_btn, border_radius=10)
        pygame.draw.rect(self.screen, (255, 215, 0), self.draw_ten_btn, 3, border_radius=10)
        txt10 = self.info_font.render("Draw 10", True, (255, 215, 0))
        self.screen.blit(txt10, txt10.get_rect(center=self.draw_ten_btn.center))

        # Back
        pygame.draw.rect(self.screen, (150, 50, 50), self.back_btn_rect, border_radius=5)
        back_txt = self.font.render("Back", True, (255, 255, 255))
        self.screen.blit(back_txt, back_txt.get_rect(center=self.back_btn_rect.center))

        # 訊息 (提示使用者操作)
        # 如果有動畫且狀態是 IDLE，提示使用者劃開
        if self.animations and hasattr(self.animations[0], 'state') and self.animations[0].state == 'IDLE':
            hint = ">> SWIPE THE PACK TO OPEN! <<"
            hint_surf = self.info_font.render(hint, True, (255, 255, 0))
            self.screen.blit(hint_surf, hint_surf.get_rect(center=(self.width//2, self.height - 80)))
        else:
            msg_surf = self.font.render(self.message, True, (200, 200, 200))
            self.screen.blit(msg_surf, msg_surf.get_rect(center=(self.width//2, self.height - 40)))

        # 動畫 (最上層)
        for anim in self.animations:
            anim.draw(self.screen)

    def draw_box_info(self):
        """繪製剩餘卡量的視覺化圖表"""
        # 定義顯示設定
        rarity_config = [
            ("Legendary", self.box_state.get('legend_count', 0), (255, 140, 0)),   # 橘色
            ("Epic",      self.box_state.get('epic_count', 0),   (186, 85, 211)),  # 紫色
            ("Rare",      self.box_state.get('rare_count', 0),   (0, 191, 255)),   # 藍色
            ("Common",    self.box_state.get('common_count', 0), (169, 169, 169)), # 灰色
        ]
        
        start_y = 120
        bar_x = self.width // 2 - 200
        bar_max_w = 400
        
        total_remaining = sum(x[1] for x in rarity_config)
        
        # 繪製總進度文字
        total_txt = self.info_font.render(f"Cards Remaining: {total_remaining}/100", True, (255, 255, 255))
        self.screen.blit(total_txt, (self.width//2 - total_txt.get_width()//2, start_y))
        
        start_y += 40

        for label, count, color in rarity_config:
            # 標籤
            label_surf = self.font.render(f"{label}", True, color)
            self.screen.blit(label_surf, (bar_x - 100, start_y))
            
            # 數字
            count_surf = self.font.render(f"{count}", True, (255, 255, 255))
            self.screen.blit(count_surf, (bar_x + bar_max_w + 20, start_y))
            
            # 進度條背景
            pygame.draw.rect(self.screen, (50, 50, 60), (bar_x, start_y + 5, bar_max_w, 15), border_radius=4)
            
            # 進度條前景 (根據最大可能數量做比例，例如 Legend 最大 1，Common 最大 75)
            # 這裡為了視覺效果，我們設定一個視覺上的 Max 基數
            max_base = 75 if label == "Common" else (20 if label == "Rare" else (4 if label == "Epic" else 1))
            if count > 0:
                fill_w = int(bar_max_w * (count / max_base))
                # 確保至少有一點點寬度看得到
                fill_w = max(fill_w, 5)
                pygame.draw.rect(self.screen, color, (bar_x, start_y + 5, fill_w, 15), border_radius=4)
            
            start_y += 35