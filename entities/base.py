# entities/base.py
class Entity:
    def __init__(self, x, y, width=1, height=1):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.alive = True

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def update(self, game_map, dt):
        pass

    def collides_with(self, other):
        ax, ay, aw, ah = self.get_rect()
        bx, by, bw, bh = other.get_rect()
        return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by
