import pygame
import math
from pygame import Rect
from client.utils.resource_manager import ResourceManager

# 狀態常數
START_BATTLE = "START_BATTLE"
GOTO_GACHA = "GOTO_GACHA"
GOTO_DECK = "GOTO_DECK"
GOTO_MARKET = "GOTO_MARKET"
GOTO_LOBBY = "GOTO_LOBBY"
GOTO_SETTINGS = "GOTO_SETTINGS"

class LobbyScene:
    def __init__(self, screen, user_data: dict = None):
        pygame.font.init()
        self.screen = screen
        self.user = user_data or {"name": "Player", "gold": 0, "gems": 0}
        self.width, self.height = screen.get_size()
        
        # 字體優化：稍微大一點，使用粗體
        self.font = pygame.font.SysFont("Arial", 20, bold=True)
        self.title_font = pygame.font.SysFont("Arial", 24, bold=True)
        # 戰鬥按鈕專用字體
        self.battle_font = pygame.font.SysFont("Arial", 36, bold=True)

        self._init_layout()

        # 配色優化 (更柔和、更有質感的顏色)
        self.colors = {
            "bg": (18, 18, 30),
            "panel_bg": (0, 0, 0, 180),     # 半透明黑
            "gold": (255, 215, 0),          # 金色
            "white": (240, 240, 240),
            "btn_normal": (60, 60, 80),
            "btn_hover": (80, 80, 120),
            "battle_main": (50, 120, 200),  # 戰鬥鈕主色
            "battle_glow": (100, 180, 255), # 戰鬥鈕光暈
        }
        
        self._mouse_pos = (0, 0)
        self.timer = 0.0 # 動畫計時器

    def _init_layout(self):
        # Settings (右上角)
        self.settings_rect = Rect(self.width - 60, 20, 40, 40)
        
        # Battle Button (正中央圓形)
        self.battle_radius = 80  # 稍微加大
        self.battle_center = (self.width // 2, self.height // 2)
        
        # Banner (全螢幕背景)
        self.banner_rect = Rect(0, 0, self.width, self.height)
        
        # Avatar (左上角)
        self.avatar_rect = Rect(20, 15, 50, 50)

        # --- 底部按鈕 Layout (改為懸浮圓角) ---
        btn_w, btn_h = 160, 50
        gap = 20
        total_w = (btn_w * 4) + (gap * 3)
        start_x = (self.width - total_w) // 2
        y_pos = self.height - 80 # 離底部有一段距離
        
        self.nav_buttons = []
        labels = [("Draw", GOTO_GACHA), ("Deck", GOTO_DECK), ("Lobby", GOTO_LOBBY), ("Market", GOTO_MARKET)]
        
        for i, (lbl, state) in enumerate(labels):
            r = Rect(start_x + i * (btn_w + gap), y_pos, btn_w, btn_h)
            active = (state == GOTO_LOBBY)
            self.nav_buttons.append((r, lbl, state, active))

    def update(self, events):
        # 更新動畫時間
        self.timer += 0.05

        for ev in events:
            if ev.type == pygame.MOUSEMOTION:
                self._mouse_pos = ev.pos
            
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                
                # Settings
                if self.settings_rect.collidepoint((mx, my)):
                    return GOTO_SETTINGS
                
                # Battle (圓形判定)
                dist = math.hypot(mx - self.battle_center[0], my - self.battle_center[1])
                if dist <= self.battle_radius:
                    return START_BATTLE

                # Nav Buttons
                for rect, label, state, active in self.nav_buttons:
                    if rect.collidepoint((mx, my)):
                        return state
        return None

    def draw(self):
        try:
            # 1. 畫背景 (Banner)
            banner_img = ResourceManager.get_banner_image("banner.png", self.width, self.height)
            if banner_img:
                self.screen.blit(banner_img, (0, 0))
            else:
                self.screen.fill(self.colors["bg"])

            # 2. 畫頂部資訊欄 (半透明漸層黑底)
            header_h = 80
            header_surf = pygame.Surface((self.width, header_h), pygame.SRCALPHA)
            # 畫一個從上到下的漸層黑色，讓文字清楚但不會擋住背景太多
            for y in range(header_h):
                alpha = int(200 * (1 - y/header_h)) # 200 -> 0
                pygame.draw.line(header_surf, (0, 0, 0, alpha), (0, y), (self.width, y))
            
            # 或者簡單一點，直接畫均勻半透明
            header_surf.fill(self.colors["panel_bg"]) 
            self.screen.blit(header_surf, (0, 0))

            # Avatar
            pygame.draw.rect(self.screen, (100, 100, 120), self.avatar_rect, border_radius=10)
            pygame.draw.rect(self.screen, (200, 200, 200), self.avatar_rect, 2, border_radius=10) # 白邊框

            # User Info
            name_str = str(self.user.get("username", "Player"))
            name_surf = self.title_font.render(name_str, True, self.colors["white"])
            
            gold_val = self.user.get('gold', 0)
            gold_txt = f"Gold: {gold_val}"
            gold_surf = self.font.render(gold_txt, True, self.colors["gold"])

            self.screen.blit(name_surf, (self.avatar_rect.right + 15, 20))
            self.screen.blit(gold_surf, (self.avatar_rect.right + 15, 50))

            # Settings Gear
            # 簡單畫個圓圈代替齒輪
            pygame.draw.circle(self.screen, (200, 200, 200), self.settings_rect.center, 15, 2)
            gear_txt = self.font.render("S", True, (200, 200, 200))
            self.screen.blit(gear_txt, gear_txt.get_rect(center=self.settings_rect.center))

            # 3. 畫中央 Battle 按鈕 (呼吸動畫特效)
            self.draw_battle_button()

            # 4. 畫底部導航列 (懸浮按鈕)
            self.draw_nav_bar()

            pygame.display.flip()
        except Exception as e:
            print(f"[LobbyScene] Draw Error: {e}")
            import traceback
            traceback.print_exc()

    def draw_battle_button(self):
        mx, my = self._mouse_pos
        dist = math.hypot(mx - self.battle_center[0], my - self.battle_center[1])
        is_hover = dist <= self.battle_radius

        # 呼吸效果 (Scale 縮放)
        pulse = math.sin(self.timer) * 5 # -5 ~ +5
        current_radius = self.battle_radius + (pulse if is_hover else 0)

        # 1. 外發光 (Glow) - 畫多層半透明圓
        glow_surf = pygame.Surface((current_radius*3, current_radius*3), pygame.SRCALPHA)
        if is_hover:
            pygame.draw.circle(glow_surf, (*self.colors["battle_glow"], 50), (current_radius*1.5, current_radius*1.5), current_radius + 10)
            pygame.draw.circle(glow_surf, (*self.colors["battle_glow"], 100), (current_radius*1.5, current_radius*1.5), current_radius + 5)
        self.screen.blit(glow_surf, (self.battle_center[0] - current_radius*1.5, self.battle_center[1] - current_radius*1.5))

        # 2. 按鈕主體 (漸層感用兩個圓模擬)
        main_color = self.colors["battle_glow"] if is_hover else self.colors["battle_main"]
        pygame.draw.circle(self.screen, (30, 30, 50), self.battle_center, current_radius) # 陰影/底
        pygame.draw.circle(self.screen, main_color, self.battle_center, current_radius - 4) # 主色

        # 3. 內圈裝飾線 (金色)
        pygame.draw.circle(self.screen, self.colors["gold"], self.battle_center, current_radius - 10, 2)

        # 4. 文字
        txt = self.battle_font.render("BATTLE", True, self.colors["white"])
        # 加一點文字陰影
        shadow = self.battle_font.render("BATTLE", True, (0, 0, 0))
        self.screen.blit(shadow, (self.battle_center[0] - txt.get_width()//2 + 2, self.battle_center[1] - txt.get_height()//2 + 2))
        self.screen.blit(txt, (self.battle_center[0] - txt.get_width()//2, self.battle_center[1] - txt.get_height()//2))

    def draw_nav_bar(self):
        mx, my = self._mouse_pos
        
        for rect, label, state, active in self.nav_buttons:
            is_hover = rect.collidepoint((mx, my))
            
            # 決定顏色
            if active:
                bg_color = self.colors["battle_main"] # 亮藍色
                border_color = self.colors["gold"]
                text_color = self.colors["white"]
                # 當前頁面按鈕稍微往上浮
                draw_rect = rect.move(0, -5)
            elif is_hover:
                bg_color = self.colors["btn_hover"]
                border_color = self.colors["white"]
                text_color = self.colors["white"]
                draw_rect = rect.move(0, -2)
            else:
                bg_color = self.colors["panel_bg"] # 半透明黑
                border_color = (100, 100, 100)
                text_color = (200, 200, 200)
                draw_rect = rect

            # 畫圓角矩形背景
            # 注意：若要畫半透明圓角矩形，需要先畫在 Surface 上再 blit
            s = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
            
            # 根據是否 active 決定透明度 (Active 不透明，其他半透明)
            color_with_alpha = (*bg_color[:3], 255) if active else (*bg_color[:3], 200)
            if len(bg_color) == 4: color_with_alpha = bg_color # 如果已經有 alpha

            pygame.draw.rect(s, color_with_alpha, (0, 0, draw_rect.width, draw_rect.height), border_radius=10)
            
            # 畫邊框
            pygame.draw.rect(s, border_color, (0, 0, draw_rect.width, draw_rect.height), 2, border_radius=10)
            
            self.screen.blit(s, draw_rect.topleft)

            # 文字
            txt = self.font.render(label, True, text_color)
            txt_rect = txt.get_rect(center=draw_rect.center)
            self.screen.blit(txt, txt_rect)

# Factory function
def create_lobby_scene(screen, user_data=None):
    return LobbyScene(screen, user_data)