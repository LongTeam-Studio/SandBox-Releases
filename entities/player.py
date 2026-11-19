# entities/player.py
from entities.base import Entity

class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, width=1, height=1)
        self.speed = 5
        self.color = (0, 200, 100)

    def move(self, dx, dy, game_map):
        new_x = self.x + dx
        new_y = self.y + dy
        tile = game_map.get_tile(new_x, new_y)
        if tile and tile.is_walkable:
            self.x = new_x
            self.y = new_y
