"""掉落物实体。small_font 通过 import main 运行时访问。"""
import time
import pygame
import main
from config import *

class DropItem:
    def __init__(self, x, y, block_id, count=1):
        self.world_x = x
        self.world_z = y
        self.block_id = block_id
        self.count = count
        self.velocity_z = 0
        self.on_ground = False
        self.spawn_time = time.time()
        self.last_update_time = time.time()

    def update(self, loaded_chunks):
        current_time = time.time()
        delta_time = min(0.1, current_time - self.last_update_time)
        self.last_update_time = current_time
        if not self.on_ground:
            self.velocity_z += 15 * delta_time
            self.velocity_z = min(self.velocity_z, 10)
            self.world_z += self.velocity_z * delta_time
            chunk_x = int(self.world_x // CHUNK_SIZE)
            chunk_z = int(self.world_z // CHUNK_SIZE)
            if (chunk_x, chunk_z) in loaded_chunks:
                chunk = loaded_chunks[(chunk_x, chunk_z)]
                in_chunk_x = int(self.world_x % CHUNK_SIZE)
                in_chunk_y = min(Y_MAX-1, max(0, int(self.world_z)))
                in_chunk_z = int(self.world_z % CHUNK_SIZE)
                if (0 <= in_chunk_x < CHUNK_SIZE and 0 <= in_chunk_y < Y_MAX and 
                    0 <= in_chunk_z < CHUNK_SIZE and chunk.blocks[in_chunk_x][in_chunk_y][in_chunk_z] != 0):
                    self.on_ground = True
                    self.velocity_z = 0
                    self.world_z = chunk_z * CHUNK_SIZE + in_chunk_z
        if time.time() - self.spawn_time > 300:
            return False
        return True

    def draw(self, screen, player):
        screen_x = int((self.world_x - player.world_x) * BLOCK_SIZE + SCREEN_WIDTH // 2)
        screen_y = int((self.world_z - player.world_z) * BLOCK_SIZE + SCREEN_HEIGHT // 2)
        if (screen_x < -16 or screen_x > SCREEN_WIDTH or 
            screen_y < -16 or screen_y > SCREEN_HEIGHT):
            return
        drop_rect = pygame.Rect(screen_x, screen_y, 16, 16)
        pygame.draw.rect(screen, BLOCK_TYPES[self.block_id]["color"], drop_rect)
        pygame.draw.rect(screen, WHITE, drop_rect, 1)
        if self.count > 1:
            count_text = main.small_font.render(str(self.count), True, WHITE)
            screen.blit(count_text, (screen_x + 8, screen_y))

