"""玩家实体 + 摇杆移动。字体/网络状态通过 import main 访问，FPS 来自 utils。"""
import math
import time
import pygame
import main
import audio
from config import *
from utils import *

class Player:
    def __init__(self, x, y, name="Player"):
        self.world_x = x
        self.world_z = y
        self.x = SCREEN_WIDTH // 2 - (BLOCK_SIZE//2//2)
        self.y = SCREEN_HEIGHT // 2 - BLOCK_SIZE//2
        self.z = 0
        self.width = BLOCK_SIZE // 2
        self.height = BLOCK_SIZE
        self.speed = 5
        self.jump_power = 12
        self.velocity_y = 0
        self.on_ground = False
        self.name = name
        self.hp = 100
        self.hunger = 100
        self.level = 1
        self.current_tool = 0
        self.tools = {0: 0, 1: 0, 2: 0, 3: 0}
        self.inventory = {1: 0, 2: 0, 3: 0, 5: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        self.last_z = self.z
        self.hunger_timer = 0
        self.last_update_time = time.time()
        self.last_network_update = 0
        self.bag_open = False
        self.workbench_open = False
        self.bag_selected = 2
        self.bag_spacing = 10
        self.crafting_recipes = []
        self.workbench_close_btn = None
        self.starvation_timer = 0
        self.regen_timer = 0
        self.initialized = False

    def update(self, loaded_chunks):
        current_time = time.time()
        delta_time = min(0.1, current_time - self.last_update_time)
        self.last_update_time = current_time

        # 出生点安全初始化
        if not self.initialized:
            self.ensure_safe_position(loaded_chunks)
            self.initialized = True

        self.velocity_y += 20 * delta_time
        self.velocity_y = min(self.velocity_y, 20)
        self.y += self.velocity_y

        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.on_ground = False

        player_world_y = int(self.world_z)

        for (chunk_x, chunk_z), chunk in loaded_chunks.items():
            chunk_screen_x = chunk_x * CHUNK_SIZE * BLOCK_SIZE - self.world_x * BLOCK_SIZE + SCREEN_WIDTH//2
            chunk_screen_z = chunk_z * CHUNK_SIZE * BLOCK_SIZE - self.world_z * BLOCK_SIZE + SCREEN_HEIGHT//2

            for x in range(max(0, int(self.world_x) - 1), min(CHUNK_SIZE, int(self.world_x) + 2)):
                for z_range in range(max(0, int(self.world_z) - 1), min(CHUNK_SIZE, int(self.world_z) + 2)):
                    block_y = player_world_y + 1
                    if 0 <= block_y < Y_MAX:
                        block_id = chunk.blocks[x][block_y][z_range]
                        if block_id != 0 and BLOCK_TYPES[block_id]["breakable"]:
                            block_screen_x = chunk_screen_x + x * BLOCK_SIZE
                            block_screen_y = chunk_screen_z + block_y * BLOCK_SIZE
                            block_rect = pygame.Rect(block_screen_x, block_screen_y, BLOCK_SIZE, BLOCK_SIZE)
                            if player_rect.colliderect(block_rect):
                                if self.velocity_y > 0:
                                    self.y = block_screen_y - self.height
                                    self.velocity_y = 0
                                    self.on_ground = True
                                    self.z = block_y
                                elif self.velocity_y < 0:
                                    self.y = block_screen_y + BLOCK_SIZE
                                    self.velocity_y = 0

        keys = pygame.key.get_pressed()
        move_speed = self.speed * delta_time * 60

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.world_x -= move_speed / BLOCK_SIZE
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.world_x += move_speed / BLOCK_SIZE
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.world_z -= move_speed / BLOCK_SIZE
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.world_z += move_speed / BLOCK_SIZE

        update_player_movement_from_joystick(self, delta_time)

        if (keys[pygame.K_SPACE]) and self.on_ground:
            self.velocity_y = -self.jump_power
            self.on_ground = False

        # 饥饿系统
        self.update_hunger(delta_time)

        # 网络同步
        if (IS_CLIENT or IS_SERVER) and current_time - self.last_network_update > 0.1:
            move_msg = {
                'type': 'player_move',
                'player_id': self.name,
                'position': [self.world_x, self.world_z, self.z]
            }
            main.net_manager.send_message(move_msg)
            self.last_network_update = current_time

        fall_distance = self.last_z - (player_world_y if self.on_ground else self.z)
        if self.on_ground and fall_distance >= 5:
            damage = min(20, int(fall_distance - 4) * 2)
            self.hp = max(0, self.hp - damage)
            audio.play_sound("hurt")
            log(f"玩家{self.name}高处掉落{fall_distance:.1f}格，HP:{self.hp}")

        self.last_z = player_world_y if self.on_ground else self.z
        self.pick_up_drop()

    def update_hunger(self, delta_time):
        """更新饥饿值"""
        self.hunger_timer += delta_time * FPS
        if self.hunger_timer >= FPS * 5:
            self.hunger = max(0, self.hunger - 1)
            self.hunger_timer = 0

        if self.hunger <= 0 and self.hp > 0:
            self.starvation_timer += delta_time * FPS
            if self.starvation_timer >= FPS * 10:
                self.hp = max(0, self.hp - 1)
                self.starvation_timer = 0
                if self.hp <= 0:
                    log(f"玩家{self.name}因饥饿死亡")
        else:
            self.starvation_timer = 0

        if self.hunger >= 80 and self.hp < 100 and self.on_ground:
            if getattr(self, 'regen_timer', 0) >= FPS * 3:
                self.hp = min(100, self.hp + 1)
                self.regen_timer = 0
            else:
                self.regen_timer += delta_time * FPS

    def use_item(self, item_id):
        if item_id == 9:  # 肉
            if self.inventory.get(9, 0) > 0:
                self.inventory[9] -= 1
                hunger_restore = 30
                self.hunger = min(100, self.hunger + hunger_restore)
                log(f"使用肉，饥饿值恢复{hunger_restore}点，当前:{self.hunger}")
                return True, f"使用肉，恢复{hunger_restore}点饥饿值"
        return False, "无法使用此物品"

    def interact_with_workbench(self):
        if not self.workbench_open:
            self.workbench_open = True
            self.bag_open = False
            self.update_crafting_recipes()
            return True
        return False

    def update_crafting_recipes(self):
        self.crafting_recipes = []
        for recipe_id, recipe in CRAFT_RECIPES.items():
            can_craft = True
            if self.workbench_open and recipe["crafting_station"] == 0:
                continue
            for need_id, need_count in recipe["need"].items():
                if self.inventory.get(need_id, 0) < need_count:
                    can_craft = False
                    break
            if can_craft:
                self.crafting_recipes.append(recipe_id)

    def draw_workbench(self, screen):
        workbench_rect = pygame.Rect(SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 200, 400, 400)
        pygame.draw.rect(screen, (80, 80, 80), workbench_rect)
        pygame.draw.rect(screen, WHITE, workbench_rect, 2)
        title_text = main.main_font.render("工作台", True, WHITE)
        screen.blit(title_text, (SCREEN_WIDTH//2 - 50, SCREEN_HEIGHT//2 - 190))

        if not self.crafting_recipes:
            no_recipes_text = main.small_font.render("没有可合成的配方", True, WHITE)
            screen.blit(no_recipes_text, (SCREEN_WIDTH//2 - 80, SCREEN_HEIGHT//2 - 50))
        else:
            for i, recipe_id in enumerate(self.crafting_recipes):
                recipe = CRAFT_RECIPES[recipe_id]
                y_pos = SCREEN_HEIGHT//2 - 150 + i * 80
                recipe_rect = pygame.Rect(SCREEN_WIDTH//2 - 180, y_pos, 360, 70)
                pygame.draw.rect(screen, (100, 100, 100), recipe_rect)
                pygame.draw.rect(screen, WHITE, recipe_rect, 1)
                name_text = main.small_font.render(recipe["name"], True, WHITE)
                screen.blit(name_text, (SCREEN_WIDTH//2 - 170, y_pos + 10))
                materials_text = "所需材料: "
                for need_id, need_count in recipe["need"].items():
                    materials_text += f"{BLOCK_TYPES[need_id]['name']}×{need_count} "
                mat_text = main.small_font.render(materials_text, True, YELLOW)
                screen.blit(mat_text, (SCREEN_WIDTH//2 - 170, y_pos + 35))
                craft_btn = pygame.Rect(SCREEN_WIDTH//2 + 100, y_pos + 40, 60, 25)
                pygame.draw.rect(screen, GREEN, craft_btn)
                craft_text = main.small_font.render("合成", True, BLACK)
                screen.blit(craft_text, (craft_btn.x + 15, craft_btn.y + 5))
                recipe["button_rect"] = craft_btn

        close_btn = pygame.Rect(SCREEN_WIDTH//2 - 50, SCREEN_HEIGHT//2 + 150, 100, 30)
        pygame.draw.rect(screen, RED, close_btn)
        close_text = main.small_font.render("关闭", True, BLACK)
        screen.blit(close_text, (close_btn.x + 30, close_btn.y + 8))
        self.workbench_close_btn = close_btn

    def handle_workbench_click(self, pos):
        if hasattr(self, 'workbench_close_btn') and self.workbench_close_btn and self.workbench_close_btn.collidepoint(pos):
            self.workbench_open = False
            return True
        for recipe_id in self.crafting_recipes:
            recipe = CRAFT_RECIPES[recipe_id]
            if "button_rect" in recipe and recipe["button_rect"].collidepoint(pos):
                success, message = self.craft_item(recipe_id)
                if success:
                    self.update_crafting_recipes()
                log(message)
                return True
        return False

    def craft_item(self, recipe_id):
        recipe = CRAFT_RECIPES.get(recipe_id)
        if not recipe:
            return False, "无此合成配方"
        for need_id, need_count in recipe["need"].items():
            if self.inventory.get(need_id, 0) < need_count:
                return False, f"材料不足：{BLOCK_TYPES[need_id]['name']}需{need_count}个"
        for need_id, need_count in recipe["need"].items():
            self.inventory[need_id] -= need_count
        output_id = recipe_id
        if recipe_id in TOOL_TYPES:
            self.tools[recipe_id] = self.tools.get(recipe_id, 0) + recipe["output"]
            self.current_tool = recipe_id
        else:
            self.inventory[output_id] = self.inventory.get(output_id, 0) + recipe["output"]
        log(f"玩家{self.name}合成了{recipe['name']}")
        return True, f"合成成功：{recipe['name']}"

    def ensure_safe_position(self, loaded_chunks):
        player_chunk_x = int(self.world_x // CHUNK_SIZE)
        player_chunk_z = int(self.world_z // CHUNK_SIZE)
        if (player_chunk_x, player_chunk_z) in loaded_chunks:
            chunk = loaded_chunks[(player_chunk_x, player_chunk_z)]
            in_x = int(self.world_x % CHUNK_SIZE)
            in_z = int(self.world_z % CHUNK_SIZE)
            safe_y = None
            for y in range(Y_MAX-1, -1, -1):
                if chunk.blocks[in_x][y][in_z] != 0:
                    safe_y = y + 1
                    break
            if safe_y is not None and safe_y < Y_MAX:
                self.world_z = player_chunk_z * CHUNK_SIZE + in_z
                self.z = safe_y
                log(f"玩家{self.name}调整到安全高度: {safe_y}")

    def pick_up_drop(self):
        new_drops = []
        for drop in main.DROPS:
            distance = math.hypot(self.world_x - drop.world_x, self.world_z - drop.world_z)
            if distance <= 1.5:
                block_id = drop.block_id
                max_stack = 16
                current = self.inventory.get(block_id, 0)
                if current < max_stack:
                    take = min(drop.count, max_stack - current)
                    self.inventory[block_id] += take
                    drop.count -= take
                    if drop.count > 0:
                        new_drops.append(drop)
                    else:
                        log(f"玩家{self.name}拾取了{BLOCK_TYPES[block_id]['name']}x{take}")
                else:
                    new_drops.append(drop)
            else:
                new_drops.append(drop)
        main.DROPS = new_drops

    def draw(self, screen):
        pygame.draw.rect(screen, YELLOW, (self.x, self.y, self.width, self.height))
        # 调试信息
        debug_text = main.small_font.render(f"Pos: ({self.world_x:.1f}, {self.z:.1f}) Ground: {self.on_ground}", True, WHITE)
        screen.blit(debug_text, (10, 110))
        # 饥饿值条
        hunger_bar_x = 10
        hunger_bar_y = 60
        hunger_width = 100
        pygame.draw.rect(screen, (50, 50, 50), (hunger_bar_x, hunger_bar_y, hunger_width, 10))
        if self.hunger > 50:
            hunger_color = GREEN
        elif self.hunger > 20:
            hunger_color = YELLOW
        else:
            hunger_color = RED
        fill_width = int(self.hunger / 100 * hunger_width)
        pygame.draw.rect(screen, hunger_color, (hunger_bar_x, hunger_bar_y, fill_width, 10))
        hunger_text = main.small_font.render(f"饥饿: {self.hunger}", True, WHITE)
        screen.blit(hunger_text, (hunger_bar_x, hunger_bar_y - 20))
        if self.hunger <= 20:
            warning_text = main.small_font.render("饥饿警告!", True, RED)
            screen.blit(warning_text, (hunger_bar_x + 110, hunger_bar_y - 5))
        tool_text = main.small_font.render(f"工具：{TOOL_TYPES[self.current_tool]['name']}", True, WHITE)
        screen.blit(tool_text, (10, 85))
        fps_text = main.small_font.render(f"FPS: {get_current_fps()}", True, WHITE)
        screen.blit(fps_text, (SCREEN_WIDTH - 100, 10))
        if self.bag_open:
            self.draw_bag(screen)
        if self.workbench_open:
            self.draw_workbench(screen)

    def draw_bag(self, screen):
        bag_rect = pygame.Rect(SCREEN_WIDTH//2 - 160, SCREEN_HEIGHT//2 - 130, 320, 260)
        pygame.draw.rect(screen, (50, 50, 50), bag_rect)
        pygame.draw.rect(screen, WHITE, bag_rect, 2)
        bag_title = main.main_font.render("物品栏", True, WHITE)
        screen.blit(bag_title, (SCREEN_WIDTH//2 - 30, SCREEN_HEIGHT//2 - 115))
        block_ids = [1, 2, 3, 5, 7, 8, 9, 10, 11, 13, 15]
        for i, block_id in enumerate(block_ids):
            row = i // 5
            col = i % 5
            grid_x = SCREEN_WIDTH//2 - 140 + col * (50 + self.bag_spacing)
            grid_y = SCREEN_HEIGHT//2 - 90 + row * (60 + self.bag_spacing)
            grid_rect = pygame.Rect(grid_x, grid_y, 50, 50)
            if block_id == self.bag_selected:
                pygame.draw.rect(screen, YELLOW, grid_rect, 3)
            else:
                pygame.draw.rect(screen, WHITE, grid_rect, 1)
            block_rect = pygame.Rect(grid_x + 10, grid_y + 10, 30, 30)
            pygame.draw.rect(screen, BLOCK_TYPES[block_id]["color"], block_rect)
            count = self.inventory.get(block_id, 0)
            count_text = main.small_font.render(str(count), True, WHITE)
            screen.blit(count_text, (grid_x + 35, grid_y + 35))
            name_text = main.small_font.render(BLOCK_TYPES[block_id]["name"], True, WHITE)
            screen.blit(name_text, (grid_x + 5, grid_y + 65))
        craft_btn = pygame.Rect(SCREEN_WIDTH//2 - 80, SCREEN_HEIGHT//2 + 70, 160, 30)
        pygame.draw.rect(screen, GREEN, craft_btn)
        craft_text = main.small_font.render("合成木镐（3木头+2泥土）", True, BLACK)
        screen.blit(craft_text, (craft_btn.x + 5, craft_btn.y + 12))

    def to_save_data(self):
        return {
            "name": self.name,
            "hp": self.hp,
            "hunger": self.hunger,
            "level": self.level,
            "current_tool": self.current_tool,
            "tools": self.tools,
            "inventory": self.inventory,
            "position": {"world_x": self.world_x, "world_z": self.world_z, "z": self.z}
        }

    @staticmethod
    def from_save_data(data):
        player = Player(x=data["position"]["world_x"], y=data["position"]["world_z"], name=data["name"])
        player.hp = data["hp"]
        player.hunger = data.get("hunger", 100)
        player.level = data["level"]
        player.current_tool = data.get("current_tool", 0)
        player.tools = data.get("tools", {0: 0, 1: 0, 2: 0, 3: 0})
        player.inventory = data.get("inventory", {1: 0, 2: 0, 3: 0, 5: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0})
        player.world_x = data["position"]["world_x"]
        player.world_z = data["position"]["world_z"]
        player.z = data["position"]["z"]
        player.last_z = player.z
        return player


def update_player_movement_from_joystick(player, delta_time):
    if not main.joystick_active or not VIRTUAL_JOYSTICK_ENABLED:
        return
    move_speed = player.speed * delta_time * 60
    dead_zone = 0.2
    if abs(main.joystick_vector[0]) > dead_zone or abs(main.joystick_vector[1]) > dead_zone:
        player.world_x += main.joystick_vector[0] * move_speed / BLOCK_SIZE
        player.world_z += main.joystick_vector[1] * move_speed / BLOCK_SIZE

