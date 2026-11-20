"""游戏常量配置。纯数据，不含逻辑。"""
import os
import sys
import random

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BLOCK_SIZE = 32
FPS = 60
CHUNK_SIZE = 16
RENDER_DISTANCE = 3
Y_MAX = 128

# 網絡配置（與模塊同步）
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 0
IS_SERVER = False
IS_CLIENT = False

# 性能優化配置
MAX_UPDATES_PER_FRAME = 50
USE_DOUBLE_BUFFER = True
FRAME_SKIP = 2

# 移動設備配置
IS_MOBILE = False
VIRTUAL_JOYSTICK_ENABLED = True
VIRTUAL_BUTTONS_ENABLED = True
JOYSTICK_RADIUS = 60
JOYSTICK_BASE_COLOR = (100, 100, 100, 150)
JOYSTICK_HANDLE_COLOR = (200, 200, 200, 200)
BUTTON_SIZE = 60
BUTTON_COLOR = (100, 100, 100, 150)
BUTTON_HIGHLIGHT_COLOR = (150, 150, 150, 200)

# 路徑配置
exe_dir = os.path.dirname(os.path.abspath(sys.executable))
SAVE_DIR = os.path.join(exe_dir, "save")
SCREENSHOT_DIR = os.path.join(exe_dir, "pic")
OGG_DIR = os.path.join(exe_dir, "ogg")
LOG_DIR = os.path.join(exe_dir, "log")
TOOL_DIR = os.path.join(exe_dir, "tools")
BG_PHOTO_PATH = "game_bg.PNG"

# 顏色定義
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BROWN = (139, 69, 19)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
PROGRESS_BG = (50, 50, 50)
PROGRESS_FG = (255, 165, 0)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
ORANGE = (255, 140, 0)
DARK_GREEN = (0, 100, 0)
WOOD_BROWN = (160, 82, 45)
COAL_BLACK = (30, 30, 30)
MEAT_COLOR = (205, 133, 63)
PURPLE = (128, 0, 128)
STONE_GRAY = (100, 100, 100)
DEEP_STONE = (70, 70, 70)
IRON_COLOR = (200, 200, 220)
GOLD_COLOR = (255, 215, 0)
BLOCK_TYPES = {
    0: {"name": "空氣", "color": BLACK, "breakable": False, "hardness": 0, "drop": 0, "tool_need": 0},
    1: {"name": "草塊", "color": GREEN, "breakable": True, "hardness": 2, "drop": 2, "tool_need": 0},
    2: {"name": "泥土", "color": BROWN, "breakable": True, "hardness": 2, "drop": 2, "tool_need": 0},
    3: {"name": "石頭", "color": STONE_GRAY, "breakable": True, "hardness": 5, "drop": 3, "tool_need": 1},
    4: {"name": "水", "color": BLUE, "breakable": False, "hardness": 0, "drop": 0, "tool_need": 0},
    5: {"name": "木頭", "color": WOOD_BROWN, "breakable": True, "hardness": 3, "drop": 5, "tool_need": 0},
    6: {"name": "樹葉", "color": DARK_GREEN, "breakable": True, "hardness": 1, "drop": 0, "tool_need": 0},
    7: {"name": "煤炭", "color": COAL_BLACK, "breakable": True, "hardness": 4, "drop": 7, "tool_need": 1},
    8: {"name": "工作台", "color": WOOD_BROWN, "breakable": True, "hardness": 3, "drop": 8, "tool_need": 0},
    9: {"name": "肉", "color": MEAT_COLOR, "breakable": False, "hardness": 0, "drop": 9, "tool_need": 0},
    10: {"name": "儲物箱", "color": (139, 69, 19), "breakable": True, "hardness": 3, "drop": 10, "tool_need": 0},
    11: {"name": "火把", "color": (255, 200, 0), "breakable": True, "hardness": 1, "drop": 11, "tool_need": 0},
    12: {"name": "鐵鎬", "color": (192, 192, 192), "breakable": False, "hardness": 0, "drop": 12, "tool_need": 0},
    13: {"name": "鐵礦石", "color": IRON_COLOR, "breakable": True, "hardness": 6, "drop": 13, "tool_need": 1},
    14: {"name": "深層石", "color": DEEP_STONE, "breakable": True, "hardness": 6, "drop": 3, "tool_need": 1},
    15: {"name": "金礦石", "color": GOLD_COLOR, "breakable": True, "hardness": 7, "drop": 15, "tool_need": 2},
}

TOOL_TYPES = {
    0: {"name": "徒手", "durability": 0, "efficiency": 1.0, "breakable_blocks": [1, 2, 5, 6]},
    1: {"name": "木鎬", "durability": 60, "efficiency": 2.0, "breakable_blocks": [1, 2, 3, 5, 6, 7]},
    2: {"name": "石鎬", "durability": 132, "efficiency": 4.0, "breakable_blocks": [1, 2, 3, 5, 6, 7, 8, 10, 13]},
    3: {"name": "鐵鎬", "durability": 250, "efficiency": 6.0, "breakable_blocks": [1, 2, 3, 5, 6, 7, 8, 10, 13, 14, 15]},
}

CRAFT_RECIPES = {
    8: {"name": "工作台", "need": {5: 3}, "output": 1, "crafting_station": 0},
    1: {"name": "木鎬", "need": {5: 3, 2: 2}, "output": 1, "crafting_station": 0},
    2: {"name": "石鎬", "need": {3: 3, 5: 2}, "output": 1, "crafting_station": 1},
    10: {"name": "儲物箱", "need": {5: 8}, "output": 1, "crafting_station": 1},
    11: {"name": "火把", "need": {5: 1, 7: 1}, "output": 4, "crafting_station": 1},
    12: {"name": "鐵鎬", "need": {13: 3, 5: 2}, "output": 1, "crafting_station": 1},
}

# 全局變量

WORLD_SEED = random.randint(0, 2**32 - 1)
