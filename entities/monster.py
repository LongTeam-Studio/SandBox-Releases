"""怪物实体。DROPS/is_day 通过 import main 运行时访问。"""
import math
import random
import time
import pygame
import main
import audio
from config import *
from utils import log
from entities.dropitem import DropItem

class Monster:
    def __init__(self, world_x, world_z):
        self.world_x = world_x
        self.world_z = world_z
        self.width = BLOCK_SIZE // 2
        self.height = BLOCK_SIZE
        self.hp = 50
        self.speed = 2
        self.attack_cooldown = 0
        self.attack_range = 1.5
        self.attack_damage = 5
        self.last_update_time = time.time()

    def update(self, player, loaded_chunks):
        current_time = time.time()
        delta_time = min(0.1, current_time - self.last_update_time)
        self.last_update_time = current_time
        if main.is_day:
            return False
        dx = player.world_x - self.world_x
        dz = player.world_z - self.world_z
        distance = math.hypot(dx, dz)
        if distance > 15:
            return True
        speed_multiplier = 1.0
        if distance < 3:
            speed_multiplier = 1.5
        elif distance > 10:
            speed_multiplier = 0.7
        move_speed = self.speed * speed_multiplier * delta_time * 60
        if distance > self.attack_range:
            self.world_x += (dx / distance) * move_speed / BLOCK_SIZE
            self.world_z += (dz / distance) * move_speed / BLOCK_SIZE
        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        if distance <= self.attack_range and self.attack_cooldown == 0:
            player.hp = max(0, player.hp - self.attack_damage)
            audio.play_sound("hurt")
            self.attack_cooldown = FPS * 2
            log(f"玩家{player.name}被僵尸攻击，HP:{player.hp}")
        chunk_x = int(self.world_x // CHUNK_SIZE)
        chunk_z = int(self.world_z // CHUNK_SIZE)
        if (chunk_x, chunk_z) in loaded_chunks:
            chunk = loaded_chunks[(chunk_x, chunk_z)]
            in_chunk_x = int(self.world_x % CHUNK_SIZE)
            in_chunk_y = min(Y_MAX-1, max(0, int(self.world_z)))
            in_chunk_z = int(self.world_z % CHUNK_SIZE)
            if (0 <= in_chunk_x < CHUNK_SIZE and 0 <= in_chunk_y < Y_MAX and 
                0 <= in_chunk_z < CHUNK_SIZE and chunk.blocks[in_chunk_x][in_chunk_y][in_chunk_z] != 0):
                self.world_x -= (dx / distance) * 0.1 if distance != 0 else 0
                self.world_z -= (dz / distance) * 0.1 if distance != 0 else 0
        if self.hp <= 0:
            if random.random() < 0.5:
                main.DROPS.append(DropItem(self.world_x, self.world_z, 9, 1))
            log(f"僵尸死亡，位置:({int(self.world_x)},{int(self.world_z)})")
            return False
        return True

    def draw(self, screen, player):
        screen_x = int((self.world_x - player.world_x) * BLOCK_SIZE + SCREEN_WIDTH // 2)
        screen_y = int((self.world_z - player.world_z) * BLOCK_SIZE + SCREEN_HEIGHT // 2)
        if (screen_x < -self.width or screen_x > SCREEN_WIDTH or 
            screen_y < -self.height or screen_y > SCREEN_HEIGHT):
            return
        monster_rect = pygame.Rect(screen_x, screen_y, self.width, self.height)
        pygame.draw.rect(screen, RED, monster_rect)
        hp_bar_x = screen_x
        hp_bar_y = screen_y - 10
        pygame.draw.rect(screen, BLACK, (hp_bar_x, hp_bar_y, self.width, 5))
        fill_width = int(self.hp / 50 * self.width)
        pygame.draw.rect(screen, RED, (hp_bar_x, hp_bar_y, fill_width, 5))

