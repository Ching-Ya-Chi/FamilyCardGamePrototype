import pygame
import sys
from client.services.game_db_service import service as db_service 
from client.utils.resource_manager import ResourceManager

class DeckBuilderScene:
    WIDTH = 1280
    HEIGHT = 720

    # Panel positions and sizes
    LEFT_W = 300
    MID_W = 500
    RIGHT_W = 480

    LEFT_X = 0
    MID_X = LEFT_W
    RIGHT_X = LEFT_W + MID_W

    BG_COLOR = (30, 30, 30)
    LEFT_BG = (40, 40, 40)  # dark gray
    INV_COLOR = (173, 216, 230)  # light blue (inventory cards)
    DECK_COLOR = (255, 165, 0)  # orange/gold (deck cards)
    EMPTY_SLOT = (60, 60, 60)
    DIM_OVERLAY = (0, 0, 0, 150)

    MAX_DECK = 30

    def __init__(self, screen: pygame.Surface = None, user_data: dict = None):
        if screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
            self._owned_screen = True
        else:
            self.screen = screen
            self._owned_screen = False
            
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 18)
        self.title_font = pygame.font.SysFont('Arial', 22, bold=True)

        self.user = user_data or {}
        self.user_id = self.user.get('user_id', 1)
        print(f"[DeckBuilder] Loading for User ID: {self.user_id}")

        self.cards = db_service.get_card_list()
        self.card_map = {c['id']: c for c in self.cards}
        self.inventory = db_service.get_user_inventory(self.user_id)
        self.deck = db_service.get_user_deck(self.user_id)
        
        self.selected_card_id = None
        self.right_page = 0
        self.deck_cols = 6
        self.deck_rows = 5
        self.right_card_rects = [] 
        self.deck_slot_rects = []
        self.back_rect = None

    def run(self):
        running = True
        while running:
            self.clock.tick(60)
            events = pygame.event.get()
            
            # 這裡呼叫 update 統一處理
            res = self.update(events)
            if res == 'GOTO_LOBBY':
                running = False

            self.draw()

        if getattr(self, '_owned_screen', False):
            pygame.quit()
            sys.exit()

    # 【修正 1】改名為 update 並加入 update_hover
    def update(self, events):
        # 每一幀都更新 hover 狀態
        self.update_hover(pygame.mouse.get_pos())

        for ev in events:
            if ev.type == pygame.QUIT:
                return 'GOTO_LOBBY'
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                res = self.handle_click(ev.pos)
                if res:
                    return res
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return 'GOTO_LOBBY'
        return None

    def save_and_exit(self):
        """儲存牌組並回傳退出訊號"""
        db_service.save_user_deck(self.user_id, self.deck)
        return 'GOTO_LOBBY'
    
    def draw(self):
        self.screen.fill(self.BG_COLOR)
        
        # 【修正 2】先畫面板背景
        left_rect = pygame.Rect(self.LEFT_X, 0, self.LEFT_W, self.HEIGHT)
        pygame.draw.rect(self.screen, self.LEFT_BG, left_rect)
        self.draw_left_panel(left_rect)

        mid_rect = pygame.Rect(self.MID_X, 0, self.MID_W, self.HEIGHT)
        pygame.draw.rect(self.screen, (50, 50, 50), mid_rect)
        self.draw_mid_panel(mid_rect)

        right_rect = pygame.Rect(self.RIGHT_X, 0, self.RIGHT_W, self.HEIGHT)
        pygame.draw.rect(self.screen, (45, 45, 55), right_rect)
        self.draw_right_panel(right_rect)

        # 【修正 2】最後才畫按鈕，確保它在最上層 (Z-Order)
        back_w = 120
        back_h = 34
        back_x = 10
        back_y = 10
        self.back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        
        pygame.draw.rect(self.screen, (50, 150, 50), self.back_rect, border_radius=5)
        # 加個白框讓按鈕更明顯
        pygame.draw.rect(self.screen, (255, 255, 255), self.back_rect, 2, border_radius=5)
        
        back_txt = self.font.render('Save & Back', True, (255, 255, 255))
        # 文字置中
        txt_rect = back_txt.get_rect(center=self.back_rect.center)
        self.screen.blit(back_txt, txt_rect)

        pygame.display.flip()

    def draw_left_panel(self, rect):
        padding = 12
        x = rect.x + padding
        # 因為上面有按鈕，把內容往下移一點
        y = rect.y + padding + 50 
        
        title_surf = self.title_font.render('Card Details', True, (220, 220, 220))
        self.screen.blit(title_surf, (x, y))
        y += 40

        if self.selected_card_id and self.selected_card_id in self.card_map:
            # 大圖預覽
            big_w, big_h = 200, 280
            img_x = rect.x + (rect.width - big_w) // 2
            big_img = ResourceManager.get_card_image(self.selected_card_id, big_w, big_h)
            self.screen.blit(big_img, (img_x, y))
            pygame.draw.rect(self.screen, (200, 200, 200), (img_x, y, big_w, big_h), 2)
            y += big_h + 20

            card = self.card_map[self.selected_card_id]
            lines = [f"Name: {card['name']}", f"Cost: {card['cost']}", f"ATK: {card['attack']}  HP: {card['health']}", '', 'Description:']
            
            desc = card.get('description', card.get('desc', ''))
            words = desc.split()
            cur = ''
            desc_lines = []
            for w in words:
                if len(cur) + len(w) + 1 > 30:
                    desc_lines.append(cur)
                    cur = w
                else:
                    cur = f"{cur} {w}" if cur else w
            if cur:
                desc_lines.append(cur)

            lines += desc_lines
            for ln in lines:
                surf = self.font.render(ln, True, (230, 230, 230))
                self.screen.blit(surf, (x, y))
                y += 24
        else:
            # 預設提示
            hint = self.font.render('Hover card to see details', True, (150, 150, 150))
            self.screen.blit(hint, (x, y))

    def draw_mid_panel(self, rect):
        padding = 12
        x = rect.x + padding
        y = rect.y + padding
        
        header = self.title_font.render(f'Deck Count: {len(self.deck)}/{self.MAX_DECK}', True, (240, 240, 240))
        self.screen.blit(header, (x, y))
        y += 48

        area_x = rect.x + padding
        area_y = rect.y + 80
        area_w = rect.w - padding * 2
        area_h = rect.h - 90

        slot_w = (area_w - (self.deck_cols + 1) * 10) / self.deck_cols
        slot_h = (area_h - (self.deck_rows + 1) * 10) / self.deck_rows

        self.deck_slot_rects = []
        idx = 0
        for r in range(self.deck_rows):
            for c in range(self.deck_cols):
                sx = int(area_x + 10 + c * (slot_w + 10))
                sy = int(area_y + 10 + r * (slot_h + 10))
                srect = pygame.Rect(sx, sy, int(slot_w), int(slot_h))
                
                self.deck_slot_rects.append((srect, idx))
                if idx < len(self.deck):
                    card_id = self.deck[idx]
                    self.draw_card_item(srect, card_id)
                else:
                    pygame.draw.rect(self.screen, self.EMPTY_SLOT, srect, border_radius=5)
                idx += 1

    def draw_right_panel(self, rect):
        padding = 12
        y = rect.y + padding

        # Pagination
        btn_w, btn_h = 100, 36
        prev_rect = pygame.Rect(rect.x + 20, y, btn_w, btn_h)
        next_rect = pygame.Rect(rect.x + rect.w - 20 - btn_w, y, btn_w, btn_h)
        pygame.draw.rect(self.screen, (100, 100, 140), prev_rect)
        pygame.draw.rect(self.screen, (100, 100, 140), next_rect)
        
        self.screen.blit(self.font.render('Prev Page', True, (240,240,240)), (prev_rect.x+10, prev_rect.y+8))
        self.screen.blit(self.font.render('Next Page', True, (240,240,240)), (next_rect.x+10, next_rect.y+8))

        # Page Info
        total_cards = len(self.cards)
        cards_per_page = 9
        total_pages = max(1, (total_cards + cards_per_page - 1) // cards_per_page)
        page_txt = self.font.render(f'Page {self.right_page + 1}/{total_pages}', True, (230, 230, 230))
        self.screen.blit(page_txt, (rect.x + rect.w // 2 - 30, y + 8))

        y += 56

        # Grid
        grid_x = rect.x + 20
        grid_y = y
        grid_w = rect.w - 40
        grid_h = rect.h - y - 20

        cols, rows = 3, 3
        card_w = int((grid_w - (cols + 1) * 12) / cols)
        card_h = int((grid_h - (rows + 1) * 12) / rows)

        start_idx = self.right_page * cards_per_page
        page_cards = self.cards[start_idx:start_idx + cards_per_page]

        self.right_card_rects = []
        i = 0
        for r in range(rows):
            for c in range(cols):
                sx = grid_x + 12 + c * (card_w + 12)
                sy = grid_y + 12 + r * (card_h + 12)
                crect = pygame.Rect(sx, sy, card_w, card_h)
                
                if i < len(page_cards):
                    card = page_cards[i]
                    count = self.inventory.get(card['id'], 0)
                    
                    self.draw_card_item(crect, card['id'])
                    
                    if count == 0:
                        s = pygame.Surface((crect.w, crect.h), pygame.SRCALPHA)
                        s.fill((0, 0, 0, 160))
                        self.screen.blit(s, crect)
                    
                    # Count badge
                    cnt_bg = pygame.Surface((24, 20))
                    cnt_bg.set_alpha(200)
                    cnt_bg.fill((0,0,0))
                    self.screen.blit(cnt_bg, (crect.right - 24, crect.bottom - 20))
                    cnt_color = (255, 100, 100) if count == 0 else (100, 255, 100)
                    self.screen.blit(self.font.render(str(count), True, cnt_color), (crect.right - 20, crect.bottom - 20))

                    self.right_card_rects.append((crect, card['id']))
                else:
                    pygame.draw.rect(self.screen, (60, 60, 70), crect)
                i += 1

        self.right_prev_rect = prev_rect
        self.right_next_rect = next_rect

    def draw_card_item(self, rect, card_id):
        img = ResourceManager.get_card_image(card_id, rect.width, rect.height)
        self.screen.blit(img, rect)
        pygame.draw.rect(self.screen, (150, 150, 150), rect, 1)

        card = self.card_map.get(card_id)
        if card:
            cost_bg = (rect.x + 15, rect.y + 15)
            pygame.draw.circle(self.screen, (0, 0, 150), cost_bg, 12)
            pygame.draw.circle(self.screen, (255, 255, 255), cost_bg, 12, 1)
            cost_surf = self.font.render(str(card['cost']), True, (255, 255, 255))
            self.screen.blit(cost_surf, (cost_bg[0] - cost_surf.get_width()//2, cost_bg[1] - cost_surf.get_height()//2))

    def handle_click(self, pos):
        if hasattr(self, 'back_rect') and self.back_rect and self.back_rect.collidepoint(pos):
            return self.save_and_exit()

        if hasattr(self, 'right_prev_rect') and self.right_prev_rect.collidepoint(pos):
            self.right_page = max(0, self.right_page - 1)
            return
        if hasattr(self, 'right_next_rect') and self.right_next_rect.collidepoint(pos):
            max_page = max(0, (len(self.cards) - 1) // 9)
            self.right_page = min(max_page, self.right_page + 1)
            return

        # Check right panel cards (Inventory -> Deck)
        for crect, cid in self.right_card_rects:
            if crect.collidepoint(pos):
                if len(self.deck) >= self.MAX_DECK:
                    print('Deck full')
                    return
                if self.inventory.get(cid, 0) <= 0:
                    print('No copies available')
                    return
                self.inventory[cid] -= 1
                self.deck.append(cid)
                self.deck.sort(key=lambda id_: (self.card_map[id_]['cost'], id_))
                return

        # Check deck slots (Deck -> Inventory)
        for srect, idx in self.deck_slot_rects:
            if srect.collidepoint(pos):
                if idx < len(self.deck):
                    cid = self.deck.pop(idx)
                    self.inventory[cid] = self.inventory.get(cid, 0) + 1
                    return

    def update_hover(self, mouse_pos):
        self.selected_card_id = None
        for crect, cid in self.right_card_rects:
            if crect.collidepoint(mouse_pos):
                self.selected_card_id = cid
                return
        for srect, idx in self.deck_slot_rects:
            if srect.collidepoint(mouse_pos):
                if idx < len(self.deck):
                    self.selected_card_id = self.deck[idx]
                    return

if __name__ == '__main__':
    # Create and run scene
    scene = DeckBuilderScene()
    scene.run()