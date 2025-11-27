import random
from client.services.game_db_service import service as db_service

class GachaEngine:
    def __init__(self, user_id):
        self.user_id = user_id
        self.cost_per_draw = 0 # 每次抽卡花費的金額 (可調整)

    def get_box_info(self):
        return db_service.get_gacha_box_state(self.user_id)

    def draw_one(self):
        # 1. 獲取當前盒子狀態
        state = self.get_box_info()
        if not state:
            return {"success": False, "message": "System Error"}

        # 2. 計算總剩餘卡數
        total = (state['legend_count'] + state['epic_count'] + 
                 state['rare_count'] + state['common_count'])
        
        if total <= 0:
            return {"success": False, "message": "Box is empty! (Reset needed)"}

        # 3. 決定抽到什麼稀有度 (動態權重)
        # 我們將所有剩餘卡片展開成一個虛擬列表來抽
        # 例如: [Legend]*1 + [Epic]*4 ...
        
        rand_val = random.randint(1, total)
        
        # 累積機率判定
        current_threshold = state['legend_count']
        if rand_val <= current_threshold:
            picked_rarity = "legend"
        else:
            current_threshold += state['epic_count']
            if rand_val <= current_threshold:
                picked_rarity = "epic"
            else:
                current_threshold += state['rare_count']
                if rand_val <= current_threshold:
                    picked_rarity = "rare"
                else:
                    picked_rarity = "common"

        # 4. 呼叫 DB 執行交易 (真正的原子操作)
        result = db_service.execute_gacha_draw(self.user_id, picked_rarity, self.cost_per_draw)
        
        return result
    
     # --- 新增：10連抽 ---
    def draw_ten(self):
        """執行10次抽卡，回傳結果列表"""
        results = []
        success_cards = []
        
        # 檢查錢夠不夠 (一次檢查總額比較好，但為了沿用 draw_one 邏輯，我們逐次抽)
        # 優化：先檢查總金額避免抽到一半沒錢
        state = self.get_box_info()
        # 這裡略過嚴格檢查，直接跑迴圈，利用 draw_one 的檢查機制
        
        for _ in range(10):
            res = self.draw_one()
            results.append(res)
            if res['success']:
                success_cards.append(res['card'])
            else:
                # 如果中途失敗(例如沒錢或沒卡)，就停止
                break
        
        if not success_cards and results:
            # 一張都沒抽到，回傳第一個錯誤
            return {"success": False, "message": results[0]['message']}
            
        return {
            "success": True,
            "cards": success_cards, # 這是成功抽到的卡片列表
            "count": len(success_cards)
        }