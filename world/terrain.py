"""地形生成：Perlin 噪声、地形生成器、区块数据容器。依赖 config 常量。"""
import random
import time
from config import *

class PerlinNoise:
    def __init__(self, seed=WORLD_SEED):
        self.seed = seed
        random.seed(seed)
        self.permutation = list(range(256))
        random.shuffle(self.permutation)
        self.p = self.permutation * 2
    
    def fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def lerp(self, t, a, b):
        return a + t * (b - a)
    
    def grad(self, hash_val, x, y, z=0):
        h = hash_val & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h in (12, 14) else z)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)
    
    def noise2d(self, x, y, frequency=1.0):
        x *= frequency
        y *= frequency
        xi = int(x) & 255
        yi = int(y) & 255
        xf = x - int(x)
        yf = y - int(y)
        u = self.fade(xf)
        v = self.fade(yf)
        a = self.p[xi] + yi
        aa = self.p[a]
        ab = self.p[a + 1]
        b = self.p[xi + 1] + yi
        ba = self.p[b]
        bb = self.p[b + 1]
        x1 = self.lerp(u, self.grad(aa, xf, yf), self.grad(ba, xf - 1, yf))
        x2 = self.lerp(u, self.grad(ab, xf, yf - 1), self.grad(bb, xf - 1, yf - 1))
        return self.lerp(v, x1, x2)
    
    def octave_noise2d(self, x, y, octaves=4, persistence=0.5, frequency=1.0):
        value = 0
        amplitude = 1.0
        max_value = 0
        for i in range(octaves):
            value += self.noise2d(x, y, frequency * (2 ** i)) * amplitude
            max_value += amplitude
            amplitude *= persistence
        return value / max_value


class TerrainGenerator:
    """混合地形生成器：地表1D噪声 + 地下2D噪声（2D风格）"""
    
    def __init__(self, seed=WORLD_SEED):
        self.seed = seed
        self.height_noise = PerlinNoise(seed)
        self.cave_noise = PerlinNoise(seed + 1)
        self.ore_noise = PerlinNoise(seed + 2)
        
        self.base_height = Y_MAX // 2
        self.amplitude = 20
        self.cave_threshold_base = 0.65
        self.ore_frequency = 0.05
        self.ore_thresholds = {
            7: (0.85, 30),   # 煤矿
            13: (0.9, 50),   # 铁矿
            15: (0.95, 70),  # 金矿
        }
    
    def get_height(self, world_x, world_z=None):
        noise_val = self.height_noise.octave_noise2d(world_x, 0, octaves=4, persistence=0.5, frequency=0.01)
        normalized = (noise_val + 1) / 2
        height = self.base_height + (normalized - 0.5) * self.amplitude
        return int(max(10, min(height, Y_MAX - 5)))
    
    def get_block(self, world_x, world_y):
        surface_y = self.get_height(world_x)
        if world_y > surface_y:
            return 0
        depth_factor = (surface_y - world_y) / surface_y
        cave_noise = self.cave_noise.noise2d(world_x * 0.03, world_y * 0.03)
        if cave_noise > self.cave_threshold_base - depth_factor * 0.3:
            return 0
        if world_y == surface_y:
            return 1
        elif world_y > surface_y - 4:
            return 2
        else:
            for block_id, (threshold, min_depth) in self.ore_thresholds.items():
                if world_y < Y_MAX - min_depth:
                    ore_noise = self.ore_noise.noise2d(world_x * self.ore_frequency, world_y * self.ore_frequency)
                    if ore_noise > threshold:
                        return block_id
            return 3
    
    def generate_chunk(self, chunk_x, chunk_z):
        blocks = [[[0 for _ in range(CHUNK_SIZE)] for _ in range(Y_MAX)] for _ in range(CHUNK_SIZE)]
        world_base_x = chunk_x * CHUNK_SIZE
        for local_x in range(CHUNK_SIZE):
            world_x = world_base_x + local_x
            for world_y in range(Y_MAX):
                block_id = self.get_block(world_x, world_y)
                for local_z in range(CHUNK_SIZE):
                    blocks[local_x][world_y][local_z] = block_id
        return blocks


class Chunk:
    def __init__(self, chunk_x, chunk_z, seed):
        self.chunk_x = chunk_x
        self.chunk_z = chunk_z
        self.seed = seed
        self.terrain_gen = TerrainGenerator(seed)
        self.blocks = self.terrain_gen.generate_chunk(chunk_x, chunk_z)
        self.last_accessed = time.time()

