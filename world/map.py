# world/map.py
from world.tile import Tile

class GameMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = self._generate_map()

    def _generate_map(self):
        """初始化地图网格，默认生成全地面，四周加墙"""
        tiles = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                # 边缘一圈设为不可通行的墙
                is_wall = (x == 0 or x == self.width - 1 or y == 0 or y == self.height - 1)
                row.append(Tile(x, y, is_walkable=not is_wall))
            tiles.append(row)
        return tiles

    def get_tile(self, x, y):
        """获取指定坐标的瓦片"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None
