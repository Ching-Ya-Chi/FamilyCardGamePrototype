import pygame
import os
from pathlib import Path

class ResourceManager:
    _images = {}
    
    # 設定圖片路徑：假設 main.py 在專案根目錄
    # 這裡使用 os.getcwd() 確保從執行目錄開始找
    BASE_DIR = Path(os.getcwd())
    ASSETS_DIR = BASE_DIR / "assets" / "cards"
    #field root
    FIELD_DIR = BASE_DIR / "assets" / "Field"
    #packs root
    PACKS_DIR = BASE_DIR / "assets" / "packs"

    DEFAULT_IMG_NAME = "default.png" 

    @classmethod
    def get_card_image(cls, card_id: int, width: int = None, height: int = None):
        key = f"{card_id}_{width}_{height}"
        
        if key in cls._images:
            return cls._images[key]
        
        # 建立路徑 (例如: assets/cards/1.png)
        img_path = cls.ASSETS_DIR / f"{card_id}.png"
        
        image = None
        
        # 除錯：只在第一次載入該 ID 時印出路徑，避免刷屏
        if f"{card_id}_debug" not in cls._images:
            print(f"[ResourceManager] Loading: {img_path}")
            print(f"                  Exists? {img_path.exists()}")
            cls._images[f"{card_id}_debug"] = True

        if img_path.exists():
            try:
                image = pygame.image.load(str(img_path)).convert_alpha()
            except Exception as e:
                print(f"[ResourceManager] Error loading {img_path}: {e}")
        else:
            # 嘗試載入 default.png
            default_path = cls.ASSETS_DIR / cls.DEFAULT_IMG_NAME
            if default_path.exists():
                try:
                    image = pygame.image.load(str(default_path)).convert_alpha()
                except:
                    pass

        # 如果真的完全沒圖，畫一個灰底紅字的暫位圖
        if image is None:
            image = pygame.Surface((100, 140))
            image.fill((100, 100, 100)) # 灰色背景
            # 畫個邊框
            pygame.draw.rect(image, (255, 50, 50), (0,0,100,140), 2)
            # 畫個 ID
            font = pygame.font.SysFont(None, 24)
            text = font.render(str(card_id), True, (255, 255, 255))
            image.blit(text, (50 - text.get_width()//2, 70 - text.get_height()//2))

        # 縮放
        if width is not None and height is not None:
            image = pygame.transform.scale(image, (width, height))

        cls._images[key] = image
        return image

    @classmethod
    def get_banner_image(cls, filename="banner.png", width=None, height=None):
        """
        從 assets/Field 載入圖片
        """
        key = f"field_{filename}_{width}_{height}"
        
        if key in cls._images:
            return cls._images[key]
        
        img_path = cls.FIELD_DIR / filename
        image = None

        # 除錯訊息 (第一次載入時顯示)
        if f"field_{filename}_debug" not in cls._images:
            print(f"[ResourceManager] Loading Banner: {img_path}")
            cls._images[f"field_{filename}_debug"] = True

        if img_path.exists():
            try:
                image = pygame.image.load(str(img_path)).convert_alpha()
            except Exception as e:
                print(f"[ResourceManager] Error loading banner {img_path}: {e}")
        
        # 如果找不到圖，回傳 None，讓 UI 自己決定怎麼辦 (畫色塊)
        if image is None:
            return None

        # 縮放
        if width is not None and height is not None:
            image = pygame.transform.scale(image, (width, height))

        cls._images[key] = image
        return image

    @classmethod
    def get_pack_image(cls, filename="pack.png", width=300, height=500):
        key = f"pack_{filename}_{width}_{height}"
        if key in cls._images:
            return cls._images[key]
            
        img_path = cls.PACKS_DIR / filename
        image = None
        
        if img_path.exists():
            try:
                image = pygame.image.load(str(img_path)).convert_alpha()
            except Exception:
                pass
        
        # 預設卡包圖 (銀色包裝)
        if image is None:
            image = pygame.Surface((300, 500))
            image.fill((192, 192, 192)) # 銀色
            # 畫個紋路
            pygame.draw.line(image, (255, 255, 255), (0, 0), (300, 500), 5)
            pygame.draw.line(image, (100, 100, 100), (300, 0), (0, 500), 5)
            # 寫字
            font = pygame.font.SysFont(None, 60)
            txt = font.render("CARD PACK", True, (50, 50, 50))
            image.blit(txt, (150 - txt.get_width()//2, 250 - txt.get_height()//2))

        if width and height:
            image = pygame.transform.scale(image, (width, height))
            
        cls._images[key] = image
        return image

    @classmethod
    def clear_cache(cls):
        cls._images.clear()