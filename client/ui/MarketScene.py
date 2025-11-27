import pygame
import sys
from client.services.game_db_service import service as db_service 
from client.utils.resource_manager import ResourceManager # 建議引入，若要顯示圖片

class MarketScene:
    def __init__(self, screen, user_data=None, size=(1280, 720)):
        self.screen = screen
        self.width, self.height = size
        
        # 1. 接收 user_data (雖然目前市場可能只看 ID，但為了介面統一需接收)
        self.user = user_data or {}
        self.user_id = self.user.get('user_id', 1)
        print(f"[MarketScene] User ID: {self.user_id}")

        # Layout columns
        self.left_w = 300
        self.mid_w = 400
        self.right_w = 580

        # Fonts
        pygame.font.init()
        self.font = ResourceManager.get_font(18)
        self.big_font = ResourceManager.get_font(24)

        # 2. 載入卡片定義
        self.cards = db_service.get_card_list()
        
        # 預設選中第一張
        self.selected_card_id = self.cards[0]["id"] if self.cards else None

        # 3. 載入市場掛單
        raw_market_data = db_service.get_market_listings()
        self.market_data = { c["name"]: {"sells": [], "buys": []} for c in self.cards }
        
        for c_name, data in raw_market_data.items():
            if c_name in self.market_data:
                self.market_data[c_name] = data

        # UI state
        self.price_input = ""
        self.input_active = False
        self.status_message = ""

        self.left_scroll = 0
        
        # Buttons rects cached
        self.buy_button_rect = None
        self.sell_button_rect = None
        self.input_rect = None
        
        # 4. 新增返回按鈕 Rect
        self.back_rect = None

        self.refresh_market_data()

    def get_selected_card(self):
        for c in self.cards:
            if c["id"] == self.selected_card_id:
                return c
        return self.cards[0] if self.cards else None

    # 【重要修改】改名為 update 並接收 events 列表
    def update(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return "GOTO_LOBBY" # 視窗關閉時回大廳而非直接退出

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                
                # 1. 檢查返回按鈕
                if self.back_rect and self.back_rect.collidepoint(mx, my):
                    return "GOTO_LOBBY"

                # Left column - clicking card names
                # 【修正】必須與 draw_left_column 的計算邏輯完全一致
                top_offset = 50          # 這是 draw 裡面設定的偏移
                padding = 12
                search_h = 36
                gap = 12

                list_y = top_offset + padding + search_h + gap # = 110
                row_h = 40
                
                # 檢查是否點擊在左欄範圍內且在列表區域
                if 0 < mx < self.left_w and my > list_y:
                    # 計算點到了第幾個
                    # 考慮間距 (row_h + 5)
                    clicked_idx = (my - list_y) // (row_h + 5)
                    
                    if 0 <= clicked_idx < len(self.cards):
                        c = self.cards[int(clicked_idx)]
                        self.selected_card_id = c["id"]
                        self.price_input = ""
                        self.status_message = f"Selected {c['name']}"
                        
                        # 重新載入該卡片的市場資料
                        self.refresh_market_data() # 如果需要即時刷新可加這行

                # Input box click
                if self.input_rect and self.input_rect.collidepoint(mx, my):
                    self.input_active = True
                else:
                    self.input_active = False

                # Buy button click
                if self.buy_button_rect and self.buy_button_rect.collidepoint(mx, my):
                    self.attempt_buy()

                # Sell button click
                if self.sell_button_rect and self.sell_button_rect.collidepoint(mx, my):
                    self.attempt_sell()

            elif event.type == pygame.KEYDOWN and self.input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.price_input = self.price_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.input_active = False
                else:
                    if event.unicode.isdigit() or (event.unicode == "." and "." not in self.price_input):
                        self.price_input += event.unicode
        
        return None
    
    def refresh_market_data(self):
        """重新從 DB 載入資料"""
        self.cards = db_service.get_card_list()
        raw_listings = db_service.get_raw_listings() # 請使用剛剛新增的 get_raw_listings
        
        # 重置結構
        self.market_data = { c["name"]: {"sells": [], "buys": []} for c in self.cards }
        
        for row in raw_listings:
            c_name = row['name']
            if c_name in self.market_data:
                self.market_data[c_name]["sells"].append({
                    "listing_id": row['listing_id'], # 重要：需要這個 ID 才能買
                    "user": row['seller'],
                    "price": row['price']
                })

    def attempt_buy(self):
        card = self.get_selected_card()
        if not card: return
        name = card["name"]
        
        # 取得最低價的掛單
        sells = self.market_data[name]["sells"]
        if not sells:
            self.status_message = "No active sellers"
            return

        # 找到最便宜的單
        cheapest = min(sells, key=lambda x: x["price"])
        
        try:
            price_offer = float(self.price_input)
        except:
            # 如果沒輸入價格，直接買最便宜的；如果有輸入，檢查是否足夠
            price_offer = cheapest["price"]

        if price_offer >= cheapest["price"]:
            # 呼叫 DB 執行購買
            result = db_service.execute_buy(self.user_id, cheapest["listing_id"])
            if result == "Success":
                self.status_message = f"Bought from {cheapest['user']}!"
                self.refresh_market_data() # 購買後刷新介面
            else:
                self.status_message = f"Buy failed: {result}"
        else:
            self.status_message = "Price too low for instant buy"

    def attempt_sell(self):
        card = self.get_selected_card()
        if not card: return
        try:
            price = int(self.price_input)
        except:
            self.status_message = "Enter valid integer price"
            return

        # 呼叫 DB 執行販賣
        result = db_service.execute_sell(self.user_id, card['id'], price)
        if result == "Success":
            self.status_message = f"Listed {card['name']} for ${price}"
            self.refresh_market_data() # 刷新
        else:
            self.status_message = f"Sell failed: {result}"

    def draw(self): # 改名為 draw (原本叫 render) 以符合 Manager 規範
        self.screen.fill((30, 30, 30))
        
        # 繪製返回按鈕
        self.back_rect = pygame.Rect(10, 10, 80, 30)
        pygame.draw.rect(self.screen, (100, 100, 120), self.back_rect, border_radius=5)
        back_txt = self.font.render("Back", True, (255, 255, 255))
        self.screen.blit(back_txt, (20, 15))

        # Layout columns
        left_rect = pygame.Rect(0, 0, self.left_w, self.height)
        mid_rect = pygame.Rect(self.left_w, 0, self.mid_w, self.height)
        right_rect = pygame.Rect(self.left_w + self.mid_w, 0, self.right_w, self.height)

        # Draw backgrounds (slightly offset y to not cover back button)
        # 其實可以讓 column 從 y=50 開始，避免遮擋按鈕
        top_offset = 50
        
        # 更新 rect 高度
        left_rect.top = top_offset
        left_rect.height -= top_offset
        mid_rect.top = top_offset
        mid_rect.height -= top_offset
        right_rect.top = top_offset
        right_rect.height -= top_offset

        pygame.draw.rect(self.screen, (40, 40, 40), left_rect)
        pygame.draw.rect(self.screen, (45, 45, 45), mid_rect)
        pygame.draw.rect(self.screen, (50, 50, 50), right_rect)

        self.draw_left_column(left_rect)
        self.draw_middle_column(mid_rect)
        self.draw_right_column(right_rect)

        # Status message
        status_surf = self.font.render(self.status_message, True, (220, 220, 220))
        self.screen.blit(status_surf, (150, 15))

        pygame.display.flip()

    def draw_left_column(self, rect):
        padding = 12
        search_rect = pygame.Rect(rect.x + padding, rect.y + padding, rect.width - 2 * padding, 36)
        pygame.draw.rect(self.screen, (60, 60, 60), search_rect, border_radius=4)
        search_txt = self.font.render("Search", True, (150, 150, 150))
        self.screen.blit(search_txt, (search_rect.x + 8, search_rect.y + 8))

        list_x = rect.x + padding
        list_y = search_rect.bottom + 20 
        row_h = 40

        for idx, c in enumerate(self.cards):
            r = pygame.Rect(search_rect.x, list_y + idx * (row_h + 5), rect.width - 2 * padding, row_h)
            if c["id"] == self.selected_card_id:
                pygame.draw.rect(self.screen, (80, 120, 160), r, border_radius=4)
            else:
                pygame.draw.rect(self.screen, (70, 70, 70), r, border_radius=4)

            txt = self.font.render(c["name"], True, (230, 230, 230))
            self.screen.blit(txt, (r.x + 10, r.y + 10))

    def draw_middle_column(self, rect):
        padding = 20
        card = self.get_selected_card()
        if not card: return

        art_rect = pygame.Rect(rect.x + padding, rect.y + padding, rect.width - padding * 2, 320)
        
        # 嘗試顯示圖片
        try:
            big_img = ResourceManager.get_card_image(card['id'], art_rect.width, art_rect.height)
            self.screen.blit(big_img, art_rect)
        except:
            pygame.draw.rect(self.screen, (80, 80, 100), art_rect, border_radius=8)
            name_surf = self.big_font.render(card["name"], True, (255, 255, 255))
            self.screen.blit(name_surf, (art_rect.x + 12, art_rect.y + 12))

        pygame.draw.rect(self.screen, (150,150,150), art_rect, 2)

        stats_y = art_rect.bottom + 12
        stats_text = f"ATK: {card['attack']}   HP: {card['health']}" # 注意 DB 欄位可能是 health
        stats_surf = self.font.render(stats_text, True, (220, 220, 220))
        self.screen.blit(stats_surf, (art_rect.x + 6, stats_y))

        action_y = rect.y + rect.height - 160
        input_w = rect.width - padding * 2
        self.input_rect = pygame.Rect(rect.x + padding, action_y, input_w, 36)
        
        # 繪製輸入框背景 (Active時全白，非Active時深灰)
        bg_color = (255, 255, 255) if self.input_active else (80, 80, 80)
        pygame.draw.rect(self.screen, bg_color, self.input_rect, border_radius=4)
        
        # 決定文字顏色 (Active時黑色，非Active時淺灰)
        text_color = (0, 0, 0) if self.input_active else (200, 200, 200)
        
        # 顯示內容：如果有輸入就顯示輸入，沒有就顯示提示
        display_text = self.price_input if self.price_input else "Enter Price..."
        
        input_surf = self.font.render(display_text, True, text_color)
        
        # 垂直置中繪製
        text_y = self.input_rect.centery - input_surf.get_height() // 2
        self.screen.blit(input_surf, (self.input_rect.x + 8, text_y))

        btn_h = 48
        btn_w = (rect.width - padding * 3) // 2
        buy_btn = pygame.Rect(rect.x + padding, self.input_rect.bottom + 12, btn_w, btn_h)
        sell_btn = pygame.Rect(buy_btn.right + padding, self.input_rect.bottom + 12, btn_w, btn_h)

        pygame.draw.rect(self.screen, (30, 160, 50), buy_btn, border_radius=6)
        pygame.draw.rect(self.screen, (180, 40, 40), sell_btn, border_radius=6)

        self.screen.blit(self.font.render("Buy", True, (255, 255, 255)), (buy_btn.x + 20, buy_btn.y + 13))
        self.screen.blit(self.font.render("Sell", True, (255, 255, 255)), (sell_btn.x + 20, sell_btn.y + 13))

        self.buy_button_rect = buy_btn
        self.sell_button_rect = sell_btn

    def draw_right_column(self, rect):
        padding = 18
        header_rect = pygame.Rect(rect.x + padding, rect.y + padding, rect.width - 2 * padding, 36)
        hdr = self.big_font.render("Market Depth", True, (230, 230, 230))
        self.screen.blit(hdr, (header_rect.x + 6, header_rect.y + 6))

        midline_y = rect.y + rect.height // 2
        divider_rect = pygame.Rect(rect.x + padding, midline_y - 2, rect.width - 2 * padding, 4)
        pygame.draw.rect(self.screen, (90, 90, 90), divider_rect)

        card = self.get_selected_card()
        if not card: return
        name = card["name"]
        
        # 防呆
        if name not in self.market_data:
            return

        sells = list(self.market_data[name]["sells"])
        buys = list(self.market_data[name]["buys"])

        sells_sorted = sorted(sells, key=lambda x: x["price"], reverse=True)
        sell_area_top = header_rect.bottom + 12
        sell_area_bottom = midline_y - 12
        row_h = 28
        
        for idx, s in enumerate(sells_sorted):
            y = sell_area_top + idx * (row_h + 6)
            if y + row_h > sell_area_bottom: break
            txt = f"{s['user']} : ${s['price']}"
            surf = self.font.render(txt, True, (220, 100, 100))
            self.screen.blit(surf, (rect.x + padding + 6, y))

        buys_sorted = sorted(buys, key=lambda x: x["price"], reverse=True)
        buy_area_top = midline_y + 12
        buy_area_bottom = rect.bottom - 20
        for idx, b in enumerate(buys_sorted):
            y = buy_area_top + idx * (row_h + 6)
            if y + row_h > buy_area_bottom: break
            txt = f"{b['user']} : ${b['price']}"
            surf = self.font.render(txt, True, (120, 220, 130))
            self.screen.blit(surf, (rect.x + padding + 6, y))