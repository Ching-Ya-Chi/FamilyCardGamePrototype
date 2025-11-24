# client/Lobby_Scene.py

import pygame
from pygame import Rect
from client.utils.resource_manager import ResourceManager

# 定義狀態常數 (供 Scene Manager 和 View 溝通使用)
START_BATTLE = "START_BATTLE"
GOTO_GACHA = "GOTO_GACHA"
GOTO_DECK = "GOTO_DECK"
GOTO_MARKET = "GOTO_MARKET"
GOTO_LOBBY = "GOTO_LOBBY"
GOTO_SETTINGS = "GOTO_SETTINGS"

class LobbyScene:
    """
    負責繪製大廳畫面與處理本地滑鼠事件。
    """
    def __init__(self, screen, user_data: dict = None):
        print("[LobbyScene] Initializing...") # Debug
        pygame.font.init()
        self.screen = screen
        self.user = user_data or {"name": "Player", "gold": 0, "gems": 0}
        self.width, self.height = screen.get_size()
        
        # 字體設定
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 32)
        self.large_font = pygame.font.Font(None, 48)

        # 介面幾何參數
        self.status_bar_h = 70
        self.banner_h = 220
        self.bottom_bar_h = 80

        # 初始化按鈕區域
        self._init_layout()

        # 顏色定義
        self.colors = {
            "bg": (18, 18, 30),
            "status_bg": (28, 28, 46),
            "panel": (40, 40, 60),
            "button": (70, 130, 180),
            "button_hover": (100, 160, 210),
            "white": (255, 255, 255),
            "muted": (180, 180, 200),
        }
        self._mouse_pos = (0, 0)

    def _init_layout(self):
        # Settings
        self.settings_rect = Rect(self.width - 50, 15, 36, 36)
        
        # Battle button
        self.battle_rect = Rect(0, 0, int(self.width * 0.7), 64)
        self.battle_rect.centerx = self.width // 2
        self.battle_rect.top = self.status_bar_h + self.banner_h + 20

        # Bottom nav
        nav_y = self.height - self.bottom_bar_h
        btn_w = self.width // 4
        self.nav_buttons = []
        labels = [("Draw", GOTO_GACHA), ("Deck", GOTO_DECK), ("Lobby", GOTO_LOBBY), ("Market", GOTO_MARKET)]
        for i, (lbl, state) in enumerate(labels):
            r = Rect(i * btn_w, nav_y, btn_w, self.bottom_bar_h)
            active = (state == GOTO_LOBBY)
            self.nav_buttons.append((r, lbl, state, active))
        
        # Banner & Avatar
        self.banner_rect = Rect(20, self.status_bar_h + 10, self.width - 40, self.banner_h)
        self.avatar_rect = Rect(15, 15, 48, 48)

    def update(self, events):
        """
        Scene Manager 會呼叫此方法。
        若有按鈕被點擊，回傳狀態字串 (State String)。
        """
        for ev in events:
            if ev.type == pygame.MOUSEMOTION:
                self._mouse_pos = ev.pos
            
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                
                if self.settings_rect.collidepoint((mx, my)):
                    return GOTO_SETTINGS

                if self.battle_rect.collidepoint((mx, my)):
                    return START_BATTLE

                for rect, label, state, active in self.nav_buttons:
                    if rect.collidepoint((mx, my)):
                        return state
        return None

    def draw(self):
        try:
            self.screen.fill(self.colors["bg"])
            
            # Status Bar
            pygame.draw.rect(self.screen, self.colors["status_bg"], (0, 0, self.width, self.status_bar_h))
            pygame.draw.rect(self.screen, self.colors["panel"], self.avatar_rect, border_radius=6)
            
            # Name
            name_str = str(self.user.get("username", "Player"))
            name_surf = self.title_font.render(name_str, True, self.colors["white"])
            self.screen.blit(name_surf, (self.avatar_rect.right + 10, 18))
            
            # Gold
            gold_val = self.user.get('gold')
            if gold_val is None: gold_val = 0
            gold_text = f"Gold: {gold_val}"
            gold_surf = self.font.render(gold_text, True, self.colors["muted"])
            self.screen.blit(gold_surf, (self.avatar_rect.right + 10, 50))

            # Settings
            pygame.draw.rect(self.screen, self.colors["panel"], self.settings_rect, border_radius=6)
            # 畫一個簡單的 'S' 代替齒輪
            gear = self.font.render("S", True, self.colors["white"])
            self.screen.blit(gear, (self.settings_rect.x + 10, self.settings_rect.y + 10))

            # Banner
            banner_img = ResourceManager.get_banner_image(
                "banner.png", 
                self.banner_rect.width, 
                self.banner_rect.height
            )

            if banner_img:
                self.screen.blit(banner_img, self.banner_rect)
                pygame.draw.rect(self.screen, (100, 100, 120), self.banner_rect, 2, border_radius=8)
            else:
                pygame.draw.rect(self.screen, self.colors["panel"], self.banner_rect, border_radius=8)
                banner_label = self.large_font.render("News / Seasonal Banner", True, self.colors["muted"])
                lbl_rect = banner_label.get_rect(center=self.banner_rect.center)
                self.screen.blit(banner_label, lbl_rect)
            
            # Battle Button
            mx, my = self._mouse_pos
            is_hover = self.battle_rect.collidepoint((mx, my))
            bcolor = self.colors["button_hover"] if is_hover else self.colors["button"]
            pygame.draw.rect(self.screen, bcolor, self.battle_rect, border_radius=12)
            lbl = self.large_font.render("BATTLE", True, self.colors["white"])
            # 置中
            lbl_rect = lbl.get_rect(center=self.battle_rect.center)
            self.screen.blit(lbl, lbl_rect)

            # Bottom Nav
            for rect, label, state, active in self.nav_buttons:
                bg = (60, 60, 80) if active else self.colors["panel"]
                pygame.draw.rect(self.screen, bg, rect)
                txt = self.font.render(label, True, self.colors["white"] if active else self.colors["muted"])
                txt_rect = txt.get_rect(center=rect.center)
                self.screen.blit(txt, txt_rect)

            pygame.display.flip()
        except Exception as e:
            print(f"[LobbyScene] Draw Error: {e}")

# Factory function
def create_lobby_scene(screen, user_data=None):
    return LobbyScene(screen, user_data)