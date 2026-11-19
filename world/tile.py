# world/tile.py
class Tile:
    def __init__(self, x, y, is_walkable=True):
        self.x = x
        self.y = y
        self.is_walkable = is_walkable  # 是否可通行（True=地面，False=墙壁）
        self.color = (70, 70, 70) if is_walkable else (30, 30, 30)

    def get_pos(self):
        return (self.x, self.y)
