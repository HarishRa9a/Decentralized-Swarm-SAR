class Victim:
    # class for victim
    def __init__(self, grid_position, world_position):
        self.grid_position = grid_position
        self.position = world_position
        self.rescued = False


class Obstacle:
    # Class for obstacle object
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def bounds(self):
        # Grid + World position
        return (self.x, self.y, self.x + self.width, self.y + self.height)
