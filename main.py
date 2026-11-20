# [file name]: sandbox_game/main.py
"""
沙盒游戏 正式版 1.10.7（历史版本误标为 1.11.1，本版已据实更正）
作者: LongTeam
整合特性:
- 1.11.0 的虚拟按钮、工作台、饥饿系统、死亡界面、内置网络管理器
- 1.10.6rd2 的混合地形生成、出生点安全、日志系统
- 使用新的网络模块 多人遊戲網絡連接2.0.py
"""

import pygame
import random
import sys
import os
import json
import time
import math
import traceback
from datetime import datetime
from collections import OrderedDict
from config import *
from utils import *
from audio import *
from world.terrain import *
from entities.dropitem import *
from entities.monster import *
from entities.player import *

# 導入網絡模塊（net.network：ASCII 包名，跨平台/打包安全；修复 A 级 ImportError 吞异常）
try:
    from net.network import net_manager, PLAYERS, configure as net_configure
    MULTIPLAYER_AVAILABLE = True
except ImportError as e:
    # 不再静默吞掉：明确打印失败原因，便于排查（修复 B 级）
    MULTIPLAYER_AVAILABLE = False
    print(f"警告: 聯機模塊 net.network 導入失敗，多人遊戲功能不可用 -> {e!r}")
    class DummyNetManager:
        def __init__(self):
            self.connected = False
        def send_message(self, msg): pass
        def connect_to_server(self, h, p): return False
        def start_server(self, h, p): return False
        def stop_server(self): pass
    net_manager = DummyNetManager()
    PLAYERS = {}
    def net_configure(*a, **k):
        pass

# ---------------------- 全局配置與初始化 ----------------------
# 方塊類型配置（來自1.11.0，但補充了礦石）
LOADED_CHUNKS = OrderedDict()

# 把世界参数与分块字典同步给网络模块（修复 A 级：原版 import 后从不 configure，
# 导致 LOADED_CHUNKS 在网络模块里永远是 None，分块更新静默丢失）。
if MULTIPLAYER_AVAILABLE:
    net_configure(CHUNK_SIZE, Y_MAX, LOADED_CHUNKS)
DROPS = []
MONSTERS = []
menu_bg = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(BASE_DIR, "fonts", "NotoSans.ttf")):
    BASE_DIR = os.getcwd()
FONT_PATH = os.path.join(BASE_DIR, "fonts", "NotoSans.ttf")
main_font = None
small_font = None
is_day = True
SOUNDS = {"dig": None, "place": None, "hurt": None, "eat": None}

# 性能監控
frame_skip_counter = 0
show_fps = True

# 虛擬搖桿狀態
joystick_active = False
joystick_pos = (JOYSTICK_RADIUS + 20, SCREEN_HEIGHT - JOYSTICK_RADIUS - 20)
joystick_handle_pos = joystick_pos
joystick_vector = (0, 0)

# 虛擬按鈕狀態（1.11.0 完整版）
button_jump_rect = pygame.Rect(SCREEN_WIDTH - BUTTON_SIZE - 20, SCREEN_HEIGHT - BUTTON_SIZE - 20, BUTTON_SIZE, BUTTON_SIZE)
button_inventory_rect = pygame.Rect(SCREEN_WIDTH - BUTTON_SIZE*2 - 40, SCREEN_HEIGHT - BUTTON_SIZE - 20, BUTTON_SIZE, BUTTON_SIZE)
button_dig_rect = pygame.Rect(SCREEN_WIDTH - BUTTON_SIZE - 20, SCREEN_HEIGHT - BUTTON_SIZE*2 - 40, BUTTON_SIZE, BUTTON_SIZE)
button_place_rect = pygame.Rect(SCREEN_WIDTH - BUTTON_SIZE*2 - 40, SCREEN_HEIGHT - BUTTON_SIZE*2 - 40, BUTTON_SIZE, BUTTON_SIZE)
button_esc_rect = pygame.Rect(20, 20, BUTTON_SIZE, BUTTON_SIZE)
button_f5_rect = pygame.Rect(20, 20 + BUTTON_SIZE + 10, BUTTON_SIZE, BUTTON_SIZE)

# 設置選項（增加死亡保留物品欄）
SETTINGS = {
    "virtual_joystick": True,
    "virtual_buttons": True,
    "sound_volume": 0.7,
    "music_volume": 0.5,
    "render_distance": 3,
    "fps_limit": 60,
    "keep_inventory_on_death": False,
}

# ---------------------- 日誌系統（1.10.6rd2 風格） ----------------------

game_logger = None


# ---------------------- 音效與音樂 ----------------------





# ---------------------- 性能優化函數 ----------------------

def limit_updates_per_frame(entities, max_updates=MAX_UPDATES_PER_FRAME):
    if len(entities) <= max_updates:
        return entities
    return entities[:max_updates]

def should_update_this_frame():
    global frame_skip_counter
    frame_skip_counter += 1
    return frame_skip_counter % FRAME_SKIP == 0

# ---------------------- 柏林噪聲（1.10.6rd2 混合地形用） ----------------------

# ---------------------- 混合地形生成器（1.10.6rd2） ----------------------


# ---------------------- 虛擬控制函數（1.11.0 完整版） ----------------------
def draw_virtual_controls(screen):
    if not VIRTUAL_JOYSTICK_ENABLED and not VIRTUAL_BUTTONS_ENABLED:
        return
        
    if VIRTUAL_JOYSTICK_ENABLED:
        pygame.draw.circle(screen, JOYSTICK_BASE_COLOR, joystick_pos, JOYSTICK_RADIUS)
        pygame.draw.circle(screen, JOYSTICK_HANDLE_COLOR, joystick_handle_pos, JOYSTICK_RADIUS//2)
    
    if VIRTUAL_BUTTONS_ENABLED:
        # 跳跃按钮
        pygame.draw.circle(screen, BUTTON_COLOR, button_jump_rect.center, BUTTON_SIZE//2)
        jump_text = small_font.render("跳", True, WHITE)
        screen.blit(jump_text, (button_jump_rect.centerx - jump_text.get_width()//2, 
                               button_jump_rect.centery - jump_text.get_height()//2))
        
        # 物品栏按钮
        pygame.draw.circle(screen, BUTTON_COLOR, button_inventory_rect.center, BUTTON_SIZE//2)
        inv_text = small_font.render("包", True, WHITE)
        screen.blit(inv_text, (button_inventory_rect.centerx - inv_text.get_width()//2, 
                              button_inventory_rect.centery - inv_text.get_height()//2))
        
        # 挖掘按钮
        pygame.draw.circle(screen, BUTTON_COLOR, button_dig_rect.center, BUTTON_SIZE//2)
        dig_text = small_font.render("挖", True, WHITE)
        screen.blit(dig_text, (button_dig_rect.centerx - dig_text.get_width()//2, 
                              button_dig_rect.centery - dig_text.get_height()//2))
        
        # 放置按钮
        pygame.draw.circle(screen, BUTTON_COLOR, button_place_rect.center, BUTTON_SIZE//2)
        place_text = small_font.render("放", True, WHITE)
        screen.blit(place_text, (button_place_rect.centerx - place_text.get_width()//2, 
                                button_place_rect.centery - place_text.get_height()//2))
        
        # ESC按钮
        pygame.draw.circle(screen, BUTTON_COLOR, button_esc_rect.center, BUTTON_SIZE//2)
        esc_text = small_font.render("ESC", True, WHITE)
        screen.blit(esc_text, (button_esc_rect.centerx - esc_text.get_width()//2, 
                              button_esc_rect.centery - esc_text.get_height()//2))
        
        # F5按钮
        pygame.draw.circle(screen, BUTTON_COLOR, button_f5_rect.center, BUTTON_SIZE//2)
        f5_text = small_font.render("F5", True, WHITE)
        screen.blit(f5_text, (button_f5_rect.centerx - f5_text.get_width()//2, 
                             button_f5_rect.centery - f5_text.get_height()//2))

def handle_virtual_controls(event, player, screen):
    global joystick_active, joystick_handle_pos, joystick_vector
    
    if not VIRTUAL_JOYSTICK_ENABLED and not VIRTUAL_BUTTONS_ENABLED:
        return False
        
    if event.type == pygame.MOUSEBUTTONDOWN:
        pos = event.pos
        
        if VIRTUAL_JOYSTICK_ENABLED:
            distance = math.hypot(pos[0] - joystick_pos[0], pos[1] - joystick_pos[1])
            if distance <= JOYSTICK_RADIUS:
                joystick_active = True
                joystick_handle_pos = pos
                return True
        
        if VIRTUAL_BUTTONS_ENABLED:
            if button_jump_rect.collidepoint(pos):
                if player.on_ground:
                    player.velocity_y = -player.jump_power
                    player.on_ground = False
                return True
            elif button_inventory_rect.collidepoint(pos):
                player.bag_open = not player.bag_open
                player.workbench_open = False
                return True
            elif button_dig_rect.collidepoint(pos):
                perform_dig_action(player)
                return True
            elif button_place_rect.collidepoint(pos):
                perform_place_action(player, screen)
                return True
            elif button_esc_rect.collidepoint(pos):
                return_to_main_menu(screen)
                return True
            elif button_f5_rect.collidepoint(pos):
                save_data = {"player": player.to_save_data(), "game_state": {"current_map": "平原", "time": "白天" if is_day else "黑夜", "completed_quests": []}}
                success, msg = create_json_file(get_save_path(player.name), save_data, LOADED_CHUNKS, WORLD_SEED)
                show_tip(screen, msg)
                return True
    
    elif event.type == pygame.MOUSEMOTION:
        if joystick_active and VIRTUAL_JOYSTICK_ENABLED:
            pos = event.pos
            dx = pos[0] - joystick_pos[0]
            dy = pos[1] - joystick_pos[1]
            distance = math.hypot(dx, dy)
            
            if distance <= JOYSTICK_RADIUS:
                joystick_handle_pos = pos
            else:
                angle = math.atan2(dy, dx)
                joystick_handle_pos = (
                    joystick_pos[0] + math.cos(angle) * JOYSTICK_RADIUS,
                    joystick_pos[1] + math.sin(angle) * JOYSTICK_RADIUS
                )
            
            joystick_vector = (
                (joystick_handle_pos[0] - joystick_pos[0]) / JOYSTICK_RADIUS,
                (joystick_handle_pos[1] - joystick_pos[1]) / JOYSTICK_RADIUS
            )
            return True
    
    elif event.type == pygame.MOUSEBUTTONUP:
        if joystick_active:
            joystick_active = False
            joystick_handle_pos = joystick_pos
            joystick_vector = (0, 0)
            return True
    
    return False


def perform_dig_action(player):
    """虚拟挖掘按钮触发的动作"""
    # 获取屏幕中心位置（玩家视角中心）
    mouse_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    target_block = get_mouse_block(mouse_pos, player)
    block_x, block_y, block_z = target_block
    chunk_x, chunk_z = int(block_x//CHUNK_SIZE), int(block_z//CHUNK_SIZE)
    
    if (chunk_x, chunk_z) in LOADED_CHUNKS:
        chunk = LOADED_CHUNKS[(chunk_x, chunk_z)]
        in_x, in_z = int(block_x % CHUNK_SIZE), int(block_z % CHUNK_SIZE)
        if 0 <= in_x < CHUNK_SIZE and 0 <= block_y < Y_MAX and 0 <= in_z < CHUNK_SIZE:
            block_id = chunk.blocks[in_x][block_y][in_z]
            if block_id != 0 and BLOCK_TYPES[block_id]["breakable"]:
                # 发送方块破坏消息
                if IS_CLIENT or IS_SERVER:
                    dig_msg = {
                        'type': 'block_update',
                        'position': [block_x, block_y, block_z],
                        'block_id': 0,
                        'player_id': player.name
                    }
                    net_manager.send_message(dig_msg)
                
                chunk.blocks[in_x][block_y][in_z] = 0
                play_sound("dig")
                drop_id = BLOCK_TYPES[block_id]["drop"]
                if drop_id != 0:
                    DROPS.append(DropItem(block_x, block_z, drop_id))

def perform_place_action(player, screen):
    """虚拟放置按钮触发的动作"""
    # 获取屏幕中心位置
    mouse_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    target_block = get_mouse_block(mouse_pos, player)
    block_x, block_y, block_z = target_block
    chunk_x, chunk_z = int(block_x//CHUNK_SIZE), int(block_z//CHUNK_SIZE)
    
    if (chunk_x, chunk_z) in LOADED_CHUNKS:
        chunk = LOADED_CHUNKS[(chunk_x, chunk_z)]
        in_x, in_z = int(block_x % CHUNK_SIZE), int(block_z % CHUNK_SIZE)
        if 0 <= in_x < CHUNK_SIZE and 0 <= block_y < Y_MAX and 0 <= in_z < CHUNK_SIZE:
            block_id = chunk.blocks[in_x][block_y][in_z]
            if block_id == 8:  # 工作台
                player.interact_with_workbench()
                return
    
    # 使用物品
    if player.bag_selected == 9:  # 肉
        success, message = player.use_item(9)
        if success:
            play_sound("eat")
            show_quick_message(screen, message, 1000)
            return
    
    # 放置方块
    if player.inventory.get(player.bag_selected, 0) > 0:
        mouse_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        target_block = get_mouse_block(mouse_pos, player)
        block_x, block_y, block_z = target_block
        chunk_x, chunk_z = int(block_x//CHUNK_SIZE), int(block_z//CHUNK_SIZE)
        if (chunk_x, chunk_z) in LOADED_CHUNKS:
            chunk = LOADED_CHUNKS[(chunk_x, chunk_z)]
            in_x, in_z = int(block_x % CHUNK_SIZE), int(block_z % CHUNK_SIZE)
            if 0 <= in_x < CHUNK_SIZE and 0 <= block_y < Y_MAX and 0 <= in_z < CHUNK_SIZE:
                if chunk.blocks[in_x][block_y][in_z] == 0:
                    # 发送方块放置消息
                    if IS_CLIENT or IS_SERVER:
                        place_msg = {
                            'type': 'block_update',
                            'position': [block_x, block_y, block_z],
                            'block_id': player.bag_selected,
                            'player_id': player.name
                        }
                        net_manager.send_message(place_msg)
                    
                    chunk.blocks[in_x][block_y][in_z] = player.bag_selected
                    player.inventory[player.bag_selected] -= 1
                    play_sound("place")

# ---------------------- 地圖繪製與交互輔助 ----------------------
def draw_infinite_map(screen, loaded_chunks, player):
    player_screen_x = SCREEN_WIDTH // 2
    player_screen_y = SCREEN_HEIGHT // 2
    visible_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
    
    for (chunk_x, chunk_z), chunk in loaded_chunks.items():
        chunk_screen_x = (chunk_x * CHUNK_SIZE - player.world_x) * BLOCK_SIZE + player_screen_x
        chunk_screen_z = (chunk_z * CHUNK_SIZE - player.world_z) * BLOCK_SIZE + player_screen_y
        chunk_rect = pygame.Rect(chunk_screen_x, chunk_screen_z, CHUNK_SIZE*BLOCK_SIZE, CHUNK_SIZE*BLOCK_SIZE)
        if not visible_rect.colliderect(chunk_rect):
            continue
        dist = math.hypot(chunk_x - player.world_x//CHUNK_SIZE, chunk_z - player.world_z//CHUNK_SIZE)
        alpha = max(50, 255 - int(dist / SETTINGS["render_distance"] * 200))
        
        for x in range(CHUNK_SIZE):
            for z_range in range(CHUNK_SIZE):
                block_screen_x = chunk_screen_x + x * BLOCK_SIZE
                block_screen_y = chunk_screen_z + z_range * BLOCK_SIZE
                if (block_screen_x + BLOCK_SIZE < 0 or block_screen_x > SCREEN_WIDTH or 
                    block_screen_y + BLOCK_SIZE < 0 or block_screen_y > SCREEN_HEIGHT):
                    continue
                for y in range(Y_MAX-1, -1, -1):
                    block_id = chunk.blocks[x][y][z_range]
                    if block_id != 0:
                        block_surf = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
                        block_surf.fill(BLOCK_TYPES[block_id]["color"])
                        block_surf.set_alpha(alpha)
                        screen.blit(block_surf, (block_screen_x, block_screen_y))
                        pygame.draw.rect(screen, GRAY, (block_screen_x, block_screen_y, BLOCK_SIZE, BLOCK_SIZE), 1)
                        break

def get_mouse_block(pos, player):
    screen_center_x = SCREEN_WIDTH // 2
    screen_center_y = SCREEN_HEIGHT // 2
    mouse_world_x = player.world_x + (pos[0] - screen_center_x) / BLOCK_SIZE
    mouse_world_z = player.world_z + (pos[1] - screen_center_y) / BLOCK_SIZE
    mouse_world_y = int(player.world_z)  # 简化，实际应使用高度层
    mouse_world_x = max(0, min(mouse_world_x, CHUNK_SIZE * 1000 - 1))
    mouse_world_y = max(0, min(mouse_world_y, Y_MAX - 1))
    mouse_world_z = max(0, min(mouse_world_z, CHUNK_SIZE * 1000 - 1))
    return (int(math.floor(mouse_world_x)), mouse_world_y, int(math.floor(mouse_world_z)))

def draw_dig_progress(screen, target_block, player, dig_progress):
    if dig_progress <= 0:
        return
    block_world_x, block_world_y, block_world_z = target_block
    block_screen_x = int((block_world_x - player.world_x) * BLOCK_SIZE + SCREEN_WIDTH//2)
    block_screen_y = int((block_world_z - player.world_z) * BLOCK_SIZE + SCREEN_HEIGHT//2)
    if (block_screen_x < -BLOCK_SIZE or block_screen_x > SCREEN_WIDTH or
        block_screen_y < -BLOCK_SIZE or block_screen_y > SCREEN_HEIGHT):
        return
    bar_x = block_screen_x
    bar_y = block_screen_y + BLOCK_SIZE + 5
    pygame.draw.rect(screen, PROGRESS_BG, (bar_x, bar_y, BLOCK_SIZE, 6))
    progress_width = int(BLOCK_SIZE * (dig_progress / 100))
    pygame.draw.rect(screen, PROGRESS_FG, (bar_x, bar_y, progress_width, 6))
    flash_freq = max(50, 200 - int(dig_progress * 1.5))
    if int(time.time() * 1000) % flash_freq < flash_freq // 2:
        pygame.draw.rect(screen, YELLOW, (block_screen_x, block_screen_y, BLOCK_SIZE, BLOCK_SIZE), 2)

def show_quick_message(screen, message, duration=1000):
    """在屏幕中央快速显示一条消息"""
    message_surface = pygame.Surface((400, 50), pygame.SRCALPHA)
    message_surface.fill((0, 0, 0, 180))
    message_text = small_font.render(message, True, WHITE)
    text_rect = message_text.get_rect(center=(200, 25))
    message_surface.blit(message_text, text_rect)
    screen_rect = message_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
    screen.blit(message_surface, screen_rect)
    pygame.display.flip()
    pygame.time.wait(duration)
# ---------------------- 核心类定义 ----------------------



# ---------------------- 设置管理 ----------------------
def load_settings():
    global SETTINGS, VIRTUAL_JOYSTICK_ENABLED, VIRTUAL_BUTTONS_ENABLED, RENDER_DISTANCE, FPS
    settings_path = os.path.join(exe_dir, "settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                loaded_settings = json.load(f)
                SETTINGS.update(loaded_settings)
        except Exception as e:
            log(f"加载设置失败: {e}")
    VIRTUAL_JOYSTICK_ENABLED = SETTINGS["virtual_joystick"]
    VIRTUAL_BUTTONS_ENABLED = SETTINGS["virtual_buttons"]
    RENDER_DISTANCE = SETTINGS["render_distance"]
    FPS = SETTINGS["fps_limit"]
    for sound in SOUNDS.values():
        if sound:
            sound.set_volume(SETTINGS["sound_volume"])
    pygame.mixer.music.set_volume(SETTINGS["music_volume"])

def save_settings():
    settings_path = os.path.join(exe_dir, "settings.json")
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(SETTINGS, f, ensure_ascii=False, indent=2)
        log("设置保存成功")
        return True
    except Exception as e:
        log(f"保存设置失败: {e}")
        return False

# ---------------------- 存档模块 ----------------------
def get_save_path(player_name):
    return os.path.join(SAVE_DIR, f"{player_name}.json")

def create_json_file(file_path, data, loaded_chunks, world_seed):
    try:
        save_data = {
            "player": data["player"],
            "world_seed": world_seed,
            "loaded_chunks": {},
            "game_state": data["game_state"]
        }
        for (chunk_x, chunk_z), chunk in loaded_chunks.items():
            default_chunk = Chunk(chunk_x, chunk_z, world_seed)
            non_default_blocks = []
            for x in range(CHUNK_SIZE):
                for y in range(Y_MAX):
                    for z_range in range(CHUNK_SIZE):
                        current = chunk.blocks[x][y][z_range]
                        default = default_chunk.blocks[x][y][z_range]
                        if current != 0 and current != default:
                            non_default_blocks.append((x, y, z_range, current))
            save_data["loaded_chunks"][f"{chunk_x},{chunk_z}"] = non_default_blocks
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        player_name = data["player"]["name"]
        for i in range(2, 0, -1):
            old_backup = os.path.join(SAVE_DIR, f"{player_name}_backup{i}.json")
            new_backup = os.path.join(SAVE_DIR, f"{player_name}_backup{i+1}.json")
            if os.path.exists(old_backup):
                try:
                    os.rename(old_backup, new_backup)
                except Exception as e:
                    log(f"备份重命名失败: {e}")
        if os.path.exists(file_path):
            try:
                os.rename(file_path, os.path.join(SAVE_DIR, f"{player_name}_backup1.json"))
            except Exception as e:
                log(f"主存档重命名失败: {e}")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        log(f"存档成功：{file_path}")
        return True, "存档成功（含3个备份）"
    except Exception as e:
        log(f"存档失败：{str(e)}")
        return False, f"存档失败：{str(e)}"

def load_json_file(file_path):
    try:
        if not os.path.exists(file_path):
            player_name = os.path.basename(file_path).replace(".json", "")
            for i in range(1, 4):
                backup_path = os.path.join(SAVE_DIR, f"{player_name}_backup{i}.json")
                if os.path.exists(backup_path):
                    file_path = backup_path
                    log(f"加载备份：{backup_path}")
                    break
            else:
                return False, "主存档与备份均不存在", None, None, None
        with open(file_path, "r", encoding="utf-8") as f:
            save_data = json.load(f)
        if "world_seed" not in save_data or save_data["world_seed"] is None:
            save_data["world_seed"] = random.randint(0, 2**32 - 1)
            log(f"补全随机种子：{save_data['world_seed']}")
        world_seed = save_data["world_seed"]
        loaded_chunks = OrderedDict()
        for chunk_key_str, non_default_blocks in save_data["loaded_chunks"].items():
            try:
                chunk_x, chunk_z = map(int, chunk_key_str.split(","))
                chunk = Chunk(chunk_x, chunk_z, world_seed)
                for (x, y, z_range, block_id) in non_default_blocks:
                    if 0 <= x < CHUNK_SIZE and 0 <= y < Y_MAX and 0 <= z_range < CHUNK_SIZE:
                        chunk.blocks[x][y][z_range] = block_id
                loaded_chunks[(chunk_x, chunk_z)] = chunk
            except Exception as e:
                log(f"加载区块失败 {chunk_key_str}: {e}")
                continue
        player_data = save_data["player"]
        log(f"加载存档成功：{file_path}")
        return True, "加载成功", player_data, loaded_chunks, world_seed
    except Exception as e:
        log(f"加载失败：{str(e)}")
        return False, f"加载失败：{str(e)}", None, None, None

def load_save_list():
    saves = []
    if not os.path.exists(SAVE_DIR):
        return saves
    try:
        for file in os.listdir(SAVE_DIR):
            if file.endswith(".json") and not file.startswith("_backup") and not file.endswith("_backup.json"):
                saves.append(file.replace(".json", ""))
    except Exception as e:
        log(f"读取存档列表失败: {e}")
    return saves

# ---------------------- 死亡界面 ----------------------
def show_death_screen(screen, player, game_mode, fullscreen):
    screen.fill((50, 0, 0))
    death_text = main_font.render("你死了!", True, RED)
    death_rect = death_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//4))
    screen.blit(death_text, death_rect)
    cause_text = small_font.render("生命值归零", True, WHITE)
    cause_rect = cause_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//4 + 60))
    screen.blit(cause_text, cause_rect)
    btn_width, btn_height = 300, 50
    btn_margin = 20
    respawn_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, SCREEN_HEIGHT//2, btn_width, btn_height)
    menu_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, SCREEN_HEIGHT//2 + btn_height + btn_margin, btn_width, btn_height)
    pygame.draw.rect(screen, GREEN, respawn_btn)
    pygame.draw.rect(screen, BLUE, menu_btn)
    respawn_text = small_font.render("重新开始", True, BLACK)
    menu_text = small_font.render("返回主菜单", True, BLACK)
    screen.blit(respawn_text, (respawn_btn.x + btn_width//2 - respawn_text.get_width()//2, 
                               respawn_btn.y + btn_height//2 - respawn_text.get_height()//2))
    screen.blit(menu_text, (menu_btn.x + btn_width//2 - menu_text.get_width()//2, 
                            menu_btn.y + btn_height//2 - menu_text.get_height()//2))
    inventory_setting = "开" if SETTINGS["keep_inventory_on_death"] else "关"
    setting_text = small_font.render(f"死亡保存物品栏: {inventory_setting}", True, YELLOW)
    screen.blit(setting_text, (SCREEN_WIDTH//2 - setting_text.get_width()//2, SCREEN_HEIGHT - 100))
    pygame.display.flip()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if respawn_btn.collidepoint(mx, my):
                    return "respawn"
                elif menu_btn.collidepoint(mx, my):
                    return "menu"

def reset_player(player, keep_inventory=False):
    spawn_x, spawn_z, spawn_y = find_safe_spawn_location()
    player.world_x = spawn_x
    player.world_z = spawn_z
    player.z = spawn_y
    player.hp = 100
    player.hunger = 100
    if not keep_inventory:
        player.inventory = {1: 0, 2: 0, 3: 0, 5: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        player.tools = {0: 0, 1: 0, 2: 0, 3: 0}
        player.current_tool = 0
        log(f"玩家{player.name}死亡，物品栏已清空")
    else:
        log(f"玩家{player.name}死亡，物品栏已保留")
    player.velocity_y = 0
    player.on_ground = False
    player.bag_open = False
    player.workbench_open = False
    return player

# ---------------------- 界面模块 ----------------------
def show_main_menu(screen):
    global menu_bg
    screen.blit(menu_bg, (0, 0))
    title_text = main_font.render("沙盒游戏 1.11.1 正式版", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//8))
    screen.blit(title_text, title_rect)
    btn_width, btn_height = 350, 70
    btn_margin = 20
    btn_y_start = SCREEN_HEIGHT//4
    sandbox_btn = pygame.Rect(SCREEN_WIDTH//4 - btn_width//2, btn_y_start, btn_width, btn_height)
    wzmc_new_btn = pygame.Rect(3*SCREEN_WIDTH//4 - btn_width//2, btn_y_start, btn_width, btn_height)
    wzmc_load_btn = pygame.Rect(SCREEN_WIDTH//4 - btn_width//2, btn_y_start + btn_height + btn_margin, btn_width, btn_height)
    multiplayer_btn = pygame.Rect(3*SCREEN_WIDTH//4 - btn_width//2, btn_y_start + btn_height + btn_margin, btn_width, btn_height)
    settings_btn = pygame.Rect(SCREEN_WIDTH//4 - btn_width//2, btn_y_start + 2*(btn_height + btn_margin), btn_width, btn_height)
    controls_btn = pygame.Rect(3*SCREEN_WIDTH//4 - btn_width//2, btn_y_start + 2*(btn_height + btn_margin), btn_width, btn_height)
    about_btn = pygame.Rect(SCREEN_WIDTH//4 - btn_width//2, btn_y_start + 3*(btn_height + btn_margin), btn_width, btn_height)
    quit_btn = pygame.Rect(3*SCREEN_WIDTH//4 - btn_width//2, btn_y_start + 3*(btn_height + btn_margin), btn_width, btn_height)
    pygame.draw.rect(screen, GREEN, sandbox_btn)
    pygame.draw.rect(screen, BROWN, wzmc_new_btn)
    pygame.draw.rect(screen, BLUE, wzmc_load_btn)
    pygame.draw.rect(screen, PURPLE, multiplayer_btn)
    pygame.draw.rect(screen, ORANGE, settings_btn)
    pygame.draw.rect(screen, (100, 100, 255), controls_btn)
    pygame.draw.rect(screen, (200, 100, 200), about_btn)
    pygame.draw.rect(screen, RED, quit_btn)
    screen.blit(small_font.render("沙盒模式", True, BLACK), (sandbox_btn.x + btn_width//2 - 40, sandbox_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("新游戏", True, BLACK), (wzmc_new_btn.x + btn_width//2 - 30, wzmc_new_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("加载存档", True, BLACK), (wzmc_load_btn.x + btn_width//2 - 40, wzmc_load_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("多人联机", True, BLACK), (multiplayer_btn.x + btn_width//2 - 40, multiplayer_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("游戏设置", True, BLACK), (settings_btn.x + btn_width//2 - 40, settings_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("控制设置", True, BLACK), (controls_btn.x + btn_width//2 - 40, controls_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("关于游戏", True, BLACK), (about_btn.x + btn_width//2 - 40, about_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("退出游戏", True, BLACK), (quit_btn.x + btn_width//2 - 40, quit_btn.y + btn_height//2 - 10))
    pygame.display.flip()
    return (sandbox_btn, wzmc_new_btn, wzmc_load_btn, multiplayer_btn, settings_btn, controls_btn, about_btn, quit_btn)

def show_multiplayer_menu(screen):
    screen.fill(BLACK)
    title_text = main_font.render("多人联机", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//8))
    screen.blit(title_text, title_rect)
    btn_width, btn_height = 400, 50
    btn_margin = 15
    btn_y_start = SCREEN_HEIGHT//4
    host_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start, btn_width, btn_height)
    join_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + btn_height + btn_margin, btn_width, btn_height)
    back_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + 2*(btn_height + btn_margin), btn_width, btn_height)
    pygame.draw.rect(screen, GREEN, host_btn)
    pygame.draw.rect(screen, BLUE, join_btn)
    pygame.draw.rect(screen, GRAY, back_btn)
    screen.blit(small_font.render("创建服务器", True, BLACK), (host_btn.x + 20, host_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("加入服务器", True, BLACK), (join_btn.x + 20, join_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("返回主菜单", True, BLACK), (back_btn.x + 20, back_btn.y + btn_height//2 - 10))
    pygame.display.flip()
    return host_btn, join_btn, back_btn

def show_join_server_menu(screen):
    screen.fill(BLACK)
    title_text = main_font.render("加入服务器", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//8))
    screen.blit(title_text, title_rect)
    input_width, input_height = 400, 50
    input_y_start = SCREEN_HEIGHT//4
    ip_label = small_font.render("服务器地址 (IP:端口):", True, WHITE)
    screen.blit(ip_label, (SCREEN_WIDTH//2 - input_width//2, input_y_start - 30))
    ip_input_rect = pygame.Rect(SCREEN_WIDTH//2 - input_width//2, input_y_start, input_width, input_height)
    pygame.draw.rect(screen, WHITE, ip_input_rect, 2)
    default_ip = "127.0.0.1:8765"
    ip_text = default_ip
    btn_width, btn_height = 200, 50
    btn_margin = 20
    btn_y_start = input_y_start + input_height + 50
    connect_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start, btn_width, btn_height)
    back_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + btn_height + btn_margin, btn_width, btn_height)
    pygame.draw.rect(screen, GREEN, connect_btn)
    pygame.draw.rect(screen, GRAY, back_btn)
    screen.blit(small_font.render("连接服务器", True, BLACK), (connect_btn.x + 50, connect_btn.y + btn_height//2 - 10))
    screen.blit(small_font.render("返回", True, BLACK), (back_btn.x + 70, back_btn.y + btn_height//2 - 10))
    text_surface = small_font.render(ip_text, True, WHITE)
    screen.blit(text_surface, (ip_input_rect.x + 10, ip_input_rect.y + input_height//2 - 10))
    pygame.display.flip()
    return ip_input_rect, connect_btn, back_btn, default_ip

def show_settings_menu(screen):
    screen.fill(BLACK)
    title_text = main_font.render("游戏设置", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//8))
    screen.blit(title_text, title_rect)
    btn_width, btn_height = 400, 50
    btn_margin = 15
    btn_y_start = SCREEN_HEIGHT//4
    joystick_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start, btn_width, btn_height)
    pygame.draw.rect(screen, GREEN if SETTINGS["virtual_joystick"] else RED, joystick_btn)
    joystick_text = small_font.render(f"虚拟摇杆: {'开' if SETTINGS['virtual_joystick'] else '关'}", True, BLACK)
    screen.blit(joystick_text, (joystick_btn.x + 20, joystick_btn.y + btn_height//2 - 10))
    buttons_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + btn_height + btn_margin, btn_width, btn_height)
    pygame.draw.rect(screen, GREEN if SETTINGS["virtual_buttons"] else RED, buttons_btn)
    buttons_text = small_font.render(f"虚拟按钮: {'开' if SETTINGS['virtual_buttons'] else '关'}", True, BLACK)
    screen.blit(buttons_text, (buttons_btn.x + 20, buttons_btn.y + btn_height//2 - 10))
    inventory_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + 2*(btn_height + btn_margin), btn_width, btn_height)
    pygame.draw.rect(screen, GREEN if SETTINGS["keep_inventory_on_death"] else RED, inventory_btn)
    inventory_text = small_font.render(f"死亡保存物品栏: {'开' if SETTINGS['keep_inventory_on_death'] else '关'}", True, BLACK)
    screen.blit(inventory_text, (inventory_btn.x + 20, inventory_btn.y + btn_height//2 - 10))
    sound_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + 3*(btn_height + btn_margin), btn_width, btn_height)
    pygame.draw.rect(screen, BLUE, sound_btn)
    sound_text = small_font.render(f"声音音量: {int(SETTINGS['sound_volume'] * 100)}%", True, BLACK)
    screen.blit(sound_text, (sound_btn.x + 20, sound_btn.y + btn_height//2 - 10))
    music_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + 4*(btn_height + btn_margin), btn_width, btn_height)
    pygame.draw.rect(screen, BLUE, music_btn)
    music_text = small_font.render(f"音乐音量: {int(SETTINGS['music_volume'] * 100)}%", True, BLACK)
    screen.blit(music_text, (music_btn.x + 20, music_btn.y + btn_height//2 - 10))
    render_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + 5*(btn_height + btn_margin), btn_width, btn_height)
    pygame.draw.rect(screen, ORANGE, render_btn)
    render_text = small_font.render(f"渲染距离: {SETTINGS['render_distance']}", True, BLACK)
    screen.blit(render_text, (render_btn.x + 20, render_btn.y + btn_height//2 - 10))
    fps_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + 6*(btn_height + btn_margin), btn_width, btn_height)
    pygame.draw.rect(screen, ORANGE, fps_btn)
    fps_text = small_font.render(f"FPS限制: {SETTINGS['fps_limit']}", True, BLACK)
    screen.blit(fps_text, (fps_btn.x + 20, fps_btn.y + btn_height//2 - 10))
    back_btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y_start + 7*(btn_height + btn_margin), btn_width, btn_height)
    pygame.draw.rect(screen, GRAY, back_btn)
    back_text = small_font.render("返回主菜单", True, BLACK)
    screen.blit(back_text, (back_btn.x + btn_width//2 - 40, back_btn.y + btn_height//2 - 10))
    pygame.display.flip()
    return (joystick_btn, buttons_btn, inventory_btn, sound_btn, music_btn, render_btn, fps_btn, back_btn)

def show_save_list(screen, scroll_offset, btn_spacing, visible_btn_count):
    screen.fill(BLACK)
    title_text = main_font.render("选择wzmc存档", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//8))
    screen.blit(title_text, title_rect)
    saves = load_save_list()
    btn_list = []
    btn_width, btn_height = 350, 50
    btn_y_start = SCREEN_HEIGHT//4
    for i, save_name in enumerate(saves):
        btn_y = btn_y_start + i * (btn_spacing + 10) - scroll_offset
        if btn_y + btn_height < 0 or btn_y > SCREEN_HEIGHT - 150:
            continue
        btn = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, btn_y, btn_width, btn_height)
        pygame.draw.rect(screen, ORANGE, btn)
        screen.blit(small_font.render(f"存档 {i+1}: {save_name}", True, BLACK), (btn.x + 20, btn.y + 12))
        btn_list.append((btn, save_name))
    back_btn = pygame.Rect(SCREEN_WIDTH//4 - 100, SCREEN_HEIGHT - 110, 200, 50)
    delete_btn = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT - 110, 200, 50)
    import_btn = pygame.Rect(3*SCREEN_WIDTH//4 - 100, SCREEN_HEIGHT - 110, 200, 50)
    pygame.draw.rect(screen, GRAY, back_btn)
    pygame.draw.rect(screen, RED, delete_btn)
    pygame.draw.rect(screen, YELLOW, import_btn)
    screen.blit(small_font.render("返回主菜单", True, BLACK), (back_btn.x + 40, back_btn.y + 12))
    screen.blit(small_font.render("删除选中存档", True, BLACK), (delete_btn.x + 30, delete_btn.y + 12))
    screen.blit(small_font.render("导入.sbx存档", True, BLACK), (import_btn.x + 30, import_btn.y + 12))
    if len(saves) > visible_btn_count:
        scroll_tip = small_font.render("鼠标滚轮滚动查看更多", True, GRAY)
        screen.blit(scroll_tip, (SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT - 30))
    pygame.display.flip()
    return btn_list, back_btn, delete_btn, import_btn, saves

def show_controls_info(screen):
    screen.fill(BLACK)
    title_text = main_font.render("控制说明", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//8))
    screen.blit(title_text, title_rect)
    controls = [
        "键盘控制:", "W/A/S/D - 移动", "空格 - 跳跃", "鼠标左键 - 挖掘方块",
        "鼠标右键 - 放置方块/使用物品", "1/2/3 - 切换工具", "I - 打开/关闭物品栏",
        "ESC - 返回主菜单", "F5 - 快速保存", "", "触摸控制:", "虚拟摇杆 - 移动",
        "跳跃按钮 - 跳跃", "物品栏按钮 - 打开物品栏", "挖掘按钮 - 挖掘方块",
        "放置按钮 - 放置方块/使用物品", "ESC按钮 - 返回主菜单", "F5按钮 - 快速保存"
    ]
    y_pos = SCREEN_HEIGHT//4
    for control in controls:
        text = small_font.render(control, True, WHITE)
        screen.blit(text, (SCREEN_WIDTH//2 - 200, y_pos))
        y_pos += 30
    back_btn = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT - 100, 200, 50)
    pygame.draw.rect(screen, GRAY, back_btn)
    back_text = small_font.render("返回主菜单", True, BLACK)
    screen.blit(back_text, (back_btn.x + 50, back_btn.y + 15))
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_btn.collidepoint(event.pos):
                    waiting = False

def show_about_screen(screen):
    screen.fill(BLACK)
    title_text = main_font.render("关于游戏", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//8))
    screen.blit(title_text, title_rect)
    about_info = [
        "沙盒游戏 1.11.1 正式版",
        "基于Python和Pygame开发",
        "",
        "新增功能:",
        "- 工作台系统：可合成更多工具和物品",
        "- 饥饿系统：食物可以恢复饥饿值",
        "- 铁矿石和铁镐：更高级的采矿工具",
        "- 储物箱和火把：新的实用方块",
        "- 改进的多人游戏系统（TCP Socket）",
        "- 完整的虚拟按钮支持",
        "- 死亡界面及物品栏保留设置",
        "",
        "开发者: long",
        "QQ群: 131293550"
    ]
    y_pos = SCREEN_HEIGHT//4
    for info in about_info:
        text = small_font.render(info, True, WHITE)
        screen.blit(text, (SCREEN_WIDTH//2 - 200, y_pos))
        y_pos += 30
    back_btn = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT - 100, 200, 50)
    pygame.draw.rect(screen, GRAY, back_btn)
    back_text = small_font.render("返回主菜单", True, BLACK)
    screen.blit(back_text, (back_btn.x + 50, back_btn.y + 15))
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_btn.collidepoint(event.pos):
                    waiting = False

def show_tip(screen, tip_text, duration=1500):
    screen.fill(BLACK)
    text_surf = small_font.render(tip_text, True, WHITE)
    text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
    screen.blit(text_surf, text_rect)
    pygame.display.flip()
    time.sleep(duration / 1000)

def find_safe_spawn_location():
    for attempt in range(100):
        spawn_x = random.randint(-10, 10)
        spawn_z = random.randint(-10, 10)
        chunk_x = int(spawn_x // CHUNK_SIZE)
        chunk_z = int(spawn_z // CHUNK_SIZE)
        if (chunk_x, chunk_z) not in LOADED_CHUNKS:
            LOADED_CHUNKS[(chunk_x, chunk_z)] = Chunk(chunk_x, chunk_z, WORLD_SEED)
        chunk = LOADED_CHUNKS[(chunk_x, chunk_z)]
        in_x = int(spawn_x % CHUNK_SIZE)
        in_z = int(spawn_z % CHUNK_SIZE)
        safe_y = None
        for y in range(Y_MAX-1, -1, -1):
            if chunk.blocks[in_x][y][in_z] != 0:
                safe_y = y + 1
                break
        if safe_y is not None and safe_y < Y_MAX:
            has_space = True
            for check_y in range(safe_y, min(safe_y + 2, Y_MAX)):
                if chunk.blocks[in_x][check_y][in_z] != 0:
                    has_space = False
                    break
            if has_space:
                return spawn_x, spawn_z, safe_y
    return 0, 0, 10

def load_chunks_around_player(player):
    player_chunk_x = int(player.world_x // CHUNK_SIZE)
    player_chunk_z = int(player.world_z // CHUNK_SIZE)
    chunks_to_keep = set()
    for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
        for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            target_chunk_x = player_chunk_x + dx
            target_chunk_z = player_chunk_z + dz
            chunks_to_keep.add((target_chunk_x, target_chunk_z))
            if (target_chunk_x, target_chunk_z) not in LOADED_CHUNKS:
                LOADED_CHUNKS[(target_chunk_x, target_chunk_z)] = Chunk(target_chunk_x, target_chunk_z, WORLD_SEED)
    chunks_to_remove = []
    for chunk_key in LOADED_CHUNKS:
        if chunk_key not in chunks_to_keep:
            chunks_to_remove.append(chunk_key)
    for chunk_key in chunks_to_remove:
        del LOADED_CHUNKS[chunk_key]

def show_player_name_input(screen):
    screen.fill(BLACK)
    title_text = main_font.render("wzmc新游戏 - 输入玩家名称", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//4))
    screen.blit(title_text, title_rect)
    tip_text1 = small_font.render("请在命令行输入玩家名称（回车用默认名）", True, YELLOW)
    tip_rect1 = tip_text1.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30))
    default_name = f"Player_{int(time.time())}"
    tip_text2 = small_font.render(f"默认名称: {default_name}", True, WHITE)
    tip_rect2 = tip_text2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 20))
    screen.blit(tip_text1, tip_rect1)
    screen.blit(tip_text2, tip_rect2)
    confirm_btn = pygame.Rect(SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 + 80, 240, 50)
    pygame.draw.rect(screen, GREEN, confirm_btn)
    screen.blit(small_font.render("命令行输入后点击确认", True, BLACK), (confirm_btn.x + 10, confirm_btn.y + 12))
    pygame.display.flip()
    return confirm_btn, default_name

def show_resolution_select(screen):
    screen.fill(BLACK)
    title_text = main_font.render("选择分辨率", True, WHITE)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//8))
    screen.blit(title_text, title_rect)
    res1_btn = pygame.Rect(SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 - 50, 240, 50)
    res2_btn = pygame.Rect(SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 + 30, 240, 50)
    fullscreen_btn = pygame.Rect(SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 + 110, 240, 50)
    pygame.draw.rect(screen, GREEN, res1_btn)
    pygame.draw.rect(screen, GREEN, res2_btn)
    pygame.draw.rect(screen, YELLOW, fullscreen_btn)
    screen.blit(small_font.render("1. 800×600（默认）", True, BLACK), (res1_btn.x + 40, res1_btn.y + 12))
    screen.blit(small_font.render("2. 1024×768", True, BLACK), (res2_btn.x + 60, res2_btn.y + 12))
    screen.blit(small_font.render("3. 全屏模式（F11切换）", True, BLACK), (fullscreen_btn.x + 20, fullscreen_btn.y + 12))
    pygame.display.flip()
    return res1_btn, res2_btn, fullscreen_btn

def show_settings_screen(screen):
    while True:
        buttons = show_settings_menu(screen)
        (joystick_btn, buttons_btn, inventory_btn, sound_btn, music_btn, render_btn, fps_btn, back_btn) = buttons
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.USEREVENT + 1:
                play_random_ogg_music()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if joystick_btn.collidepoint(mx, my):
                    SETTINGS["virtual_joystick"] = not SETTINGS["virtual_joystick"]
                    save_settings()
                    load_settings()
                elif buttons_btn.collidepoint(mx, my):
                    SETTINGS["virtual_buttons"] = not SETTINGS["virtual_buttons"]
                    save_settings()
                    load_settings()
                elif inventory_btn.collidepoint(mx, my):
                    SETTINGS["keep_inventory_on_death"] = not SETTINGS["keep_inventory_on_death"]
                    save_settings()
                    load_settings()
                elif sound_btn.collidepoint(mx, my):
                    SETTINGS["sound_volume"] = (SETTINGS["sound_volume"] + 0.1) % 1.1
                    if SETTINGS["sound_volume"] > 1.0:
                        SETTINGS["sound_volume"] = 0.0
                    save_settings()
                    load_settings()
                elif music_btn.collidepoint(mx, my):
                    SETTINGS["music_volume"] = (SETTINGS["music_volume"] + 0.1) % 1.1
                    if SETTINGS["music_volume"] > 1.0:
                        SETTINGS["music_volume"] = 0.0
                    save_settings()
                    load_settings()
                elif render_btn.collidepoint(mx, my):
                    SETTINGS["render_distance"] = (SETTINGS["render_distance"] % 5) + 1
                    save_settings()
                    load_settings()
                elif fps_btn.collidepoint(mx, my):
                    SETTINGS["fps_limit"] = 60 if SETTINGS["fps_limit"] == 120 else 120
                    save_settings()
                    load_settings()
                elif back_btn.collidepoint(mx, my):
                    return

# ---------------------- 游戏主循环 ----------------------
def return_to_main_menu(screen):
    global LOADED_CHUNKS, WORLD_SEED, DROPS, MONSTERS, IS_SERVER, IS_CLIENT, PLAYERS
    LOADED_CHUNKS = OrderedDict()
    WORLD_SEED = random.randint(0, 2**32 - 1)
    DROPS = []
    MONSTERS = []
    PLAYERS.clear()
    if IS_CLIENT:
        net_manager.connected = False
        if hasattr(net_manager, 'socket') and net_manager.socket:
            net_manager.socket.close()
    if IS_SERVER:
        net_manager.stop_server()
    IS_SERVER = False
    IS_CLIENT = False

    scroll_offset = 0
    btn_spacing = 60
    visible_btn_count = 5
    game_mode = ""
    player = None
    fullscreen = False

    # 主菜单音乐
    pygame.mixer.music.stop()
    play_random_ogg_music(prefix="menu")

    while True:
        buttons = show_main_menu(screen)
        (sandbox_btn, wzmc_new_btn, wzmc_load_btn, multiplayer_btn, settings_btn, 
         controls_btn, about_btn, quit_btn) = buttons

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.USEREVENT + 1:
                play_random_ogg_music(prefix="menu")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if sandbox_btn.collidepoint(mx, my):
                    spawn_x, spawn_z, spawn_y = find_safe_spawn_location()
                    player = Player(x=spawn_x, y=spawn_z, name="Sandbox_Player")
                    player.z = spawn_y
                    load_chunks_around_player(player)
                    game_mode = "sandbox"
                    start_game_loop(screen, player, game_mode, fullscreen)
                elif wzmc_new_btn.collidepoint(mx, my):
                    confirm_btn, default_name = show_player_name_input(screen)
                    name_confirmed = False
                    while not name_confirmed:
                        for sub_event in pygame.event.get():
                            if sub_event.type == pygame.QUIT:
                                pygame.quit()
                                sys.exit()
                            elif sub_event.type == pygame.USEREVENT + 1:
                                play_random_ogg_music(prefix="menu")
                            elif sub_event.type == pygame.MOUSEBUTTONDOWN:
                                sub_mx, sub_my = sub_event.pos
                                if confirm_btn.collidepoint(sub_mx, sub_my):
                                    try:
                                        user_input = input("请输入玩家名称：").strip()
                                    except Exception:
                                        user_input = ""
                                    final_name = user_input if user_input else default_name
                                    spawn_x, spawn_z, spawn_y = find_safe_spawn_location()
                                    player = Player(x=spawn_x, y=spawn_z, name=final_name)
                                    player.z = spawn_y
                                    load_chunks_around_player(player)
                                    save_data = {
                                        "player": player.to_save_data(),
                                        "game_state": {"current_map": "平原", "time": "白天" if is_day else "黑夜", "completed_quests": []}
                                    }
                                    success, msg = create_json_file(get_save_path(final_name), save_data, LOADED_CHUNKS, WORLD_SEED)
                                    show_tip(screen, msg)
                                    game_mode = "wzmc"
                                    name_confirmed = True
                                    start_game_loop(screen, player, game_mode, fullscreen)
                elif wzmc_load_btn.collidepoint(mx, my):
                    saves = load_save_list()
                    if not saves:
                        show_tip(screen, "无wzmc存档，返回主菜单")
                        continue
                    max_scroll = max(0, (len(saves) - visible_btn_count) * (btn_spacing + 10))
                    selected_save = None
                    while selected_save is None:
                        btn_list, back_btn, delete_btn, import_btn, _ = show_save_list(screen, scroll_offset, btn_spacing, visible_btn_count)
                        for sub_event in pygame.event.get():
                            if sub_event.type == pygame.QUIT:
                                pygame.quit()
                                sys.exit()
                            elif sub_event.type == pygame.USEREVENT + 1:
                                play_random_ogg_music(prefix="menu")
                            elif sub_event.type == pygame.MOUSEBUTTONDOWN:
                                sub_mx, sub_my = sub_event.pos
                                if sub_event.button == 4:
                                    scroll_offset = max(0, scroll_offset - (btn_spacing + 10))
                                elif sub_event.button == 5:
                                    scroll_offset = min(max_scroll, scroll_offset + (btn_spacing + 10))
                                else:
                                    for btn, save_name in btn_list:
                                        if btn.collidepoint(sub_mx, sub_my):
                                            selected_save = save_name
                                            break
                                    if back_btn.collidepoint(sub_mx, sub_my):
                                        selected_save = "back"
                                        break
                                    if delete_btn.collidepoint(sub_mx, sub_my) and selected_save:
                                        try:
                                            confirm = input(f"确定删除「{selected_save}」？输入D确认：").strip().upper()
                                        except Exception:
                                            confirm = ""
                                        if confirm == "D":
                                            try:
                                                os.remove(get_save_path(selected_save))
                                                show_tip(screen, f"删除成功：{selected_save}")
                                                saves = load_save_list()
                                                max_scroll = max(0, (len(saves) - visible_btn_count) * (btn_spacing + 10))
                                                scroll_offset = 0
                                            except Exception as e:
                                                show_tip(screen, f"删除失败: {e}")
                                        else:
                                            show_tip(screen, "取消删除")
                                        selected_save = None
                    if selected_save not in ("back", None):
                        success, msg, player_data, loaded_chunks, world_seed = load_json_file(get_save_path(selected_save))
                        if success:
                            LOADED_CHUNKS = loaded_chunks
                            WORLD_SEED = world_seed
                            player = Player.from_save_data(player_data)
                            game_mode = "wzmc"
                            show_tip(screen, "加载成功")
                            start_game_loop(screen, player, game_mode, fullscreen)
                        else:
                            show_tip(screen, msg)
                elif multiplayer_btn.collidepoint(mx, my):
                    host_btn, join_btn, back_btn = show_multiplayer_menu(screen)
                    multiplayer_selected = False
                    while not multiplayer_selected:
                        for sub_event in pygame.event.get():
                            if sub_event.type == pygame.QUIT:
                                pygame.quit()
                                sys.exit()
                            elif sub_event.type == pygame.USEREVENT + 1:
                                play_random_ogg_music(prefix="menu")
                            elif sub_event.type == pygame.MOUSEBUTTONDOWN:
                                sub_mx, sub_my = sub_event.pos
                                if host_btn.collidepoint(sub_mx, sub_my):
                                    if net_manager.start_server(SERVER_HOST, SERVER_PORT):
                                        IS_SERVER = True
                                        show_tip(screen, "服务器已创建，查看控制台获取连接信息")
                                        spawn_x, spawn_z, spawn_y = find_safe_spawn_location()
                                        player = Player(x=spawn_x, y=spawn_z, name=f"Host_{int(time.time())}")
                                        player.z = spawn_y
                                        load_chunks_around_player(player)
                                        game_mode = "multiplayer"
                                        multiplayer_selected = True
                                        start_game_loop(screen, player, game_mode, fullscreen)
                                    else:
                                        show_tip(screen, "创建服务器失败")
                                elif join_btn.collidepoint(sub_mx, sub_my):
                                    ip_input_rect, connect_btn, back_btn_join, default_ip = show_join_server_menu(screen)
                                    join_selected = False
                                    while not join_selected:
                                        for join_event in pygame.event.get():
                                            if join_event.type == pygame.QUIT:
                                                pygame.quit()
                                                sys.exit()
                                            elif join_event.type == pygame.USEREVENT + 1:
                                                play_random_ogg_music(prefix="menu")
                                            elif join_event.type == pygame.MOUSEBUTTONDOWN:
                                                join_mx, join_my = join_event.pos
                                                if connect_btn.collidepoint(join_mx, join_my):
                                                    try:
                                                        host, port_str = default_ip.split(":")
                                                        port = int(port_str)
                                                        if net_manager.connect_to_server(host, port):
                                                            IS_CLIENT = True
                                                            show_tip(screen, "已连接到服务器")
                                                            spawn_x, spawn_z, spawn_y = find_safe_spawn_location()
                                                            player = Player(x=spawn_x, y=spawn_z, name=f"Client_{int(time.time())}")
                                                            player.z = spawn_y
                                                            load_chunks_around_player(player)
                                                            game_mode = "multiplayer"
                                                            join_selected = True
                                                            multiplayer_selected = True
                                                            start_game_loop(screen, player, game_mode, fullscreen)
                                                        else:
                                                            show_tip(screen, "连接服务器失败")
                                                    except Exception as e:
                                                        show_tip(screen, f"地址格式错误: {e}")
                                                elif back_btn_join.collidepoint(join_mx, join_my):
                                                    join_selected = True
                                elif back_btn.collidepoint(sub_mx, sub_my):
                                    multiplayer_selected = True
                elif settings_btn.collidepoint(mx, my):
                    show_settings_screen(screen)
                elif controls_btn.collidepoint(mx, my):
                    show_controls_info(screen)
                elif about_btn.collidepoint(mx, my):
                    show_about_screen(screen)
                elif quit_btn.collidepoint(mx, my):
                    pygame.quit()
                    sys.exit(0)

def start_game_loop(screen, player, game_mode, fullscreen):
    global LOADED_CHUNKS, WORLD_SEED, DROPS, MONSTERS, is_day, PLAYERS
    selected_block = 2
    current_dig_block = None
    current_dig_progress = 0
    clock = pygame.time.Clock()
    DAY_DURATION = 5 * 60 * FPS
    current_time = 0
    monster_spawn_timer = 0
    monster_spawn_interval = FPS * 15

    if USE_DOUBLE_BUFFER:
        buffer_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # 游戏内音乐（所有ogg）
    pygame.mixer.music.stop()
    play_random_ogg_music()

    last_send_time = 0
    SEND_INTERVAL = 0.1

    while True:
        delta_time = clock.tick(FPS) / 1000.0

        if player.hp <= 0:
            result = show_death_screen(screen, player, game_mode, fullscreen)
            if result == "respawn":
                keep_inventory = SETTINGS["keep_inventory_on_death"]
                player = reset_player(player, keep_inventory)
                load_chunks_around_player(player)
                continue
            elif result == "menu":
                return_to_main_menu(screen)
                return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return_to_main_menu(screen)
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    tool_id = int(event.unicode) - 1
                    if 0 <= tool_id < 3 and player.tools.get(tool_id, 0) > 0:
                        player.current_tool = tool_id
                elif event.key in (pygame.K_UP, pygame.K_DOWN):
                    selected_block = (selected_block - 1) % len(BLOCK_TYPES) if event.key == pygame.K_UP else (selected_block + 1) % len(BLOCK_TYPES)
                elif event.key == pygame.K_i:
                    player.bag_open = not player.bag_open
                    player.workbench_open = False
                elif event.key == pygame.K_F5:
                    save_data = {"player": player.to_save_data(), "game_state": {"current_map": "平原", "time": "白天" if is_day else "黑夜", "completed_quests": []}}
                    success, msg = create_json_file(get_save_path(player.name), save_data, LOADED_CHUNKS, WORLD_SEED)
                    show_tip(screen, msg)
            elif event.type == pygame.USEREVENT + 1:
                play_random_ogg_music()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if handle_virtual_controls(event, player, screen):
                    continue
                if event.button == 1:  # 左键
                    if player.workbench_open:
                        if player.handle_workbench_click(event.pos):
                            continue
                    mouse_pos = pygame.mouse.get_pos()
                    target_block = get_mouse_block(mouse_pos, player)
                    block_x, block_y, block_z = target_block
                    chunk_x, chunk_z = int(block_x//CHUNK_SIZE), int(block_z//CHUNK_SIZE)
                    if (chunk_x, chunk_z) in LOADED_CHUNKS:
                        chunk = LOADED_CHUNKS[(chunk_x, chunk_z)]
                        in_x, in_z = int(block_x % CHUNK_SIZE), int(block_z % CHUNK_SIZE)
                        if 0 <= in_x < CHUNK_SIZE and 0 <= block_y < Y_MAX and 0 <= in_z < CHUNK_SIZE:
                            block_id = chunk.blocks[in_x][block_y][in_z]
                            if block_id != 0 and BLOCK_TYPES[block_id]["breakable"]:
                                if IS_CLIENT or IS_SERVER:
                                    dig_msg = {
                                        'type': 'block_update',
                                        'position': [block_x, block_y, block_z],
                                        'block_id': 0,
                                        'player_id': player.name
                                    }
                                    net_manager.send_message(dig_msg)
                                chunk.blocks[in_x][block_y][in_z] = 0
                                play_sound("dig")
                                drop_id = BLOCK_TYPES[block_id]["drop"]
                                if drop_id != 0:
                                    DROPS.append(DropItem(block_x, block_z, drop_id))
                elif event.button == 3:  # 右键
                    if player.workbench_open:
                        if player.handle_workbench_click(event.pos):
                            continue
                    if not player.bag_open and not player.workbench_open:
                        success, message = player.use_item(player.bag_selected)
                        if success:
                            play_sound("eat")
                            show_quick_message(screen, message, 1000)
                            continue
                    if player.inventory.get(selected_block, 0) > 0:
                        mouse_pos = pygame.mouse.get_pos()
                        target_block = get_mouse_block(mouse_pos, player)
                        block_x, block_y, block_z = target_block
                        chunk_x, chunk_z = int(block_x//CHUNK_SIZE), int(block_z//CHUNK_SIZE)
                        if (chunk_x, chunk_z) in LOADED_CHUNKS:
                            chunk = LOADED_CHUNKS[(chunk_x, chunk_z)]
                            in_x, in_z = int(block_x % CHUNK_SIZE), int(block_z % CHUNK_SIZE)
                            if 0 <= in_x < CHUNK_SIZE and 0 <= block_y < Y_MAX and 0 <= in_z < CHUNK_SIZE:
                                if chunk.blocks[in_x][block_y][in_z] == 0:
                                    if IS_CLIENT or IS_SERVER:
                                        place_msg = {
                                            'type': 'block_update',
                                            'position': [block_x, block_y, block_z],
                                            'block_id': selected_block,
                                            'player_id': player.name
                                        }
                                        net_manager.send_message(place_msg)
                                    chunk.blocks[in_x][block_y][in_z] = selected_block
                                    player.inventory[selected_block] -= 1
                                    play_sound("place")
            elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                handle_virtual_controls(event, player, screen)

        current_time = (current_time + 1) % DAY_DURATION
        if current_time == 0:
            is_day = not is_day

        if not is_day:
            monster_spawn_timer = (monster_spawn_timer + 1) % monster_spawn_interval
            if monster_spawn_timer == 0 and len(MONSTERS) < 5:
                spawn_x = player.world_x + random.randint(-10, 10)
                spawn_z = player.world_z + random.randint(-10, 10)
                MONSTERS.append(Monster(spawn_x, spawn_z))

        load_chunks_around_player(player)
        player.update(LOADED_CHUNKS)

        limited_monsters = limit_updates_per_frame(MONSTERS)
        new_monsters = []
        for m in limited_monsters:
            if m.update(player, LOADED_CHUNKS):
                new_monsters.append(m)
        MONSTERS = new_monsters

        limited_drops = limit_updates_per_frame(DROPS)
        new_drops = []
        for d in limited_drops:
            if d.update(LOADED_CHUNKS):
                new_drops.append(d)
        DROPS = new_drops

        # 网络发送玩家更新
        if (IS_CLIENT or IS_SERVER) and time.time() - last_send_time > SEND_INTERVAL:
            last_send_time = time.time()
            move_msg = {
                'type': 'player_move',
                'player_id': player.name,
                'position': [player.world_x, player.world_z, player.z]
            }
            net_manager.send_message(move_msg)

        target_surface = buffer_surface if USE_DOUBLE_BUFFER else screen
        target_surface.fill((255,255,255) if is_day else (10, 10, 30))

        draw_infinite_map(target_surface, LOADED_CHUNKS, player)

        # 绘制其他玩家
        for pid, pos in PLAYERS.items():
            if pid != player.name:
                screen_x = int((pos[0] - player.world_x) * BLOCK_SIZE + SCREEN_WIDTH // 2)
                screen_y = int((pos[1] - player.world_z) * BLOCK_SIZE + SCREEN_HEIGHT // 2)
                if (screen_x < -BLOCK_SIZE or screen_x > SCREEN_WIDTH or 
                    screen_y < -BLOCK_SIZE or screen_y > SCREEN_HEIGHT):
                    continue
                other_player_rect = pygame.Rect(screen_x, screen_y, BLOCK_SIZE//2, BLOCK_SIZE)
                pygame.draw.rect(target_surface, PURPLE, other_player_rect)
                name_text = small_font.render(pid, True, WHITE)
                target_surface.blit(name_text, (screen_x - 10, screen_y - 20))

        for drop in DROPS:
            drop.draw(target_surface, player)
        for monster in MONSTERS:
            monster.draw(target_surface, player)

        player.draw(target_surface)
        draw_virtual_controls(target_surface)

        selected_surf = small_font.render(f"选中方块：{BLOCK_TYPES[selected_block]['name']}", True, WHITE)
        target_surface.blit(selected_surf, (10, 30))

        hp_bar_x = SCREEN_WIDTH - 110
        hp_bar_y = 10
        pygame.draw.rect(target_surface, BLACK, (hp_bar_x, hp_bar_y, 100, 8))
        hp_fill = int(player.hp)
        pygame.draw.rect(target_surface, RED, (hp_bar_x, hp_bar_y, hp_fill, 8))
        hp_text = small_font.render("HP", True, WHITE)
        target_surface.blit(hp_text, (hp_bar_x - 30, hp_bar_y - 2))

        if player.hp <= 20:
            warning_text = small_font.render("警告：生命值过低!", True, RED)
            target_surface.blit(warning_text, (SCREEN_WIDTH//2 - warning_text.get_width()//2, 40))

        mode_text = small_font.render(f"模式: {game_mode}", True, WHITE)
        target_surface.blit(mode_text, (10, 10))

        if game_mode == "multiplayer":
            player_count = small_font.render(f"玩家: {len(PLAYERS) + 1}", True, WHITE)
            target_surface.blit(player_count, (SCREEN_WIDTH - 150, 30))

        if USE_DOUBLE_BUFFER:
            screen.blit(buffer_surface, (0, 0))

        pygame.display.flip()

# ---------------------- 主函数 ----------------------
def main():
    global menu_bg, main_font, small_font, IS_MOBILE, game_logger

    try:
        # 移动设备检测
        try:
            import android
            import android.mixer
            IS_MOBILE = True
        except ImportError:
            IS_MOBILE = False

        pygame.init()
        pygame.mixer.init()

        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("沙盒游戏 正式版 1.11.1")

        # 加载字体
        try:
            main_font = pygame.font.Font(FONT_PATH, 48)
            small_font = pygame.font.Font(FONT_PATH, 24)
        except Exception:
            main_font = pygame.font.Font(None, 48)
            small_font = pygame.font.Font(None, 24)

        # 初始化日志
        try:
            game_logger = GameLogger(LOG_DIR, enabled=True)
            game_logger.info("日誌系統初始化成功")
        except Exception as e:
            print(f"日志系统初始化失败: {e}")
            game_logger = None

        # 加载设置
        load_settings()

        # 加载背景图
        try:
            if os.path.exists(BG_PHOTO_PATH):
                menu_bg = pygame.image.load(BG_PHOTO_PATH).convert()
                menu_bg = pygame.transform.scale(menu_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
                log(f"背景图加载成功：{BG_PHOTO_PATH}")
            else:
                menu_bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                menu_bg.fill(BROWN)
                log(f"背景图不存在，使用棕色背景：{BG_PHOTO_PATH}")
        except Exception as e:
            menu_bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            menu_bg.fill(BROWN)
            log(f"背景图加载失败：{str(e)}，使用棕色背景")

        # 初始化音效与音乐
        init_sounds()
        play_random_ogg_music(prefix="menu")

        print("Copyright (c) LongTeam Studio, all rights reserved.")
        print("如有发现盗版，必会追究责任")
        print("QQ群:131293550，只是玩家交流群")

        # 进入主菜单
        return_to_main_menu(screen)

    except KeyboardInterrupt:
        if game_logger:
            game_logger.info("用户通过键盘中断退出游戏")
        pygame.quit()
        if game_logger:
            game_logger.close()
        sys.exit(0)
    except Exception as e:
        if game_logger:
            game_logger.fatal("游戏运行时发生致命错误")
            game_logger.exception("错误详情", e)
            game_logger.exit("游戏异常退出", exit_code=-1)
        else:
            print(f"[FATAL] 游戏运行时发生致命错误: {e}")
            traceback.print_exc()
        pygame.quit()
        sys.exit(-1)


if __name__ == "__main__":
    main()
