from utils.constants import FREE, WALL, VICTIM

class GridMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[WALL for _ in range(width)] for _ in range(height)]

    def in_bounds(self, x, y):
        return 0 <= x < self.height and 0 <= y < self.width

    def is_free(self, x, y):
        return self.grid[x][y] == FREE

    def is_wall(self, x, y):
        return self.grid[x][y] == WALL
    
    def can_move(self, x, y):
        return self.grid[x][y] == FREE or self.grid[x][y] == VICTIM

    def set_cell(self, x, y, value):
        if self.in_bounds(x, y):
            self.grid[x][y] = value

    def get_cell(self, x, y):
        if self.in_bounds(x, y):
            return self.grid[x][y]
        return None

    def get_neighbors(self, x, y):
        directions = [(1,0), (-1,0), (0,1), (0,-1)]
        neighbors = []

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                neighbors.append((nx, ny))

        return neighbors